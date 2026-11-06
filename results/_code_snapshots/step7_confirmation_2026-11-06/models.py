"""Models: EEGNet-style CNN on raw EEG, optionally fused with a small CNN on microstates.

MicroStateNet(use_ms=False) is a plain EEGNet (Lawhern et al., 2018) re-implemented in PyTorch.
MicroStateNet(use_ms=True)  is our hybrid: EEGNet branch + microstate CNN branch, concatenated.
"""
import torch
import torch.nn as nn


class EEGBranch(nn.Module):
    """EEGNet feature extractor (Lawhern et al., 2018): temporal -> depthwise spatial -> separable."""

    def __init__(self, n_chans=19, n_times=512, F1=8, D=2, F2=16, k_time=64, dropout=0.5):
        super().__init__()
        self.net = nn.Sequential(
            # temporal filters (kernel = 0.5 s at 128 Hz): learn frequency bands
            nn.Conv2d(1, F1, (1, k_time), padding="same", bias=False),
            nn.BatchNorm2d(F1),
            # depthwise spatial filters: learn electrode combinations
            nn.Conv2d(F1, F1 * D, (n_chans, 1), groups=F1, bias=False),
            nn.BatchNorm2d(F1 * D), nn.ELU(),
            nn.AvgPool2d((1, 4)), nn.Dropout(dropout),
            # separable convolution: combine patterns over time
            nn.Conv2d(F1 * D, F1 * D, (1, 16), padding="same", groups=F1 * D, bias=False),
            nn.Conv2d(F1 * D, F2, 1, bias=False),
            nn.BatchNorm2d(F2), nn.ELU(),
            nn.AvgPool2d((1, 8)), nn.Dropout(dropout),
            nn.Flatten(),
        )
        self.out_dim = F2 * (n_times // 32)

    def forward(self, x):  # x: (batch, channels, time)
        return self.net(x.unsqueeze(1))


class MSBranch(nn.Module):
    """Small 1D CNN over the microstate sequence: (batch, 4 classes, time) of |spatial correlation|."""

    def __init__(self, n_states=4, dropout=0.5, out_dim=32):
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv1d(n_states, 8, 33, padding="same", bias=False),  # ~0.25 s: segment durations
            nn.BatchNorm1d(8), nn.ELU(),
            nn.AvgPool1d(4), nn.Dropout(dropout),
            nn.Conv1d(8, 16, 9, padding="same", bias=False),          # switching patterns
            nn.BatchNorm1d(16), nn.ELU(),
            nn.AdaptiveAvgPool1d(8), nn.Dropout(dropout),
            nn.Flatten(),
            nn.Linear(16 * 8, out_dim), nn.ELU(),
        )
        self.out_dim = out_dim

    def forward(self, x):
        return self.net(x)


class MicroStateNet(nn.Module):
    def __init__(self, n_chans=19, n_times=512, n_classes=2, use_ms=True, dropout=0.5, n_feats=0):
        super().__init__()
        self.use_ms = use_ms
        self.eeg = EEGBranch(n_chans, n_times, dropout=dropout)
        dim = self.eeg.out_dim
        if use_ms:
            self.ms = MSBranch(dropout=dropout)
            dim += self.ms.out_dim
        self.feat = None
        if use_ms and n_feats:  # optional: window-level microstate features (coverage, duration, ...) via a small MLP
            self.feat = nn.Sequential(nn.Linear(n_feats, 16), nn.ELU(), nn.Dropout(dropout))
            dim += 16
        self.head = nn.Linear(dim, n_classes)

    def forward(self, x_eeg, x_ms=None, x_feat=None):
        z = self.eeg(x_eeg)
        if self.use_ms:
            z = torch.cat([z, self.ms(x_ms)], dim=1)
        if self.feat is not None:
            z = torch.cat([z, self.feat(x_feat)], dim=1)
        return self.head(z)

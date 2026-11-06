# ds004504 dataset check

**Result: PASS** — 88 subjects, A=36, F=23, C=29; 0 missing and 0 unreadable .set files.

## Dataset

- Name: A dataset of EEG recordings from: Alzheimer's disease, Frontotemporal dementia and Healthy subjects
- Version / DOI: doi:10.18112/openneuro.ds004504.v1.0.9 (CHANGES top entry: `1.0.9 2026-05-20`)
- BIDS version: v1.2.1; licence: CC0
- Local path: `/Users/nawaf/Desktop/Neurostate/ds004504`
- Total size: 5.38 GiB = 5.78 GB (5,780,997,840 bytes)
- Download date (not logged; creation time of the local folder): 2026-11-03. The .set modification times (2023-02-17) are the original upload times kept by the download, not the download date.
- Check run: 2026-11-03 20:45, Python 3.12.16, mne 1.13.2, pandas 3.1.0

Derivatives are already preprocessed by the dataset authors (0.5-45 Hz band-pass, ASR, ICA); state this in the paper's data section.

## Participants

| Group | Expected | Found |
|---|---|---|
| A | 36 | 36 |
| F | 23 | 23 |
| C | 29 | 29 |
| Total | 88 | 88 |

- `sub-*` folders at top level: 88; in `derivatives/`: 88
- Folders not in participants.tsv: none

## Files

- Raw .set found: 88 / 88
- Derivative .set found: 88 / 88
- Missing: none
- Unreadable by MNE: none
- Signal data is stored inside each .set (no separate .fdt files).

## Recording properties (read from file headers)

- derivative: channels [19], sampling rate [500.0] Hz, duration 306.1-1281.7 s (median 804.5 s)
- raw: channels [19], sampling rate [500.0] Hz, duration 307.1-1291.1 s (median 814.0 s)
- Distinct channel lists across all files: 1 (`Fp1, Fp2, F3, F4, C3, C4, P3, P4, O1, O2, F7, F8, T3, T4, T5, T6, Fz, Cz, Pz`)

Derivative recording length by group (minutes, mean ± SD):

- A: 13.5 ± 2.7 (min 5.1, max 21.4)
- F: 12.0 ± 2.4 (min 8.0, max 16.9)
- C: 13.9 ± 1.1 (min 12.5, max 16.5)

## SHA-256 of .set files

```
2bee41ac31694c06688bd4e36e4fd1233b4744c5ac80a822ec2a9cd67c5efe0d  derivatives/sub-001/eeg/sub-001_task-eyesclosed_eeg.set
7996d30b453a6438d39f0059547b8ef50669f9f084111d05bfec694a14b59a2c  derivatives/sub-002/eeg/sub-002_task-eyesclosed_eeg.set
6689383d189c2469b9f9786d2e0487d92cc215ca1eb1f729a792ed51ad9a9f9c  derivatives/sub-003/eeg/sub-003_task-eyesclosed_eeg.set
e9a582edcdd5a6fffd1bb7232007ec11d29486dba46d0e5c45f260cb9e7b92b8  derivatives/sub-004/eeg/sub-004_task-eyesclosed_eeg.set
befa4f7ac305c6faefb92fa0f82028327f51c277f5c5ecaf6271d669e7800291  derivatives/sub-005/eeg/sub-005_task-eyesclosed_eeg.set
3b87b043aa7540910d7b9e4b871e1f11af1f2437ee2f1cfb6f6b14d86f36ee04  derivatives/sub-006/eeg/sub-006_task-eyesclosed_eeg.set
d1aa601da8b8ecdf4f3ae7be1857aaca414209d2791b3cfdf02630a9258cfa1e  derivatives/sub-007/eeg/sub-007_task-eyesclosed_eeg.set
30d3b20abae8fe15f9c4771da03ac090403a0adfeed2292fae67a4484a297b05  derivatives/sub-008/eeg/sub-008_task-eyesclosed_eeg.set
6a22b93a1901593f2eb1fc600c03af8a54f318f4a8695745f5a65bfb63f76657  derivatives/sub-009/eeg/sub-009_task-eyesclosed_eeg.set
514316b75b01095d987b50f286f8d1843da2f13d24dbac42d245af1378d4c777  derivatives/sub-010/eeg/sub-010_task-eyesclosed_eeg.set
5f99ea3575b9b2f5c33f1c091d27c7a2119b105feab11dfbfa5187b764f6a998  derivatives/sub-011/eeg/sub-011_task-eyesclosed_eeg.set
871259ec1ff9fa4bfda7f2ea92b1a9a597de716c28e4a4181616267206ec5b13  derivatives/sub-012/eeg/sub-012_task-eyesclosed_eeg.set
cb34050f098bf22a3f8c2d2ad310ad7a26b336dd80707cd6c845c9ea051dde8a  derivatives/sub-013/eeg/sub-013_task-eyesclosed_eeg.set
7de89cab9ba48b48f7c7d470f78ed1164488910e8ab905a293be376a3a2d8448  derivatives/sub-014/eeg/sub-014_task-eyesclosed_eeg.set
ecc8fb5fd0c67f5ecfa61a98ad8c99c9fbb91ded460ae622e766ccbd3bb7b694  derivatives/sub-015/eeg/sub-015_task-eyesclosed_eeg.set
5ed950cc3b031ca26d6edb8666225f6d8136fbbf6758869130ab27eef67ce914  derivatives/sub-016/eeg/sub-016_task-eyesclosed_eeg.set
9ef28e09655f1b57fdd44eed4b594bbc4f89ce8630eb8a9acfb2ded9ece241e5  derivatives/sub-017/eeg/sub-017_task-eyesclosed_eeg.set
a7a62ed9c6a3155d421fd0750c3a4cdec7f60b27dfc95be687092e1ede1552c7  derivatives/sub-018/eeg/sub-018_task-eyesclosed_eeg.set
91b718e4ec88613f4b3f6a1105c909a8d524e9176801f46b69dcf0aabd010b09  derivatives/sub-019/eeg/sub-019_task-eyesclosed_eeg.set
31ad3071940f98dc3abe7fb6079f2fbb65d4c07f7e81c9c318bd719035533050  derivatives/sub-020/eeg/sub-020_task-eyesclosed_eeg.set
f5cee362ad4f1b7c7983bec413fbeff2813ad53c120663c2b62ae228f87abe65  derivatives/sub-021/eeg/sub-021_task-eyesclosed_eeg.set
c6aa0f028980b37694c8f6c5eebf33a30251da88f82a275409fd84f0a14044f3  derivatives/sub-022/eeg/sub-022_task-eyesclosed_eeg.set
6f76aa5f0f7e76e7c924f87dfe5cd4a54bdf205da1a39d050e51263462f28ea6  derivatives/sub-023/eeg/sub-023_task-eyesclosed_eeg.set
20f9c037debb0a5123e50ddb23a9c724902573d9730ddf313d347154806468f2  derivatives/sub-024/eeg/sub-024_task-eyesclosed_eeg.set
9f69af89ee60139680ee1255d8133433da3d858e786c88d34b698b89883f1c48  derivatives/sub-025/eeg/sub-025_task-eyesclosed_eeg.set
cee439f692a00cca2ebadc9cab9bfbfdf0c53c80da92984874a0621486bd82cb  derivatives/sub-026/eeg/sub-026_task-eyesclosed_eeg.set
8647c35865d88d35b96641774465a1848374da726e3d27af10cac3e67b4d9e1b  derivatives/sub-027/eeg/sub-027_task-eyesclosed_eeg.set
456cef7bceecea7d73aa05204d40462939c46c0d587f727c2d258a872e766197  derivatives/sub-028/eeg/sub-028_task-eyesclosed_eeg.set
976381a11cc2d05ab83dfa18ed2ea5b823de0b628123a7a87b56261a6e4d1c7e  derivatives/sub-029/eeg/sub-029_task-eyesclosed_eeg.set
52ac5b13f2b9f63404d3ed9fa441f62cdcb007e18d0536d3948d2d6219ea415b  derivatives/sub-030/eeg/sub-030_task-eyesclosed_eeg.set
b3aa5706a8105488c1804ebd3af84e0feb3617f60fd919fbc118cc1a5b3c93c5  derivatives/sub-031/eeg/sub-031_task-eyesclosed_eeg.set
85df1c92af6da493a20aff8714ebe54b50a9ce0067800b2879141d225a8e38f1  derivatives/sub-032/eeg/sub-032_task-eyesclosed_eeg.set
d84c49e0663506d46db48c6862d1591b88df3d15d50e0e51da73a87e138fb3dd  derivatives/sub-033/eeg/sub-033_task-eyesclosed_eeg.set
d3bc3e0b4be18da274907ff65b3bbe3355ad6ef8d6b1ca6f3cbefae88585d9b6  derivatives/sub-034/eeg/sub-034_task-eyesclosed_eeg.set
09deb5d9eab734e989c4c38d0296763b3697ab93ed46445f1a0fabf3fca964de  derivatives/sub-035/eeg/sub-035_task-eyesclosed_eeg.set
0e2d814176e6f0f55245d339ec0fec12c1c014ac2933ecffd1e1da495e797c3c  derivatives/sub-036/eeg/sub-036_task-eyesclosed_eeg.set
9921624e8bd740202cbb116a23f66fe9258378998bd0032bfefa47b7bf9d35d9  derivatives/sub-037/eeg/sub-037_task-eyesclosed_eeg.set
cdc9cf5e704517ae645483f7f4af73644407510c99aede2b2ef9d114a5d7b8bb  derivatives/sub-038/eeg/sub-038_task-eyesclosed_eeg.set
5576afeb06073f77760f4803dc4333e2c77ddb25e40cf3af54343b665214e593  derivatives/sub-039/eeg/sub-039_task-eyesclosed_eeg.set
20279f151615d595e925631f226110b6ee02691f0c5dee1223f8176f1e645e4f  derivatives/sub-040/eeg/sub-040_task-eyesclosed_eeg.set
6643ac4b575fcb6cf03329274034a345077ebd39cbf0e4d8daa647d5c395eadb  derivatives/sub-041/eeg/sub-041_task-eyesclosed_eeg.set
88aed8afce7b3ffc2ff879713c5dcf95048c3583691c01d7bef850fc680c294b  derivatives/sub-042/eeg/sub-042_task-eyesclosed_eeg.set
b16d7982c0660c627c25e758698937ce58f046f08f39fe4df17452dab2f65f1b  derivatives/sub-043/eeg/sub-043_task-eyesclosed_eeg.set
89f84d55abd8ca9d37fae77bd5735956f4f98fcc72a8e9d8e33b9881499eb422  derivatives/sub-044/eeg/sub-044_task-eyesclosed_eeg.set
06872ef2c34385452a7bb106acfc2c773b88a72898e27554b822568ed6ac3e3b  derivatives/sub-045/eeg/sub-045_task-eyesclosed_eeg.set
1a1dc77cc8be6b6405e89876757da3db75cd11c08a33f7613c02a4606c91fe1a  derivatives/sub-046/eeg/sub-046_task-eyesclosed_eeg.set
94ed76a3ddc87d8adb0db946fefdbfa18dbfae7cdfae4ee9e1aec9dbb7d39eb7  derivatives/sub-047/eeg/sub-047_task-eyesclosed_eeg.set
b749f9e3058dbb3398ce498d1f205c68b5a4312e4f766c8e37f3452b8ed26bd0  derivatives/sub-048/eeg/sub-048_task-eyesclosed_eeg.set
98f2b1baf832eae2357754a0d5be50ca01ad0ed5b9d0f0e786e85d51d6572a3e  derivatives/sub-049/eeg/sub-049_task-eyesclosed_eeg.set
a5340e8a7feb7e35595ca512bf4c4e0478ed1bfac762afd9d014be3e77731c54  derivatives/sub-050/eeg/sub-050_task-eyesclosed_eeg.set
568e5f06f280ae7dc31256b0637f1f610183fd5ff72f30dca6214e33f3c739e0  derivatives/sub-051/eeg/sub-051_task-eyesclosed_eeg.set
068e3687d2dff59ff1b790485236551439136c6d139e2e88d9d26e47d7d83b47  derivatives/sub-052/eeg/sub-052_task-eyesclosed_eeg.set
c06142af0699bdf65b61e6457609cf40b92587e59d98f03fd84d69816285b1ed  derivatives/sub-053/eeg/sub-053_task-eyesclosed_eeg.set
53e5b0f56b67f33d6c02ad277fda1d57d383ccb27b43c2c19f39beb5aaf7a3ca  derivatives/sub-054/eeg/sub-054_task-eyesclosed_eeg.set
9d65d41bac4803e47e328b8c586aa82866805d89e77c2a6183c520df467df0f9  derivatives/sub-055/eeg/sub-055_task-eyesclosed_eeg.set
9a8fbb0923d836bd5aa29010124828f794648beb4b52eabf7c046e4586b41ba3  derivatives/sub-056/eeg/sub-056_task-eyesclosed_eeg.set
4a0b8095a0f0f75ffb65ba96d1555c50a3e2522d53f71013957d3a287322e800  derivatives/sub-057/eeg/sub-057_task-eyesclosed_eeg.set
f5a8ca25a68bfdf219d2399d31575ff901c824afc5b1cb76f84ac7d1bfc10df9  derivatives/sub-058/eeg/sub-058_task-eyesclosed_eeg.set
fb6bd8c4d81efa76eb54c9025b788c04f0944a9bab602d97999995b01555a16b  derivatives/sub-059/eeg/sub-059_task-eyesclosed_eeg.set
fe203229a97787a46cecde4d8e1abfe90b60183b65e99e35393793bff8e76adf  derivatives/sub-060/eeg/sub-060_task-eyesclosed_eeg.set
edb69e0e90c8489d63fe801fe8c5fec4cedc655ec6b14f56b18a42f726280f65  derivatives/sub-061/eeg/sub-061_task-eyesclosed_eeg.set
b75b58ca0f404bec77680fac09555091799dc902338376a8f262cbb3bdb4b246  derivatives/sub-062/eeg/sub-062_task-eyesclosed_eeg.set
5c61ab2332d33e62e16ba3f4749625825d23ea12c50630d92ec3a576525e1f14  derivatives/sub-063/eeg/sub-063_task-eyesclosed_eeg.set
4e0162e511499bfdd958ae8ba84aad1048b6cf106580643135eb67866358a0a0  derivatives/sub-064/eeg/sub-064_task-eyesclosed_eeg.set
a9220b46810a2b187037e669bc59840d2923161ada06bc471a2b962dc1895b43  derivatives/sub-065/eeg/sub-065_task-eyesclosed_eeg.set
cd323034017eea41f5c9ecc1f7535a30c0326f59e1c4d85bf3a6cec7ab8bda52  derivatives/sub-066/eeg/sub-066_task-eyesclosed_eeg.set
d7e2b5f66437c30643ad28ca8730c4b1b7b5bbb6037ab38249f8d29d78bdba8f  derivatives/sub-067/eeg/sub-067_task-eyesclosed_eeg.set
62fac557c99a1914d7f819343b7ddba66053e74f095f337240c3a5214856b7fe  derivatives/sub-068/eeg/sub-068_task-eyesclosed_eeg.set
d16e501268da0b4d4fd873c32906fd404a9d7c527dac384ffdd08377efb80282  derivatives/sub-069/eeg/sub-069_task-eyesclosed_eeg.set
9f50e2e825a33961ffed6f6da35d942de20c92268feafdecd610bad188781faf  derivatives/sub-070/eeg/sub-070_task-eyesclosed_eeg.set
73639ad2c30a4d33305640fef7da944699cb80fbf205f51991e55294bef7fe79  derivatives/sub-071/eeg/sub-071_task-eyesclosed_eeg.set
94feae216ee0e44d2858bf66b85b573fabc5a45fd4c45e590025107106cfcc7a  derivatives/sub-072/eeg/sub-072_task-eyesclosed_eeg.set
13462b8c825e45cb2d4e5097cbbed5e46a52cb4ce007fb359bcc47ca2883d00b  derivatives/sub-073/eeg/sub-073_task-eyesclosed_eeg.set
323d400ad2e18106de90ca7ed5192deaa7d8b8f3e2aa3188f13744db3e3acbaf  derivatives/sub-074/eeg/sub-074_task-eyesclosed_eeg.set
98d0bffea203d140f1385a41c219e9f5bc3e6b71ad89c3c825e61a7875e0c271  derivatives/sub-075/eeg/sub-075_task-eyesclosed_eeg.set
2b5f954943899f88157eace7532785a34d62a5c7cdcc98f34cf926be6ac3238d  derivatives/sub-076/eeg/sub-076_task-eyesclosed_eeg.set
5d23325eca733ae0ef9bd4ce1d1352d9869830ffd0933e2d90c77e8a7a0276bb  derivatives/sub-077/eeg/sub-077_task-eyesclosed_eeg.set
3dd1baae55cceaaae0359a5bfcd83e8dbd65c6c0e28f0f2a2ff1e9e870970504  derivatives/sub-078/eeg/sub-078_task-eyesclosed_eeg.set
c53402e00fe8e65d283a257c84365abe53e74cc97a21bd54463f6bde793a6fdd  derivatives/sub-079/eeg/sub-079_task-eyesclosed_eeg.set
a8dd6fccc53a582fdd3278995edd654bb39aafffb92d20eb1dca803328328991  derivatives/sub-080/eeg/sub-080_task-eyesclosed_eeg.set
22352b2257891716a26e8787b812e4ff11df389abde1bb4f2554662def9b0c72  derivatives/sub-081/eeg/sub-081_task-eyesclosed_eeg.set
18aa69628a62676b2b679edeb90c123d5de237f1a4f7d63b7e75d58a753445d3  derivatives/sub-082/eeg/sub-082_task-eyesclosed_eeg.set
8cd414126e564a2d0e34bf622a69602e8f378d3e8dd16612a9b7d303823eab88  derivatives/sub-083/eeg/sub-083_task-eyesclosed_eeg.set
0b99404c8b7eef25be6746686ceaf12975d9c6ecf4569c45e24a5dc61042f098  derivatives/sub-084/eeg/sub-084_task-eyesclosed_eeg.set
3498d4a95aeb30d28034a7713b480e450fb3fc04faa0df17a94672122d5bf6e9  derivatives/sub-085/eeg/sub-085_task-eyesclosed_eeg.set
7e5e1da143fff33cd62b88735a358b1b05a388e1d775c8c8fe23c0544babe2e5  derivatives/sub-086/eeg/sub-086_task-eyesclosed_eeg.set
0974feca278c7e5d7cd9f0c51ba74f1b037d61662c7be111a1d7c9949ba1e417  derivatives/sub-087/eeg/sub-087_task-eyesclosed_eeg.set
f34f5e7e62dad1a4722acf5b007dc1f2744018fff3d5f5fa5caa1872c61debc3  derivatives/sub-088/eeg/sub-088_task-eyesclosed_eeg.set
98e923d2d4d5682882ef8254da3a1060d305287b26eed9af61cbbce558e885c3  sub-001/eeg/sub-001_task-eyesclosed_eeg.set
3178a7b0cc07799857f564eb236cc835cf479bb161cf7745b0427bf8c08c7818  sub-002/eeg/sub-002_task-eyesclosed_eeg.set
c8de6b9bfd868ed8f4d522a74a0c957a41fc9ac412a9563fe387d45dce500252  sub-003/eeg/sub-003_task-eyesclosed_eeg.set
2cf33a8674758403d9234774e6fd042a4e3a23be3373a9a77f7d6e621880a256  sub-004/eeg/sub-004_task-eyesclosed_eeg.set
f582444e9f2cd43651d8b80aa6830420c7293759a3be86c12bcd05a3e69e6f0a  sub-005/eeg/sub-005_task-eyesclosed_eeg.set
8133ce66a41337db9f83950fbbaff1b91b7ac69d6fddedc5ea2253c83e461ffb  sub-006/eeg/sub-006_task-eyesclosed_eeg.set
e1ccd926fbda0309db58ec60b4b6fa32d9ef7493e6f8ecb6e769777454c31c21  sub-007/eeg/sub-007_task-eyesclosed_eeg.set
36bacf70b96aea2a2d25ca1cd284d4f13dd6029227f1426b77680e9014f93697  sub-008/eeg/sub-008_task-eyesclosed_eeg.set
d4f322bcb6c659f92beb2333b93bc48e4815e3a438e62fde4ce9cae59aa44284  sub-009/eeg/sub-009_task-eyesclosed_eeg.set
3e5c2e666c893ca1ec1fd757123e3b6f4f1a8717e2e1e4a54ac39a004062fb9e  sub-010/eeg/sub-010_task-eyesclosed_eeg.set
61ce09c19b8e4265304ec1853cccf57b1ae4bea14a734a3b20555a4fa68c2a18  sub-011/eeg/sub-011_task-eyesclosed_eeg.set
d6606b4549b7b5b9c32909e3e9a76804cb0e1915d8fd65b5d4125cdfc5a652ba  sub-012/eeg/sub-012_task-eyesclosed_eeg.set
68772a6d65d4fe1e7fbd3fde279ba5bdc8d0a8814be7b7293c38c69a3a67407a  sub-013/eeg/sub-013_task-eyesclosed_eeg.set
f8312a062231c1fe54ae1b075ed4b6c4831f00c3c7ca06a58dd25fbc13f729df  sub-014/eeg/sub-014_task-eyesclosed_eeg.set
26ed6b8adfa29402093600a846e0ae40f0df2e3e45d8f21b180e8b8290b9dae6  sub-015/eeg/sub-015_task-eyesclosed_eeg.set
4a242b0f09b39f897ae9b0c42ac34d8f793c49e59ae8b64221b39fc80335018b  sub-016/eeg/sub-016_task-eyesclosed_eeg.set
bdb574d2f8c637dcec514ea779c38b71ed2d38282c64a3e32bd36f343f16404d  sub-017/eeg/sub-017_task-eyesclosed_eeg.set
aaf6bed0275d68274b85bdac7218e8a70e270050d12f4d21bbc3a2c6c0850b73  sub-018/eeg/sub-018_task-eyesclosed_eeg.set
a9cb087391066c1147da49bf681ca3f0ee1d0e911a7f842fcb08902fa5096e50  sub-019/eeg/sub-019_task-eyesclosed_eeg.set
a30fef22f00cfb2de436d56b5206149974b7ffbce93340c2d3fc496fc45e72bf  sub-020/eeg/sub-020_task-eyesclosed_eeg.set
e9d1b195784fd1b1188ce7ba4af414cde05f5d185c5298680bae51e4ca7e80ca  sub-021/eeg/sub-021_task-eyesclosed_eeg.set
07eedbfdf8ae43675c03005aeeb3537d4fbb3da2604551ce6fc0747a62e0a48b  sub-022/eeg/sub-022_task-eyesclosed_eeg.set
c2a06c9d355af32f0db2066649b4190cdfb1171c3d7b4d4fde736274211de63d  sub-023/eeg/sub-023_task-eyesclosed_eeg.set
ca36ebf4ec191e56c318d352be065b879260711e298711abc647046d58cf16a7  sub-024/eeg/sub-024_task-eyesclosed_eeg.set
5c874121c531d2221e9d4d60c1a387bdc77a35be7a176e2ab9832aef77fa63d6  sub-025/eeg/sub-025_task-eyesclosed_eeg.set
f227ae47ac2e02e326cf4ed84b13c968b5f6a06e871fb3da8455cb4600fc4d5f  sub-026/eeg/sub-026_task-eyesclosed_eeg.set
f1a307e350bd0ccf80b046d6b6cbab6865ba37c8d1bacfacc90e072e0ecb4f42  sub-027/eeg/sub-027_task-eyesclosed_eeg.set
65b8776d2cecc851fb539296aff211bfa30c9c12e5234bf9fc73584d4f21552c  sub-028/eeg/sub-028_task-eyesclosed_eeg.set
eadf530ce6eef61262feedacb3793dffe8b04e3d88354960a496efb06645e8d8  sub-029/eeg/sub-029_task-eyesclosed_eeg.set
53f5e142a805f05e3986beed8ab27065628fc61c64c359831d1322ddb25b34bd  sub-030/eeg/sub-030_task-eyesclosed_eeg.set
931223a59ff74c555c282e3a72cd788a7753eccba0f8aff37a8cad788377601c  sub-031/eeg/sub-031_task-eyesclosed_eeg.set
6df8416f89161ab707f5e4adf33aedab3524a834b0e46fa1a28db69cc8722ffc  sub-032/eeg/sub-032_task-eyesclosed_eeg.set
2b0e80a11eea30ce3913f34ad5bcc2cdedda66298969ebfa143fd61247218970  sub-033/eeg/sub-033_task-eyesclosed_eeg.set
b66a26ad333f8e3ddad5d246a170629c495dc358f21018ae0f11e5c57e2d70ca  sub-034/eeg/sub-034_task-eyesclosed_eeg.set
e7ab2657bb5c389f808c669ccc22c4268ce48fb42d41ff3a5b9ebc405e9fa087  sub-035/eeg/sub-035_task-eyesclosed_eeg.set
bce564e1a84730e1cf6fd9ca1175776b783b79bafc294757af93b38c4361b127  sub-036/eeg/sub-036_task-eyesclosed_eeg.set
f5893131a1b9f868d78fd8406a3235d6165e82fa78ecd6bcf4046fcaa9a9b92d  sub-037/eeg/sub-037_task-eyesclosed_eeg.set
6f2ccdbfb52f5933b526d1f7ac0f20a806abe32ddbd2a57d934761fc05933c25  sub-038/eeg/sub-038_task-eyesclosed_eeg.set
007eb1397b78444858f51d4c5f0e6041a1092a098f1e54697df9ac6665b6b203  sub-039/eeg/sub-039_task-eyesclosed_eeg.set
d3c347b790604e3d9cb9d4ad56ebe0a9b0e35d00cc9186b4eea2d07bfae990b6  sub-040/eeg/sub-040_task-eyesclosed_eeg.set
a1ec80a114f08aa4598012f3ff70fdfe45bc6341921fb00ce42b5dd27d69bb68  sub-041/eeg/sub-041_task-eyesclosed_eeg.set
99065672f54de793fdf1dd581c69d776c4f3ebb39d49a4bcde12c1e4aaac0a88  sub-042/eeg/sub-042_task-eyesclosed_eeg.set
d2fd9e0e750e68c1441d67a4b22df570b96c8c9944f374ca0280639e2c17d8ab  sub-043/eeg/sub-043_task-eyesclosed_eeg.set
a76981615b74026a877c2a43f21a85f277c40b5efc23248c88be144667ce09c5  sub-044/eeg/sub-044_task-eyesclosed_eeg.set
68207ae36e35ca7644ee365e112c0e001ced55c97f24cd491297d1da5fa7c413  sub-045/eeg/sub-045_task-eyesclosed_eeg.set
85c0dcf2323b2c6833a93a6aa43ab95b53bc4115de6b987c3ca46cec532c9cf5  sub-046/eeg/sub-046_task-eyesclosed_eeg.set
38deee24c6f1cb4a4e2686dc4a7a8892f115e5639f654ddef86635afd491b83a  sub-047/eeg/sub-047_task-eyesclosed_eeg.set
998da7b0dc65e18d5bfdc6e8bafa8790cf9d287a62170838dfd12eee2cfb9341  sub-048/eeg/sub-048_task-eyesclosed_eeg.set
758e82cbe710a4314aa09ec07b485e1206969a507a59103e4d1b7b5d0ebda4d3  sub-049/eeg/sub-049_task-eyesclosed_eeg.set
6d8fbedad83e88314d0e77f7944f438e0e96a7aeee6d92b2bcbb211b3ea5cdce  sub-050/eeg/sub-050_task-eyesclosed_eeg.set
2af5181c37f7b8cbe16053e3a9bf1213f268728a08c1eec443301283b42a094d  sub-051/eeg/sub-051_task-eyesclosed_eeg.set
4bc6fd9b848ea26d2343e720248d37a2b8254cdf4f084145bbc519003d789b45  sub-052/eeg/sub-052_task-eyesclosed_eeg.set
2725b1b524ce39c1b21c3c884854e53bb3f30b17c088fd56fd95bb7a5288dc96  sub-053/eeg/sub-053_task-eyesclosed_eeg.set
6a9eed6554ffa79b583a5997c81ffcc7123f3de3b8ea3de72ce1214378d570ee  sub-054/eeg/sub-054_task-eyesclosed_eeg.set
0a24d8a21447f7220b290b7d56446c629cc9c79f9e4d99cf606edf2a3b800e4a  sub-055/eeg/sub-055_task-eyesclosed_eeg.set
7a0e6feb17a637038fd14603eab68496f6d6ce214e43eac4df84fc228009da18  sub-056/eeg/sub-056_task-eyesclosed_eeg.set
08b3b16322d9693c739d4a1aef9968124cbcecc4fb6ff5b2368c14641e005de7  sub-057/eeg/sub-057_task-eyesclosed_eeg.set
7d6547c67e2b181d1876e356b025a2d6f1632665bb327f196bcb56242c78ecd6  sub-058/eeg/sub-058_task-eyesclosed_eeg.set
fb5798843ac7620f446c867952f312376404d124a75001393c18210a9ff50a61  sub-059/eeg/sub-059_task-eyesclosed_eeg.set
2e39d4c53b43d1b10f4358d2949107d7ead119ab2727476aed09ae00d50e1b1b  sub-060/eeg/sub-060_task-eyesclosed_eeg.set
d65b1f823d74f3a242d76d7ef50ee59a984f72a6153c75b21acfe90dc47a4974  sub-061/eeg/sub-061_task-eyesclosed_eeg.set
f12652e2d57c41db79cd84a4d1dc597ab03ceec9c83a2734223107c8506f872f  sub-062/eeg/sub-062_task-eyesclosed_eeg.set
d89b37c17a5ad979947c901b9850a5691a278ee5fcfa9bd9a942811fc44b2b19  sub-063/eeg/sub-063_task-eyesclosed_eeg.set
83709f08c97180be0d20ac97a5d7686b06453417b0c6680ab495bc11e77846cd  sub-064/eeg/sub-064_task-eyesclosed_eeg.set
8356409d3b50ccbe097d4ab859a1c786b97851e6ac20e7ad82e1b388641d6bb2  sub-065/eeg/sub-065_task-eyesclosed_eeg.set
82022e582b6828730f582981ed7009298a9a0498f38a10eef94130634104c821  sub-066/eeg/sub-066_task-eyesclosed_eeg.set
b6e340cc59365f5ef9ab9ba0be5d6e22c4425a06d5c36d155198de71fc729483  sub-067/eeg/sub-067_task-eyesclosed_eeg.set
69c194a859bacf02c8e521849455dcaf45d8ca451d134d4d9e236b1b647fca89  sub-068/eeg/sub-068_task-eyesclosed_eeg.set
a7d5f6f40395b9b4efa20375bd61130076ae921d2ba558293cc00d923b6bd17c  sub-069/eeg/sub-069_task-eyesclosed_eeg.set
72b9190a22e6f22e6bcaba38688fa670a0bd1ee4d3d1304ed67f9e753ec92aeb  sub-070/eeg/sub-070_task-eyesclosed_eeg.set
4a342ead6feb45de53021432de83b72a3281cae9c33adfb6eabf31904b87d369  sub-071/eeg/sub-071_task-eyesclosed_eeg.set
a16ca3ee348ec179d1e31fa0822f6e6157014a31a14685c3e38be6e560cb7410  sub-072/eeg/sub-072_task-eyesclosed_eeg.set
c81bf6cd3a722d688ecef0a67b1cde88826b1a9f2acec8d6f5fe8d062aac7715  sub-073/eeg/sub-073_task-eyesclosed_eeg.set
fc2ac9b56246a397e42a4b158fddaeb59236f6761c35aca003ef524600a4fbf9  sub-074/eeg/sub-074_task-eyesclosed_eeg.set
36b420fb87429ec20e2ccd307d4e52c93f41a082be305380582e5bc5352f3612  sub-075/eeg/sub-075_task-eyesclosed_eeg.set
72183094d8671d17d34f2c3d70ffa4647ee4c02cf3ff7a06996032c5a777bf1c  sub-076/eeg/sub-076_task-eyesclosed_eeg.set
e90e1b0232d6ad6cef5f25a28ffd611f9c624138d655e49ecc6f19c182f9bb9f  sub-077/eeg/sub-077_task-eyesclosed_eeg.set
22901160687ac63d1bf0e9df80a15b629f7bd6595dc4f1c0a77ee81c2434a5d3  sub-078/eeg/sub-078_task-eyesclosed_eeg.set
ecf5717d2eba1d257ea6bac6763e5349a7ff34529d6a3919331cfd110fb3f4d0  sub-079/eeg/sub-079_task-eyesclosed_eeg.set
c5855058ece8f6dd1e92d7ee45e9652f070792c503419739b8e8fc22e5f598dd  sub-080/eeg/sub-080_task-eyesclosed_eeg.set
fed2ff70966f48bb0d1d14603db9804691ea4676a321aa7ddbbbd89b1e237cda  sub-081/eeg/sub-081_task-eyesclosed_eeg.set
6db55415e9d409945e3c52db48f1d337553f14f940e37c06d7633df91981b596  sub-082/eeg/sub-082_task-eyesclosed_eeg.set
3bd1bdc966d13070a9c31096e4f4a21feea04d2609c43e2c5928adf988370c71  sub-083/eeg/sub-083_task-eyesclosed_eeg.set
380acab076d54322e05a33651c468e8b4aa9588d5fcdfadb8a6cc66603badf77  sub-084/eeg/sub-084_task-eyesclosed_eeg.set
10220e189e1353f8585660d7930a73b30ba80763920dfe06be81af187629be27  sub-085/eeg/sub-085_task-eyesclosed_eeg.set
b0d8591f2ea895e36641ab69f54fae5ebed28ec6bc7ab62100eb919ba03dd38a  sub-086/eeg/sub-086_task-eyesclosed_eeg.set
0d3be1615cf426744a0283dc7233ceeaaf655bdbe3db10c82b7a6f822a27f498  sub-087/eeg/sub-087_task-eyesclosed_eeg.set
4ec75c4fcaa022ff52c882cd149b573fff675108fca78c30c77247450f74fd6c  sub-088/eeg/sub-088_task-eyesclosed_eeg.set
```

_Runtime: 3 s._

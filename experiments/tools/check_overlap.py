"""Layout check for a rendered PDF of the paper (LibreOffice or Word export).

Flags, per page: text lines from different blocks that overlap, text inside an image's area, and text off the page.
With --slack it also reports, per page, how far the lowest full-width block (a figure or table spanning both columns)
ends above the bottom margin, and flags it as FRAGILE under 18 pt: a slightly different renderer could push that block
across the page. Exit code 1 if anything is flagged. Needs PyMuPDF (pip install pymupdf).

  python tools/check_overlap.py <paper.pdf> [--slack] [-q]
"""
import sys

import fitz


def area(r):
    return max(0, r.width) * max(0, r.height)


def check(path, verbose=True):
    doc = fitz.open(path); bad_pages = []
    for pno, page in enumerate(doc, 1):
        d = page.get_text("dict"); lines = []
        for bi, b in enumerate(d["blocks"]):
            if b["type"] != 0: continue
            for l in b["lines"]:
                t = "".join(s["text"] for s in l["spans"]).strip()
                if t: lines.append((bi, fitz.Rect(l["bbox"]), t))
        imgs = [fitz.Rect(i["bbox"]) for i in page.get_image_info()]
        issues = []
        for i in range(len(lines)):
            bi, ri, ti = lines[i]
            for j in range(i + 1, len(lines)):
                bj, rj, tj = lines[j]
                if bi == bj: continue
                x = ri & rj
                if x.is_empty: continue
                if area(x) > 0.15 * min(area(ri), area(rj)) and x.height > 2:
                    issues.append(f"text/text: '{ti[:30]}' x '{tj[:30]}'")
            for im in imgs:
                x = ri & im
                if not x.is_empty and area(x) > 0.15 * area(ri):
                    issues.append(f"text/image: '{ti[:40]}'")
            if not page.rect.contains(ri):
                issues.append(f"off page: '{ti[:40]}'")
        for a in range(len(imgs)):
            for b in range(a + 1, len(imgs)):
                if area(imgs[a] & imgs[b]) > 4: issues.append("image/image")
        if verbose: print(f"page {pno}: {len(lines)} text lines, {len(imgs)} images, " + ("OK" if not issues else f"FLAGGED {len(issues)}: " + "; ".join(issues[:4])))
        if issues: bad_pages.append(pno)
    return len(doc), bad_pages


def full_width_slack(path, bottom_margin=72, min_slack=18):
    """Full-width blocks (images or table rules wider than 400 pt, images centred on the page, plus the caption just
    below a figure): their lowest point vs the bottom margin (72 pt in this template)."""
    doc = fitz.open(path); out = []
    for pno, page in enumerate(doc, 1):
        limit = page.rect.height - bottom_margin; bottoms = []
        for i in page.get_image_info():
            r = fitz.Rect(i["bbox"])
            if r.width > 400 or abs((r.x0 + r.x1) / 2 - page.rect.width / 2) < 30:  # wide, or centred on the page = full-width section
                caps = [fitz.Rect(b[:4]) for b in page.get_text("blocks") if b[1] >= r.y1 - 1 and b[1] < r.y1 + 30]
                bottoms.append(("figure", max([r.y1] + [c.y1 for c in caps])))
        rules = [d["rect"] for d in page.get_drawings() if d["rect"].width > 400 and d["rect"].height < 3]
        if rules: bottoms.append(("table", max(r.y1 for r in rules)))
        for kind, y in bottoms:
            out.append((pno, kind, round(limit - y, 1), limit - y < min_slack))
    return out


def main():
    path = sys.argv[1]
    n, bad = check(path, verbose="-q" not in sys.argv)
    print(f"{path.split('/')[-1]}: {n} pages, overlaps flagged on {bad or 'no page'}")
    fragile = []
    if "--slack" in sys.argv:
        for pno, kind, slack, frag in full_width_slack(path):
            print(f"  page {pno}: lowest full-width {kind} ends {slack} pt above the bottom margin{' FRAGILE' if frag else ''}")
            if frag: fragile.append(pno)
    sys.exit(1 if bad or fragile else 0)


if __name__ == "__main__":
    main()

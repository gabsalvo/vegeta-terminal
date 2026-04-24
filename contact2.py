#!/usr/bin/env python3
"""Render a clean contact sheet of extracted frames at native size,
filtered to plausible Vegeta sprite dimensions."""
import os, glob
from PIL import Image, ImageDraw

OUT = "/home/gabrielesalvo/vegeta/frames"
frames = sorted(glob.glob(f"{OUT}/frame_*.png"))

# Keep sprite-sized frames only (full bodies)
keep = []
for f in frames:
    im = Image.open(f)
    w, h = im.size
    if 18 <= w <= 120 and 25 <= h <= 110:
        keep.append((f, im))

print(f"kept {len(keep)} of {len(frames)} frames")

# Lay out at native size, 10 cols
cols = 10
cell_w = max(im.size[0] for _, im in keep) + 8
cell_h = max(im.size[1] for _, im in keep) + 20
rows = (len(keep) + cols - 1) // cols
sheet = Image.new("RGB", (cols*cell_w, rows*cell_h), (30, 30, 40))
draw = ImageDraw.Draw(sheet)
for i, (path, im) in enumerate(keep):
    r, c = i // cols, i % cols
    idx = int(os.path.basename(path).split("_")[1].split(".")[0])
    x = c*cell_w + (cell_w - im.size[0])//2
    y = r*cell_h + 16 + (cell_h - 16 - im.size[1])//2
    sheet.paste(im, (x, y), im if im.mode == "RGBA" else None)
    draw.text((c*cell_w + 4, r*cell_h + 2), f"#{idx}", fill=(255,255,180))

sheet.save(f"{OUT}/_contact2.png")
print(f"wrote {OUT}/_contact2.png")

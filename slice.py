#!/usr/bin/env python3
"""Slice the Vegeta sprite sheet into individual frames.
Strategy: find background color, locate connected non-bg regions,
save each as its own PNG with transparent background."""
import os, sys
from PIL import Image
from collections import deque

SHEET = "/home/gabrielesalvo/pet/dkp58h6-7c4ca149-2b79-435a-b270-2e856361f4bd.png"
OUT = "/home/gabrielesalvo/pet/frames"
os.makedirs(OUT, exist_ok=True)

img = Image.open(SHEET).convert("RGBA")
W, H = img.size
px = img.load()

# Crop off the footer (credits) and header (logos) so we only scan sprites.
# Looking at the image: header ~25px, footer ~60px. Be conservative.
TOP = 30
BOTTOM = H - 70

# Background: most common color within the sprite body (skip top/footer margins)
from collections import Counter
BODY_TOP = 130  # below the logo strip
cnt = Counter()
for y in range(BODY_TOP, BOTTOM, 3):
    for x in range(0, W, 3):
        cnt[px[x,y][:3]] += 1
bg = cnt.most_common(1)[0][0] + (255,)
TOP = BODY_TOP
print(f"bg color: {bg}, area: {W}x{BOTTOM-TOP}")

def is_bg(p, tol=25):
    return (abs(p[0]-bg[0]) < tol and abs(p[1]-bg[1]) < tol and abs(p[2]-bg[2]) < tol)

# Flood fill connected non-bg regions
visited = [[False]*H for _ in range(W)]
regions = []

for y in range(TOP, BOTTOM):
    for x in range(W):
        if visited[x][y]: continue
        if is_bg(px[x, y]):
            visited[x][y] = True
            continue
        # BFS
        q = deque([(x,y)])
        visited[x][y] = True
        minx, miny, maxx, maxy = x, y, x, y
        count = 0
        while q:
            cx, cy = q.popleft()
            count += 1
            if cx < minx: minx = cx
            if cx > maxx: maxx = cx
            if cy < miny: miny = cy
            if cy > maxy: maxy = cy
            for dx, dy in ((1,0),(-1,0),(0,1),(0,-1)):
                nx, ny = cx+dx, cy+dy
                if 0 <= nx < W and TOP <= ny < BOTTOM and not visited[nx][ny]:
                    visited[nx][ny] = True
                    if not is_bg(px[nx, ny]):
                        q.append((nx, ny))
        if count >= 30:  # filter tiny noise
            regions.append((minx, miny, maxx, maxy, count))

print(f"raw regions: {len(regions)}")

# Merge regions that are very close (same sprite split by transparent gap)
def merge_close(regs, gap=3):
    changed = True
    while changed:
        changed = False
        out = []
        used = [False]*len(regs)
        for i, a in enumerate(regs):
            if used[i]: continue
            ax1,ay1,ax2,ay2,ac = a
            for j in range(i+1, len(regs)):
                if used[j]: continue
                bx1,by1,bx2,by2,bc = regs[j]
                # overlap or near in both axes
                if (ax1-gap <= bx2 and bx1-gap <= ax2 and
                    ay1-gap <= by2 and by1-gap <= ay2):
                    ax1=min(ax1,bx1); ay1=min(ay1,by1)
                    ax2=max(ax2,bx2); ay2=max(ay2,by2)
                    ac += bc
                    used[j] = True
                    changed = True
            used[i] = True
            out.append((ax1,ay1,ax2,ay2,ac))
        regs = out
    return regs

regions = merge_close(regions, gap=0)
print(f"merged regions: {len(regions)}")

# Sort top-to-bottom, then left-to-right by row
regions.sort(key=lambda r: (r[1]//20, r[0]))

# Save and make a contact sheet
for i, (x1,y1,x2,y2,c) in enumerate(regions):
    crop = img.crop((x1, y1, x2+1, y2+1))
    # Make bg transparent
    data = []
    for p in crop.getdata():
        if is_bg(p): data.append((0,0,0,0))
        else: data.append(p)
    crop.putdata(data)
    crop.save(f"{OUT}/frame_{i:03d}.png")
    print(f"  {i:03d}: pos=({x1},{y1}) size={x2-x1+1}x{y2-y1+1} px={c}")

# Contact sheet for preview
if regions:
    maxw = max(r[2]-r[0]+1 for r in regions)
    maxh = max(r[3]-r[1]+1 for r in regions)
    cols = 8
    rows = (len(regions) + cols - 1) // cols
    sheet = Image.new("RGBA", (cols*(maxw+4), rows*(maxh+4)), (40,40,40,255))
    for i, (x1,y1,x2,y2,_) in enumerate(regions):
        crop = img.crop((x1, y1, x2+1, y2+1))
        r, c = i // cols, i % cols
        sheet.paste(crop, (c*(maxw+4)+2, r*(maxh+4)+2))
    sheet.save(f"{OUT}/_contact.png")
    print(f"contact sheet: {OUT}/_contact.png")

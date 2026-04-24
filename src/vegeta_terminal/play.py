"""Interactive Vegeta — walks around your terminal.

Controls
--------
arrow keys / hjkl   move Vegeta
space               power-up (flares aura, triggers hype quote)
t                   taunt (random quote)
mouse drag          pick up and move him
q / ESC             quit
"""

import curses
import time
import random

from PIL import Image

from .core import (
    HERO_QUOTES,
    POSES,
    QUOTES,
    load_frame,
)

FPS = 15
FRAME_DT = 1.0 / FPS


class Sprite:
    def __init__(self, frames, scale=1):
        self.tiles = [self._tilize(f, scale) for f in frames]
        ref = frames[0].resize(
            (frames[0].width * scale, frames[0].height * scale), Image.NEAREST
        )
        self.w = ref.width
        self.h = (ref.height + 1) // 2  # rows of half-blocks

    def _tilize(self, img, scale):
        if scale > 1:
            img = img.resize(
                (img.width * scale, img.height * scale), Image.NEAREST
            )
        w, h = img.size
        if h % 2:
            new = Image.new("RGBA", (w, h + 1), (0, 0, 0, 0))
            new.paste(img, (0, 0))
            img = new
            h += 1
        px = img.load()
        tiles = []
        for y in range(0, h, 2):
            row = y // 2
            for x in range(w):
                tp = px[x, y]
                bp = px[x, y + 1]
                tt = tp[3] < 64
                bt = bp[3] < 64
                if tt and bt:
                    continue
                if tt:
                    tiles.append((row, x, "▄", bp[:3], None))
                elif bt:
                    tiles.append((row, x, "▀", tp[:3], None))
                else:
                    tiles.append((row, x, "▀", tp[:3], bp[:3]))
        return tiles


class ColorPool:
    """Curses dynamic color allocator.

    Maps (r,g,b) fg + optional (r,g,b) bg → color pair.
    """

    def __init__(self):
        self.colors = {}
        self.pairs = {}
        self.color_next = 16
        self.pair_next = 1
        self.max_colors = (
            min(curses.COLORS, 256) if hasattr(curses, "COLORS") else 256
        )
        self.max_pairs = (
            min(curses.COLOR_PAIRS, 256) if hasattr(curses, "COLOR_PAIRS") else 256
        )
        self.default_bg = -1
        try:
            curses.use_default_colors()
        except Exception:
            self.default_bg = curses.COLOR_BLACK

    def _color_idx(self, rgb):
        if rgb is None:
            return self.default_bg
        if rgb in self.colors:
            return self.colors[rgb]
        if self.color_next >= self.max_colors:
            best, bd = self.default_bg, 10**9
            for c, idx in self.colors.items():
                d = (c[0] - rgb[0]) ** 2 + (c[1] - rgb[1]) ** 2 + (c[2] - rgb[2]) ** 2
                if d < bd:
                    bd, best = d, idx
            return best
        idx = self.color_next
        self.color_next += 1
        try:
            curses.init_color(
                idx,
                int(rgb[0] * 1000 / 255),
                int(rgb[1] * 1000 / 255),
                int(rgb[2] * 1000 / 255),
            )
        except curses.error:
            return curses.COLOR_WHITE
        self.colors[rgb] = idx
        return idx

    def pair(self, fg_rgb, bg_rgb):
        fi = self._color_idx(fg_rgb)
        bi = self._color_idx(bg_rgb)
        key = (fi, bi)
        if key in self.pairs:
            return curses.color_pair(self.pairs[key])
        if self.pair_next >= self.max_pairs:
            return curses.A_NORMAL
        idx = self.pair_next
        self.pair_next += 1
        try:
            curses.init_pair(idx, fi, bi)
        except curses.error:
            return curses.A_NORMAL
        self.pairs[key] = idx
        return curses.color_pair(idx)


def draw_sprite(win, sprite, frame_idx, row, col, flip, pool, maxy, maxx):
    tiles = sprite.tiles[frame_idx % len(sprite.tiles)]
    w = sprite.w
    for r, c, ch, fg_c, bg_c in tiles:
        x = col + (w - 1 - c if flip else c)
        y = row + r
        if 0 <= y < maxy and 0 <= x < maxx:
            try:
                win.addstr(y, x, ch, pool.pair(fg_c, bg_c))
            except curses.error:
                pass


def draw_bubble(win, text, row, col, maxy, maxx):
    words = text.split()
    lines, cur = [], ""
    W = min(44, maxx - col - 4)
    if W < 10:
        return
    for w in words:
        if len(cur) + len(w) + 1 <= W:
            cur = (cur + " " + w).strip()
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    w = max(len(l) for l in lines)
    top = "╭" + "─" * (w + 2) + "╮"
    bot = "╰" + "─" * (w + 2) + "╯"
    rows = [top] + ["│ " + l.ljust(w) + " │" for l in lines] + [bot, " ◣"]
    for i, line in enumerate(rows):
        y = row + i
        if 0 <= y < maxy and col >= 0 and col + len(line) < maxx:
            try:
                win.addstr(y, col, line)
            except curses.error:
                pass


def play():
    def _main(stdscr):
        curses.curs_set(0)
        stdscr.nodelay(True)
        stdscr.keypad(True)
        try:
            curses.mousemask(
                curses.ALL_MOUSE_EVENTS | curses.REPORT_MOUSE_POSITION
            )
            print("\x1b[?1003h", end="", flush=True)
        except Exception:
            pass

        pool = ColorPool()

        scale = 2
        idle = Sprite([load_frame(i) for i in [10, 11]], scale=scale)
        walk = Sprite([load_frame(i) for i in [43, 44, 45, 46]], scale=scale)
        # "super" is the power-up pose group
        powerup = Sprite(
            [load_frame(i) for i in POSES["super"]], scale=scale
        )

        maxy, maxx = stdscr.getmaxyx()
        y = maxy - idle.h - 1
        x = maxx // 2 - idle.w // 2
        vx = 1
        flip = False
        state = "walk"
        state_frame = 0
        state_timer = 0
        anim_timer = 0.0
        auto_walk = True
        quote = None
        quote_until = 0
        quote_x = x
        dragging = False
        drag_offset = (0, 0)
        tick = 0

        next_auto_quote = time.time() + random.uniform(12, 25)

        def say(q, dur=3.5):
            nonlocal quote, quote_until, quote_x
            quote = q
            quote_until = time.time() + dur
            quote_x = x

        last_time = time.time()
        while True:
            now = time.time()
            dt = now - last_time
            last_time = now
            tick += 1

            maxy, maxx = stdscr.getmaxyx()

            # Input
            try:
                ch = stdscr.getch()
            except Exception:
                ch = -1
            while ch != -1:
                if ch in (ord("q"), 27):
                    return
                elif ch == curses.KEY_LEFT or ch == ord("h"):
                    x -= 2
                    flip = True
                    auto_walk = False
                    if state != "walk":
                        state = "walk"
                        state_frame = 0
                elif ch == curses.KEY_RIGHT or ch == ord("l"):
                    x += 2
                    flip = False
                    auto_walk = False
                    if state != "walk":
                        state = "walk"
                        state_frame = 0
                elif ch == curses.KEY_UP or ch == ord("k"):
                    y -= 1
                    auto_walk = False
                    if state == "powerup":
                        state = "walk"
                        state_frame = 0
                elif ch == curses.KEY_DOWN or ch == ord("j"):
                    y += 1
                    auto_walk = False
                    if state == "powerup":
                        state = "walk"
                        state_frame = 0
                elif ch == ord(" "):
                    state = "powerup"
                    state_frame = 0
                    state_timer = now
                    say(random.choice(HERO_QUOTES), dur=3.0)
                elif ch == ord("t"):
                    say(random.choice(QUOTES), dur=3.5)
                elif ch == ord("a"):
                    auto_walk = True
                    state = "walk"
                elif ch == curses.KEY_MOUSE:
                    try:
                        _, mx, my, _, bstate = curses.getmouse()
                    except curses.error:
                        ch = -1
                        continue
                    inside = x <= mx < x + idle.w and y <= my < y + idle.h
                    if bstate & curses.BUTTON1_PRESSED and inside:
                        dragging = True
                        drag_offset = (mx - x, my - y)
                        auto_walk = False
                    elif bstate & curses.BUTTON1_RELEASED:
                        dragging = False
                    elif dragging:
                        x = mx - drag_offset[0]
                        y = my - drag_offset[1]
                try:
                    ch = stdscr.getch()
                except Exception:
                    ch = -1

            # State machine
            if state == "powerup":
                if now - state_timer > 0.12:
                    state_frame += 1
                    state_timer = now
                if state_frame >= len(powerup.tiles):
                    state = "walk"
                    state_frame = 0
                    anim_timer = now
            else:
                if now - anim_timer > 0.125:
                    state_frame += 1
                    anim_timer = now

            cur_sp = (
                powerup
                if state == "powerup"
                else (walk if (auto_walk or state == "walk") else idle)
            )

            # Auto-walk
            if auto_walk and state != "powerup":
                if tick % 2 == 0:
                    x += vx
                if x < 0:
                    x = 0
                    vx = 1
                    flip = False
                if x + cur_sp.w > maxx:
                    x = maxx - cur_sp.w
                    vx = -1
                    flip = True

            # Clamp
            x = max(0, min(maxx - cur_sp.w, x))
            y = max(0, min(maxy - cur_sp.h - 1, y))

            # Random taunt
            if now >= next_auto_quote and (
                quote is None or now > quote_until
            ):
                say(random.choice(QUOTES), dur=3.5)
                next_auto_quote = now + random.uniform(14, 28)

            # Render
            stdscr.erase()
            hint = " arrows/hjkl move · space powerup · t taunt · a auto-walk · q quit "
            try:
                stdscr.addstr(maxy - 1, 0, hint[: maxx - 1], curses.A_DIM)
            except curses.error:
                pass

            sp = cur_sp
            fi = state_frame

            draw_sprite(stdscr, sp, fi, y, x, flip, pool, maxy, maxx)

            if quote and now <= quote_until:
                by = max(0, y - 6)
                bx = min(max(0, x + sp.w + 1), maxx - 10)
                draw_bubble(stdscr, quote, by, bx, maxy, maxx)
            else:
                quote = None

            stdscr.refresh()

            sleep = FRAME_DT - (time.time() - now)
            if sleep > 0:
                time.sleep(sleep)

    try:
        curses.wrapper(_main)
    finally:
        print("\x1b[?1003l", end="", flush=True)

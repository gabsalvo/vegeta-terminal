"""Core rendering engine — sprite→text conversion, speech bubbles, animation."""

import os
import sys
import random
import time
import shutil
import glob

from PIL import Image

# Frame assets live alongside this module inside the installed package.
FRAMES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frames")

# ---------------------------------------------------------------------------
# Coherent animation cycles — each list is a run of consecutive frames that
# together form ONE motion from the sprite sheet.  Do not mix frames across
# groups; pick a group and play it end-to-end.
# ---------------------------------------------------------------------------
POSES = {
    "stance_a":   list(range(1, 15)),      # 1..14  — idle / breathing cycle
    "stance_b":   list(range(19, 31)),     # 19..30 — alt stance cycle
    "charge":     [15, 16, 17, 18],        # charging up
    "crouch":     list(range(33, 38)),     # 33..37
    "step":       list(range(39, 43)),     # 39..42
    "dash":       list(range(43, 50)),     # 43..49
    "super":      [64, 65],                # full power-up pose
    "recover":    list(range(66, 72)),     # 66..71
    "punch":      list(range(86, 95)),     # 86..94
    "land":       list(range(100, 105)),   # 100..104
    "pose":       list(range(110, 116)),   # 110..115
}

# Which groups are "greeting-appropriate" vs hero / power moments
GREET_POSES = ["stance_a", "stance_b", "step", "crouch", "pose"]
HERO_POSES  = ["charge", "super", "punch", "dash"]

# ---------------------------------------------------------------------------
# Motivational quotes
# ---------------------------------------------------------------------------
QUOTES = [
    "Stand up! A prince doesn't kneel before his keyboard!",
    "Push beyond your limits! Break the ceiling!",
    "I am the prince of all Saiyans — and you are my protégé!",
    "Stop making excuses! Train harder!",
    "Kakarot already shipped his feature. What about you?",
    "Your power level is rising. I can feel it.",
    "Pain is temporary. Glory is eternal. Now compile!",
    "You think this bug is hard? Face Frieza without senzu beans.",
    "A true warrior writes tests. Now write them.",
    "Stop scrolling. Start shipping.",
    "The meek inherit nothing. The bold inherit everything.",
    "If you're not going to give it your all, why bother at all?",
    "Your focus determines your reality. Focus now.",
    "One more commit. One more rep. One more push.",
    "I did not come this far to only come this far. Neither did you.",
    "Rivals are gifts. They force you to ascend.",
    "Stop whining about the linter and fix your code.",
    "Power comes from struggle. Struggle today.",
    "The best code is written by those who refuse to lose.",
    "Discipline. Every. Single. Day.",
]

HERO_QUOTES = [
    "It's over 9000!!! — go conquer your day.",
    "I am the hype you need. Now go.",
    "Final Flash! — that's you shipping today's work.",
    "Galick Gun! — fire at every problem on your list.",
]

# ---------------------------------------------------------------------------
# ANSI true-color rendering
# ---------------------------------------------------------------------------

ESC = "\x1b["

def fg(r, g, b):
    return f"{ESC}38;2;{r};{g};{b}m"

def bg(r, g, b):
    return f"{ESC}48;2;{r};{g};{b}m"

RESET = f"{ESC}0m"


def render_sprite(img, scale=1, bg_color=None):
    """Render a PIL RGBA image as truecolor half-block text.

    Parameters
    ----------
    scale : int
        Integer up-scale factor (nearest-neighbor).
    bg_color : tuple[int,int,int] | None
        Terminal bg color for transparent pixels; ``None`` uses the ANSI
        default background.

    Returns
    -------
    list[str]
        Lines of ANSI-colored text (without trailing newline).
    """
    if scale != 1:
        img = img.resize(
            (max(1, int(img.width * scale)), max(1, int(img.height * scale))),
            Image.NEAREST,
        )
    w, h = img.size
    # Pad to even height
    if h % 2:
        new = Image.new("RGBA", (w, h + 1), (0, 0, 0, 0))
        new.paste(img, (0, 0))
        img = new
        h += 1
    px = img.load()
    lines = []
    for y in range(0, h, 2):
        line = []
        for x in range(w):
            tp = px[x, y]
            bp = px[x, y + 1]
            top_t = tp[3] < 64
            bot_t = bp[3] < 64
            if top_t and bot_t:
                line.append(RESET + " ")
                continue
            if top_t:
                line.append(f"{RESET}{fg(bp[0], bp[1], bp[2])}▄")
                continue
            if bot_t:
                line.append(f"{RESET}{fg(tp[0], tp[1], tp[2])}▀")
                continue
            line.append(f"{fg(tp[0], tp[1], tp[2])}{bg(bp[0], bp[1], bp[2])}▀")
        line.append(RESET)
        lines.append("".join(line))
    return lines


def load_frame(idx):
    """Load a single frame PNG by index and return an RGBA PIL Image."""
    path = os.path.join(FRAMES_DIR, f"frame_{idx:03d}.png")
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    return Image.open(path).convert("RGBA")


# ---------------------------------------------------------------------------
# Speech bubble
# ---------------------------------------------------------------------------

def wrap(text, width):
    words = text.split()
    out, cur = [], ""
    for w in words:
        if len(cur) + len(w) + 1 <= width:
            cur = (cur + " " + w).strip()
        else:
            if cur:
                out.append(cur)
            cur = w
    if cur:
        out.append(cur)
    return out


def bubble(text, max_width=40):
    lines = wrap(text, max_width)
    w = max(len(l) for l in lines)
    top = "  ╭" + "─" * (w + 2) + "╮"
    bot = "  ╰" + "─" * (w + 2) + "╯"
    tail = "   ◣"
    body = ["  │ " + l.ljust(w) + " │" for l in lines]
    return [top] + body + [bot, tail]


# ---------------------------------------------------------------------------
# Animation helpers
# ---------------------------------------------------------------------------

def _render_centered_sequence(frames, target_h):
    """Render pose frames on a fixed-size canvas, each anchored at
    center-x and feet-to-bottom.  Keeps Vegeta rooted in one spot
    across frames of varying widths/heights (no jitter)."""
    max_h = max(f.height for f in frames)
    max_w = max(f.width for f in frames)
    scale = max(1, target_h // max_h)
    scaled = [
        f.resize((f.width * scale, f.height * scale), Image.NEAREST)
        for f in frames
    ]
    term_cols = shutil.get_terminal_size().columns
    canvas_w = min(max(term_cols - 6, 20), max(s.width for s in scaled) + 6)
    canvas_h = max(s.height for s in scaled) + 2
    renders = []
    for s in scaled:
        canvas = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
        x = (canvas_w - s.width) // 2
        y = canvas_h - s.height
        canvas.paste(s, (x, y), s)
        renders.append(render_sprite(canvas, scale=1))
    h = max(len(r) for r in renders)
    renders = [r + [""] * (h - len(r)) for r in renders]
    return renders, h


def _play_animation(renders, h, delay=0.18):
    """Play an in-place animation, clearing each line before redraw."""
    sys.stdout.write("\x1b[?25l")
    try:
        for n, r in enumerate(renders):
            if n > 0:
                sys.stdout.write(f"\x1b[{h}A")
            for line in r:
                sys.stdout.write("\r\x1b[2K  " + line + "\n")
            sys.stdout.flush()
            time.sleep(delay)
    finally:
        sys.stdout.write("\x1b[?25h")
        sys.stdout.flush()


def _play_galick_gun(target_h=20, delay=0.09):
    """Galick Gun — SSJ Vegeta cups the energy at his hip (086, 089-093),
    thrusts both hands forward (094), holds the pose, then fires a continuous
    beam that extends rightward to the edge of the terminal."""
    charge_imgs = [load_frame(i) for i in (86, 89, 90, 91, 92, 93)]
    fire_img = load_frame(94)
    burst = load_frame(96)
    head = load_frame(97)

    term_cols = shutil.get_terminal_size().columns
    canvas_w = max(40, term_cols - 6)

    target_px = target_h * 2
    ps_h = max(1, round(target_px / fire_img.height))
    ps_w = max(1, canvas_w // (fire_img.width * 2))
    ps = max(1, min(ps_h, ps_w))

    def up(im, s=ps):
        return im.resize(
            (max(1, im.width * s), max(1, im.height * s)), Image.NEAREST
        )

    fire_s = up(fire_img)
    charge_s = [up(im) for im in charge_imgs]

    beam_h = max(6, int(fire_s.height * 0.35))

    def fit_h(im, h):
        new_w = max(1, int(im.width * h / im.height))
        return im.resize((new_w, h), Image.NEAREST)

    head_s = fit_h(head, beam_h)
    burst_s = fit_h(burst, int(beam_h * 1.6))

    canvas_h = max(fire_s.height, burst_s.height) + 2

    hand_x = fire_s.width - max(2, ps * 2)
    hand_y = canvas_h - int(fire_s.height * 0.60)

    def composite(pose_img, extras):
        canvas = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
        canvas.paste(pose_img, (0, canvas_h - pose_img.height), pose_img)
        for img, x, y in extras:
            if x + img.width > 0 and x < canvas_w:
                canvas.paste(img, (x, y), img)
        return canvas

    mid_x = head_s.width // 2
    strip_w = max(2, ps * 2)
    body_strip = head_s.crop(
        (mid_x - strip_w // 2, 0, mid_x + strip_w // 2, head_s.height)
    )
    body_y = hand_y - body_strip.height // 2
    head_y = hand_y - head_s.height // 2

    def build_body(length):
        body = Image.new("RGBA", (length, body_strip.height), (0, 0, 0, 0))
        x = 0
        while x < length:
            body.paste(body_strip, (x, 0), body_strip)
            x += body_strip.width
        return body

    frames = []

    # Phase 1 — charge
    for _ in range(2):
        for im in charge_s:
            frames.append(composite(im, []))

    # Phase 2 — firing pose held
    for _ in range(3):
        frames.append(composite(fire_s, []))

    # Phase 3 — burst bloom
    burst_x = hand_x - burst_s.width // 3
    burst_y = hand_y - burst_s.height // 2
    frames.append(composite(fire_s, [(burst_s, burst_x, burst_y)]))
    frames.append(composite(fire_s, [(burst_s, burst_x, burst_y)]))

    # Phase 4 — continuous beam
    start_x = hand_x
    end_x = canvas_w - head_s.width // 2
    span = max(1, end_x - start_x)
    dx = max(1, span // 18)
    hx = start_x
    while hx <= end_x:
        extras = []
        body_len = hx - hand_x
        if body_len > 0:
            extras.append((build_body(body_len), hand_x, body_y))
        extras.append((head_s, hx - head_s.width // 2, head_y))
        frames.append(composite(fire_s, extras))
        hx += dx

    # Hold final full-length beam
    frames.append(frames[-1])
    frames.append(frames[-1])

    renders = [render_sprite(f, scale=1) for f in frames]
    h = max(len(r) for r in renders)
    renders = [r + [""] * (h - len(r)) for r in renders]
    _play_animation(renders, h, delay=delay)

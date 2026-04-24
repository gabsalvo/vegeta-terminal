"""CLI entry point — ``vegeta`` command."""

import argparse
import glob
import os
import random
import shutil

from PIL import Image

from .core import (
    FRAMES_DIR,
    GREET_POSES,
    HERO_POSES,
    HERO_QUOTES,
    POSES,
    QUOTES,
    _play_animation,
    _play_galick_gun,
    _render_centered_sequence,
    bubble,
    load_frame,
    render_sprite,
)


def _resolve_group(forced, hero_prob):
    """Pick a pose group.  If *forced* matches a known group, use it;
    otherwise roll a hero / greet choice with the given hero probability."""
    if forced and forced in POSES:
        is_hero = forced in HERO_POSES
        return forced, is_hero
    if random.random() < hero_prob:
        return random.choice(HERO_POSES), True
    return random.choice(GREET_POSES), False


def cmd_greet(args):
    forced = getattr(args, "pose", None)
    group, is_hero = _resolve_group(forced, hero_prob=0.5)
    quote = random.choice(HERO_QUOTES if is_hero else QUOTES)
    bub = bubble(quote, max_width=min(40, shutil.get_terminal_size().columns - 16))
    for line in bub:
        print(line)
    print()
    if group == "beam":
        _play_galick_gun(target_h=20)
        print()
        return
    # Only use frames that actually exist on disk
    pool = [
        i
        for i in POSES[group]
        if os.path.exists(os.path.join(FRAMES_DIR, f"frame_{i:03d}.png"))
    ]
    if not pool:
        pool = POSES["stance_a"]
    frames = [load_frame(i) for i in pool]
    renders, h = _render_centered_sequence(frames, target_h=20)
    _play_animation(renders, h)
    print()


def cmd_powerup(args):
    """Play the power-up animation in place."""
    forced = getattr(args, "pose", None)
    if forced and forced in POSES:
        group = forced
    else:
        group = random.choice(HERO_POSES)
    if group == "beam":
        _play_galick_gun(target_h=36)
        quote = random.choice(HERO_QUOTES)
        for line in bubble(quote):
            print(line)
        return
    seq = [
        i
        for i in POSES[group]
        if os.path.exists(os.path.join(FRAMES_DIR, f"frame_{i:03d}.png"))
    ]
    frames = [load_frame(i) for i in seq]
    renders, h = _render_centered_sequence(frames, target_h=36)
    _play_animation(renders, h)
    quote = random.choice(HERO_QUOTES)
    for line in bubble(quote):
        print(line)


def cmd_list(args):
    files = sorted(glob.glob(f"{FRAMES_DIR}/frame_*.png"))
    for f in files:
        im = Image.open(f)
        idx = int(os.path.basename(f).split("_")[1].split(".")[0])
        print(f"  #{idx:3d}  {im.size[0]:3d}x{im.size[1]:3d}  {os.path.basename(f)}")
    print(f"\nCurated sets: {', '.join(POSES.keys())}")


def cmd_show(args):
    idx = args.index
    img = load_frame(idx)
    scale = max(1, 30 // img.height)
    for line in render_sprite(img, scale=scale):
        print(line)
    print(f"frame #{idx}  {img.size[0]}x{img.size[1]}  scale={scale}")


def main():
    p = argparse.ArgumentParser(
        prog="vegeta",
        description="Vegeta — your terminal motivator.",
        epilog=(
            "Pose groups: stance_a, stance_b, charge, crouch, step, "
            "dash, super, recover, punch, land, pose"
        ),
    )
    sub = p.add_subparsers(dest="cmd")

    g = sub.add_parser("greet", help="Random pose + motivational quote")
    g.add_argument("pose", nargs="?", default=None)

    pu = sub.add_parser("powerup", help="Full power-up animation")
    pu.add_argument("pose", nargs="?", default=None)

    sub.add_parser("list", help="Show all available frames")

    s = sub.add_parser("show", help="Render a single frame")
    s.add_argument("index", type=int)

    sub.add_parser("play", help="Interactive mode (arrows to move, q to quit)")

    args = p.parse_args()
    cmd = args.cmd or "greet"
    if cmd == "greet":
        cmd_greet(args)
    elif cmd == "powerup":
        cmd_powerup(args)
    elif cmd == "list":
        cmd_list(args)
    elif cmd == "show":
        cmd_show(args)
    elif cmd == "play":
        from .play import play

        play()

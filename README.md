# 🔥 Vegeta Terminal

> *"Stand up! A prince doesn't kneel before his keyboard!"*

**Vegeta Terminal** is a pixel-art animated terminal companion that drops
motivational Dragon Ball quotes, powers up with full sprite animations,
and even walks around your terminal in interactive mode.

Because every developer deserves a Saiyan prince watching over their code.

---

## ✨ Features

| Command | What it does |
|---------|-------------|
| `vegeta` | Random greeting — pose + motivational quote |
| `vegeta greet [pose]` | Greet with an optional pose group |
| `vegeta powerup [pose]` | Full power-up animation |
| `vegeta play` | **Interactive mode** — walk him around, power up, drag with mouse |
| `vegeta list` | Show all available frames |
| `vegeta show <N>` | Render a single frame at large scale |

### Available Pose Groups

`stance_a` · `stance_b` · `charge` · `crouch` · `step` · `dash` ·
`super` · `recover` · `punch` · `land` · `pose`

---

## 📦 Installation

### From PyPI (when published)

```bash
pip install vegeta-terminal
```

### From source

```bash
git clone https://github.com/gabrielesalvo/vegeta-terminal.git
cd vegeta-terminal
pip install .
```

### Development install

```bash
pip install -e .
```

After installation the `vegeta` command is available system-wide.

---

## 🎮 Interactive Mode

```bash
vegeta play
```

| Key | Action |
|-----|--------|
| Arrow keys / `hjkl` | Move Vegeta |
| `Space` | Power up (aura + hype quote) |
| `t` | Taunt (random quote) |
| `a` | Toggle auto-walk |
| Mouse drag | Pick him up and move him |
| `q` / `ESC` | Quit |

---

## 🖥️ Requirements

- **Python** ≥ 3.9
- **Pillow** ≥ 9.0
- A terminal with **true-color** (24-bit) support — works great in kitty,
  iTerm2, WezTerm, Windows Terminal, Alacritty, and most modern terminals.

---

## 🏗️ Project Structure

```
vegeta-terminal/
├── pyproject.toml              # Package metadata & build config
├── LICENSE                     # MIT + Dragon Ball disclaimer
├── README.md
└── src/
    └── vegeta_terminal/
        ├── __init__.py
        ├── cli.py              # CLI entry point (vegeta command)
        ├── core.py             # Sprite rendering, animation engine
        ├── play.py             # Interactive curses mode
        └── frames/             # 131 sprite PNGs
            ├── frame_000.png
            ├── frame_001.png
            └── ...
```

---

## 📜 License

This project is licensed under the **MIT License** — see [LICENSE](LICENSE)
for details.

### ⚠️ Dragon Ball Disclaimer

Dragon Ball, Vegeta, and all related characters, names, and imagery are the
intellectual property of **Bird Studio / Shueisha**, **Toei Animation**, and
the estate of **Akira Toriyama** (鳥山 明, 1955 – 2024).

This project is an **unofficial, non-commercial fan tribute**. The authors
do not own, claim ownership of, nor profit from any Dragon Ball intellectual
property. The sprite artwork is used solely for personal, educational, and
entertainment purposes.

---

## 💛 In Memory of Akira Toriyama

We are forever grateful to Toriyama-sensei for the incredible universe he
created. His work inspired generations of fans, artists, and developers
around the world — including this little terminal companion.

Rest in peace. Your legacy lives on in every Kamehameha, every Final Flash,
and every kid who believed they could go Super Saiyan. 🐉

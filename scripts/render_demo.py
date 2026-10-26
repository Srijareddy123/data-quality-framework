"""Render the output of `python -m dqf.demo` as docs/demo.png (a picture of real output)."""

import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
FONT = "/System/Library/Fonts/Menlo.ttc"


def main() -> None:
    out = subprocess.run(
        [sys.executable, "-m", "dqf.demo"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        env={"PYTHONPATH": "src", "PATH": "/usr/bin:/bin"},
        check=True,
    ).stdout
    lines = ["$ make demo", *out.rstrip().splitlines()]
    font = ImageFont.truetype(FONT, 16)
    width = max(int(font.getlength(line)) for line in lines) + 48
    height = 24 * len(lines) + 40
    img = Image.new("RGB", (width, height), "#16181d")
    draw = ImageDraw.Draw(img)
    for i, line in enumerate(lines):
        color = "#8bd5a0" if i == 0 else "#e6e6e6"
        if " failed " in line:
            color = "#f28b82"
        elif " warning " in line:
            color = "#f2c46d"
        draw.text((24, 20 + 24 * i), line, font=font, fill=color)
    target = ROOT / "docs" / "demo.png"
    target.parent.mkdir(exist_ok=True)
    img.save(target)
    print(f"wrote {target}")


if __name__ == "__main__":
    main()

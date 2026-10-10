"""Regenerate the synthetic OCR fixture with Pillow and a local Arial font."""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


if __name__ == "__main__":
    image = Image.new("RGB", (600, 140), "white")
    ImageDraw.Draw(image).text((30, 35), "HELLO", font=ImageFont.truetype("arial.ttf", 48), fill="black")
    image.save(Path(__file__).with_name("scan.png"))

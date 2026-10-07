from pathlib import Path

from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter


output = Path("tests/fixtures/hybrid.pdf")
output.parent.mkdir(parents=True, exist_ok=True)

c = canvas.Canvas(str(output), pagesize=letter)

# Page 1 — real selectable text
c.setFont("Helvetica", 14)
c.drawString(72, 700, "HYBRID TEST - TEXT PAGE")
c.drawString(72, 670, "This page should be extracted using pypdf.")
c.showPage()

# Page 2 — image-only page
image = Image.new("RGB", (1200, 800), "white")

from PIL import ImageDraw, ImageFont

draw = ImageDraw.Draw(image)
draw.text((100, 200), "HYBRID TEST - OCR PAGE", fill="black")
draw.text((100, 260), "This page should be extracted using OCR.", fill="black")

image_path = Path("tests/fixtures/hybrid_page.png")
image.save(image_path)

c.drawImage(
    str(image_path),
    0,
    0,
    width=letter[0],
    height=letter[1],
)
c.showPage()

c.save()

print(f"Created {output}")
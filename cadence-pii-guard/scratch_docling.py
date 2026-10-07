from pathlib import Path
from docling.document_converter import DocumentConverter

PDF_PATH = Path(r"C:\Users\ivang\Optiv\cadence-pii-guard\tests\fixtures\text.pdf")

converter = DocumentConverter()

result = converter.convert(PDF_PATH)

print("Conversion complete.")
print(result.document.export_to_markdown()[:2000])
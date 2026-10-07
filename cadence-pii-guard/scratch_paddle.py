from pathlib import Path
from paddleocr import PaddleOCR
from pdf2image import convert_from_path
import os
# Disable the buggy oneDNN engine optimizations entirely
os.environ["FLAGS_use_onednn"] = "0"
os.environ["PADDLE_DISABLE_ONEDNN"] = "True"

# Optional: Bypasses network version verification lookups to speed things up
os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"

# Your remaining script continues below...
from paddleocr import PaddleOCR
# ... rest of your code


PDF_PATH = Path(
    r"C:\Users\ivang\Optiv\Cadence_Group_Risk_Management_Policy__v6.0.pdf"
)

def main():
    print("Rendering first page...")

    images = convert_from_path(
        str(PDF_PATH),
        first_page=1,
        last_page=1,
        dpi=200,
    )

    image_path = Path("scratch_page.png")
    images[0].save(image_path)

    print("Initializing PaddleOCR...")

    ocr = PaddleOCR(
        lang="en",
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=False,
    )

    print("Running OCR...")

    result = ocr.predict(str(image_path))

    for res in result:
        print(res)

if __name__ == "__main__":
    main()
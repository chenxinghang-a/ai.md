from pypdf import PdfReader
from PIL import Image
import io

# Try to extract images from PDF
pdf_path = r"C:\Users\cxx\WorkBuddy\2026-07-05-22-13-37\training_table.pdf"
reader = PdfReader(pdf_path)

print(f"Pages: {len(reader.pages)}")

for i, page in enumerate(reader.pages):
    print(f"\nPage {i+1} images: {len(page.images)}")
    for j, img in enumerate(page.images):
        print(f"  Image {j}: {img.name}, size: {img.width}x{img.height}")
        # Save image
        img_data = img.data
        ext = img.name.split('.')[-1] if '.' in (img.name or '') else 'png'
        out_path = f"page{i+1}_img{j}.{ext}"
        with open(out_path, 'wb') as f:
            f.write(img_data)
        print(f"  Saved to {out_path}")

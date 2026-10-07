import sys
sys.stdout.reconfigure(encoding='utf-8')

from pypdf import PdfReader

pdf_path = r"C:\Users\cxx\WorkBuddy\2026-07-05-22-13-37\training_table.pdf"
reader = PdfReader(pdf_path)
print(f"PDF pages: {len(reader.pages)}")
print("=" * 60)

for i, page in enumerate(reader.pages):
    print(f"\n--- Page {i+1} ---")
    text = page.extract_text()
    if text:
        print(text)
    else:
        print("[No text extracted]")

"""更好的DOC解析 - 尝试多种方式"""
import sys
sys.path.insert(0, r"C:\Users\cxx\.workbuddy\binaries\python\versions\3.14.3\Lib\site-packages")

doc_path = r"C:\Users\cxx\Documents\xwechat_files\wxid_dn3b6rwdvyjd22_e1ed\msg\attach\8c45a45ed3aace6b261a05a8c2e2ee71\2026-07\Rec\7ae521a44fab2421\F\1\电子线路装调实训指导书.doc"
pdf_path = r"C:\Users\cxx\Documents\xwechat_files\wxid_dn3b6rwdvyjd22_e1ed\msg\attach\8c45a45ed3aace6b261a05a8c2e2ee71\2026-07\Rec\7ae521a44fab2421\F\0\实训表格.pdf"

# ---- 方法1: 尝试python-docx (可能实际是docx) ----
print("="*60)
print("方法1: python-docx")
print("="*60)
try:
    from docx import Document
    doc = Document(doc_path)
    for i, para in enumerate(doc.paragraphs):
        if para.text.strip():
            print(f"[P{i}] {para.text.strip()}")
    
    # 表格
    for ti, table in enumerate(doc.tables):
        print(f"\n[表格{ti}]")
        for ri, row in enumerate(table.rows):
            cells = [cell.text.strip() for cell in row.cells]
            print(f"  R{ri}: {' | '.join(cells)}")
except Exception as e:
    print(f"python-docx失败: {e}")

# ---- 方法2: olefile + 更干净的提取 ----
print("\n" + "="*60)
print("方法2: olefile (提取WordDocument中的可读文本)")
print("="*60)
try:
    import olefile
    import struct
    ole = olefile.OleFileIO(doc_path)
    
    # List all streams
    print("OLE streams:", ole.listdir())
    
    # Try 1Table or 0Table stream (contains text in newer Word docs)
    for stream_name in ['1Table', '0Table', 'WordDocument']:
        if ole.exists(stream_name):
            data = ole.openstream(stream_name).read()
            print(f"\n--- {stream_name}: {len(data)} bytes ---")
            
            # Extract all printable ASCII strings >= 3 chars
            import re
            # GBK strings
            text = b''
            i = 0
            while i < len(data) - 1:
                b = data[i]
                if 0x81 <= b <= 0xFE and i+1 < len(data):
                    if 0x40 <= data[i+1] <= 0xFE:
                        text += data[i:i+2]
                        i += 2
                        continue
                if 0x20 <= b <= 0x7E:
                    text += bytes([b])
                elif b in (0x0D, 0x0A):
                    text += bytes([b])
                i += 1
            
            # Decode GBK
            try:
                decoded = text.decode('gbk', errors='replace')
                # Clean up: remove runs of replacement chars
                decoded = re.sub(r'[^\u4e00-\u9fff\u3000-\u303f\uff00-\uffefa-zA-Z0-9\s\.\,\;\:\!\?\-\+\=\(\)\[\]\{\}\/\\\>\<\@\#\$\%\^\&\*\_\~\`\'\"]+', ' ', decoded)
                decoded = re.sub(r'\s{2,}', '\n', decoded)
                lines = [l.strip() for l in decoded.split('\n') if len(l.strip()) > 3]
                for l in lines[:200]:
                    print(l)
            except:
                pass
    
    ole.close()
except Exception as e:
    print(f"olefile失败: {e}")

# ---- 方法3: PDF图像检查 ----
print("\n" + "="*60)
print("方法3: PDF检查(是否扫描件)")
print("="*60)
try:
    from pypdf import PdfReader
    reader = PdfReader(pdf_path)
    print(f"PDF页数: {len(reader.pages)}")
    for i, page in enumerate(reader.pages):
        print(f"\n第{i+1}页:")
        print(f"  尺寸: {page.mediabox}")
        text = page.extract_text()
        if text:
            print(f"  文字: {text[:200]}")
        else:
            print("  [无文字 - 可能是扫描件/图片]")
        
        # Check for images
        if '/XObject' in page['/Resources']:
            xobjects = page['/Resources']['/XObject']
            img_count = 0
            for obj_name in xobjects:
                obj = xobjects[obj_name]
                if obj['/Subtype'] == '/Image':
                    img_count += 1
            print(f"  图片数: {img_count}")
except Exception as e:
    print(f"PDF解析失败: {e}")

# ---- 方法4: DOC内嵌图片提取 ----
print("\n" + "="*60)
print("方法4: 尝试提取DOC中的图片")
print("="*60)
try:
    import olefile
    ole = olefile.OleFileIO(doc_path)
    
    # Word docs store images in ObjectPool or Data streams
    from pathlib import Path
    out_dir = Path(r"C:\Users\cxx\WorkBuddy\Claw\_doc_images")
    out_dir.mkdir(exist_ok=True)
    
    # Look for PNG/JPG/BMP in all streams
    img_count = 0
    for stream_info in ole.listdir():
        stream_path = '/'.join(stream_info)
        try:
            data = ole.openstream(stream_info).read()
            # Check for image signatures
            if data[:4] == b'\x89PNG':
                ext = 'png'
            elif data[:2] == b'\xff\xd8':
                ext = 'jpg'
            elif data[:2] == b'BM':
                ext = 'bmp'
            elif data[:4] == b'GIF8':
                ext = 'gif'
            elif data[:4] == b'\xd0\xcf\x11\xe0':  # OLE - skip
                continue
            else:
                # Try to find images embedded in binary data
                continue
            
            img_count += 1
            fname = f"img_{img_count}.{ext}"
            fpath = out_dir / fname
            with open(fpath, 'wb') as f:
                f.write(data)
            print(f"  提取: {fname} ({len(data)} bytes) from {stream_path}")
        except:
            pass
    
    # Also try to extract from WordDocument stream by scanning for JPEG/PNG markers
    if ole.exists('WordDocument'):
        wd_data = ole.openstream('WordDocument').read()
        
        # Scan for JPEG markers
        pos = 0
        while pos < len(wd_data) - 2:
            if wd_data[pos:pos+2] == b'\xff\xd8':
                # Find JPEG end
                end = wd_data.find(b'\xff\xd9', pos+2)
                if end > pos and end - pos > 100:
                    img_count += 1
                    fpath = out_dir / f"wd_jpg_{img_count}.jpg"
                    with open(fpath, 'wb') as f:
                        f.write(wd_data[pos:end+2])
                    print(f"  提取(WordDocument JPEG): wd_jpg_{img_count}.jpg ({end-pos+2} bytes) at offset {pos}")
                    pos = end + 2
                    continue
            elif wd_data[pos:pos+8] == b'\x89PNG\r\n\x1a\n':
                # Find PNG end (IEND chunk)
                end = wd_data.find(b'IEND\xaeB`\x82', pos+8)
                if end > pos:
                    img_count += 1
                    fpath = out_dir / f"wd_png_{img_count}.png"
                    with open(fpath, 'wb') as f:
                        f.write(wd_data[pos:end+8])
                    print(f"  提取(WordDocument PNG): wd_png_{img_count}.png ({end-pos+8} bytes)")
                    pos = end + 8
                    continue
            pos += 1
    
    ole.close()
    print(f"\n共提取 {img_count} 张图片到 {out_dir}")
    
except Exception as e:
    import traceback
    print(f"图片提取失败: {e}")
    traceback.print_exc()

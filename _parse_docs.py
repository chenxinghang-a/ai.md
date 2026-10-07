"""解析DOC指导书和PDF实训表格"""
import sys
import struct

# ---- 解析 DOC (旧格式 .doc) ----
def parse_doc_ole(filepath):
    """用olefile提取DOC文本"""
    import olefile
    ole = olefile.OleFileIO(filepath)
    
    # 方法1: 读取WordDocument流中的文本
    try:
        word_stream = ole.openstream('WordDocument')
        data = word_stream.read()
        
        # Word二进制格式：文本在FIB之后
        # 尝试提取ASCII/GBK文本
        text_parts = []
        i = 0
        while i < len(data) - 1:
            # 检测双字节中文 (GBK: 0x81-0xFE + 0x40-0xFE)
            if 0x81 <= data[i] <= 0xFE and i + 1 < len(data):
                if 0x40 <= data[i+1] <= 0xFE:
                    try:
                        ch = data[i:i+2].decode('gbk')
                        if ch.isprintable() or ch in '\n\r\t':
                            text_parts.append(ch)
                    except:
                        pass
                    i += 2
                    continue
            # ASCII
            if 0x20 <= data[i] <= 0x7E or data[i] in (0x0A, 0x0D, 0x09):
                text_parts.append(chr(data[i]))
            i += 1
        
        raw_text = ''.join(text_parts)
        
        # 清理：合并连续空格/换行
        import re
        raw_text = re.sub(r'\n{3,}', '\n\n', raw_text)
        raw_text = re.sub(r' {2,}', ' ', raw_text)
        
        # 过滤明显噪音
        lines = raw_text.split('\n')
        clean_lines = []
        for line in lines:
            stripped = line.strip()
            if len(stripped) >= 2 and not re.match(r'^[A-Za-z0-9+\-/=*_<>{}()\[\]\\|~`@#$%^&]+$', stripped):
                clean_lines.append(stripped)
        
        return '\n'.join(clean_lines)
    except Exception as e:
        return f"[OLE Stream Error] {e}"
    finally:
        ole.close()

# ---- 解析 PDF ----
def parse_pdf(filepath):
    """用pypdf提取PDF文本"""
    from pypdf import PdfReader
    reader = PdfReader(filepath)
    pages_text = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text()
        if text:
            pages_text.append(f"--- 第{i+1}页 ---\n{text}")
    return '\n\n'.join(pages_text)

# ---- 主程序 ----
if __name__ == '__main__':
    doc_path = r"C:\Users\cxx\Documents\xwechat_files\wxid_dn3b6rwdvyjd22_e1ed\msg\attach\8c45a45ed3aace6b261a05a8c2e2ee71\2026-07\Rec\7ae521a44fab2421\F\1\电子线路装调实训指导书.doc"
    pdf_path = r"C:\Users\cxx\Documents\xwechat_files\wxid_dn3b6rwdvyjd22_e1ed\msg\attach\8c45a45ed3aace6b261a05a8c2e2ee71\2026-07\Rec\7ae521a44fab2421\F\0\实训表格.pdf"
    
    print("=" * 60)
    print("【DOC指导书】")
    print("=" * 60)
    doc_text = parse_doc_ole(doc_path)
    print(doc_text[:10000])
    
    print("\n" + "=" * 60)
    print("【PDF实训表格】")
    print("=" * 60)
    pdf_text = parse_pdf(pdf_path)
    print(pdf_text[:10000])

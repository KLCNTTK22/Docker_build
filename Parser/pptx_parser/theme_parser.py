import xml.etree.ElementTree as ET
from .xml_utils import NAMESPACES

def parse_theme_to_map(xml_content):
    """
    Trích xuất bản đồ ánh xạ font chữ từ file theme*.xml.
    Trả về: {"+mn-lt": "Arial", "+mj-lt": "Calibri", ...}
    """
    theme_map = {}
    if not xml_content:
        return theme_map
    try:
        root = ET.fromstring(xml_content.encode('utf-8'))
        
        # Major Font phục vụ cho Tiêu đề (+mj-lt), Minor Font phục vụ cho Nội dung (+mn-lt)
        font_schemes = [
            ("majorFont", "mj"), 
            ("minorFont", "mn")
        ]
        
        for zone, prefix in font_schemes:
            # Truy vấn thẻ latin nằm trong font scheme của hệ thống đồ họa drawingml
            latin = root.find(f".//{{{NAMESPACES['a']}}}{zone}/{{{NAMESPACES['a']}}}latin")
            if latin is not None:
                typeface = latin.attrib.get("typeface")
                if typeface:
                    theme_map[f"+{prefix}-lt"] = typeface
                    
    except Exception as e:
        print(f"[Cảnh báo] Lỗi khi xử lý file theme xml: {e}")
        
    return theme_map
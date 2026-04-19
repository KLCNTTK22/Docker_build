from xml.etree import ElementTree as ET


def parse_theme(xml):
    """
    Phân tích theme1.xml.
    Trả về cấu trúc: { "majorFont": { "latin": "...", "ea": "...", "Jpan": "...", ... }, "minorFont": { ... } }
    """
    if not xml:
        return {}

    root = ET.fromstring(xml)
    ns = {"a": "http://schemas.openxmlformats.org/drawingml/2006/main"}
    theme = {"majorFont": {}, "minorFont": {}}

    for font_type in ["majorFont", "minorFont"]:
        font_node = root.find(f".//a:{font_type}", ns)
        if font_node is not None:

            # 1. Các font cơ bản (latin, ea, cs)
            for tag in ["latin", "ea", "cs"]:
                node = font_node.find(f"a:{tag}", ns)
                if node is not None:
                    theme[font_type][tag] = node.attrib.get("typeface")

            # 2. Các font theo Script (Jpan, Viet, Arab, Hang,...)
            for font in font_node.findall("a:font", ns):
                script = font.attrib.get("script")
                typeface = font.attrib.get("typeface")
                if script and typeface:
                    theme[font_type][script] = typeface

    return theme
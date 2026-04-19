from xml.etree import ElementTree as ET
from .xml_utils import qn, NS


def parse_styles(xml):
    if not xml:
        return {"styles": {}, "default": {}}

    root = ET.fromstring(xml)
    styles = {}
    doc_defaults = {"run": {}, "paragraph": {}}

    # 1. PARSE DOCUMENT DEFAULTS
    rPrDefault = root.find(".//w:docDefaults/w:rPrDefault/w:rPr", NS)
    if rPrDefault is not None:
        doc_defaults["run"] = parse_rPr_full(rPrDefault)

    # Có thể thêm pPrDefault ở đây nếu dự án sau này cần khoảng cách dòng mặc định

    # 2. PARSE NAMED STYLES
    for s in root.findall("w:style", NS):
        style_id = s.attrib.get(qn("w:styleId"))

        rPr = s.find("w:rPr", NS)
        based_on = s.find("w:basedOn", NS)

        styles[style_id] = {
            "type": s.attrib.get(qn("w:type")),
            "basedOn": based_on.attrib.get(qn("w:val")) if based_on is not None else None,
            "properties": parse_rPr_full(rPr)
        }

    return {
        "styles": styles,
        "default": doc_defaults
    }


def parse_rPr_full(rPr):
    """Trích xuất toàn bộ Font, Lang, và Size để phục vụ kế thừa"""
    props = {}
    if rPr is None: return props

    # --- FONT ---
    fonts = rPr.find("w:rFonts", NS)
    if fonts is not None:
        font_data = {}
        # Lấy đủ 8 loại thuộc tính khai báo font
        keys = ["ascii", "hAnsi", "cs", "eastAsia", "asciiTheme", "hAnsiTheme", "cstheme", "eastAsiaTheme"]
        for key in keys:
            val = fonts.attrib.get(qn(f"w:{key}"))
            if val: font_data[key] = val
        if font_data: props["font"] = font_data

    # --- LANG ---
    lang = rPr.find("w:lang", NS)
    if lang is not None:
        lang_data = {}
        for key in ["val", "eastAsia", "bidi"]:
            val = lang.attrib.get(qn(f"w:{key}"))
            if val: lang_data[key] = val
        if lang_data: props["lang"] = lang_data

    # --- SIZE ---
    sz = rPr.find("w:sz", NS)
    if sz is not None:
        props["fontSize"] = int(sz.attrib.get(qn("w:val"))) / 2

    return props
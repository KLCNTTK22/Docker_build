from xml.etree import ElementTree as ET
from .xml_utils import qn, NS


def parse_numbering(xml):
    """
    Phân tích numbering.xml.
    Cấu trúc trả về: { numId: { "levels": { ilvl: { "format": ..., "text": ..., "start": ... } } } }
    """
    if not xml:
        return {}

    root = ET.fromstring(xml)

    # 1. Map abstractNumId -> levels
    abstract_map = {}
    for abs_num in root.findall("w:abstractNum", NS):
        abs_id = abs_num.attrib.get(qn("w:abstractNumId"))
        levels = {}

        for lvl in abs_num.findall("w:lvl", NS):
            ilvl = lvl.attrib.get(qn("w:ilvl"))

            fmt_elem = lvl.find("w:numFmt", NS)
            txt_elem = lvl.find("w:lvlText", NS)
            start_elem = lvl.find("w:start", NS)

            levels[ilvl] = {
                "format": fmt_elem.attrib.get(qn("w:val")) if fmt_elem is not None else "decimal",
                "text": txt_elem.attrib.get(qn("w:val")) if txt_elem is not None else "",
                "start": int(start_elem.attrib.get(qn("w:val"))) if start_elem is not None else 1
            }

        abstract_map[abs_id] = {"levels": levels}

    # 2. Map numId -> levels (Phẳng hóa cấu trúc để dễ truy xuất)
    numbering = {}
    for num in root.findall("w:num", NS):
        num_id = num.attrib.get(qn("w:numId"))
        abs_link = num.find("w:abstractNumId", NS)

        if abs_link is not None:
            abs_id = abs_link.attrib.get(qn("w:val"))
            if abs_id in abstract_map:
                # Gán trực tiếp dictionary chứa levels để resolver truy cập thẳng
                numbering[num_id] = abstract_map[abs_id]

    return numbering
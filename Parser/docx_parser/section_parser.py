from .xml_utils import *


def parse_section(sectPr, node, context=None):
    if sectPr is None:
        return

    if not hasattr(node, "section"):
        node.section = {}

    # ===== COLUMNS =====
    cols = safe_find(sectPr, "w:cols")
    if cols is not None:
        node.section["columns"] = {
            "count": cols.attrib.get(qn("w:num")),
            "space": cols.attrib.get(qn("w:space"))
        }

    # ===== PAGE SIZE =====
    pgSz = safe_find(sectPr, "w:pgSz")
    if pgSz is not None:
        node.section["pageSize"] = {
            "w": pgSz.attrib.get(qn("w:w")),
            "h": pgSz.attrib.get(qn("w:h")),
            "orient": pgSz.attrib.get(qn("w:orient"))
        }

    # ===== MARGIN =====
    pgMar = safe_find(sectPr, "w:pgMar")
    if pgMar is not None:
        node.section["margin"] = {
            "top": pgMar.attrib.get(qn("w:top")),
            "bottom": pgMar.attrib.get(qn("w:bottom")),
            "left": pgMar.attrib.get(qn("w:left")),
            "right": pgMar.attrib.get(qn("w:right")),
            "header": pgMar.attrib.get(qn("w:header")),
            "footer": pgMar.attrib.get(qn("w:footer")),
            "gutter": pgMar.attrib.get(qn("w:gutter"))
        }

    # ===== PAGE NUMBER =====
    pgNum = safe_find(sectPr, "w:pgNumType")
    if pgNum is not None:
        node.section["pageNumber"] = {
            "format": pgNum.attrib.get(qn("w:fmt")),
            "start": pgNum.attrib.get(qn("w:start"))
        }

    # ===== TITLE PAGE =====
    if safe_find(sectPr, "w:titlePg") is not None:
        node.section["titlePage"] = True

    # ===== DOC GRID =====
    docGrid = safe_find(sectPr, "w:docGrid")
    if docGrid is not None:
        node.section["docGrid"] = {
            "linePitch": docGrid.attrib.get(qn("w:linePitch"))
        }

    # ==========================================
    # 🔥 NEW: HEADERS & FOOTERS (Deep Parsing)
    # ==========================================
    if context is not None:
        headers_footers = []

        # Tìm tất cả thẻ tham chiếu Header & Footer
        references = safe_findall(sectPr, "w:headerReference") + safe_findall(sectPr, "w:footerReference")

        for ref in references:
            tag_name = ref.tag.split("}")[-1]
            hf_type = tag_name.replace("Reference", "")  # Lấy chữ "header" hoặc "footer"
            display_type = ref.attrib.get(qn("w:type"))  # Các giá trị: default, first, even
            rid = ref.attrib.get(qn("r:id"))

            if rid and "relationships" in context and rid in context["relationships"]:

                target_path = context["relationships"][rid]
                if not target_path.startswith("word/"):
                    target_path = f"word/{target_path}"

                xml_content = context.get("files", {}).get(target_path)

                if xml_content:
                    # Chuyển xuống hàm parse nội dung thực sự
                    hf_data = _parse_header_footer(xml_content, target_path, context, hf_type, display_type)
                    if hf_data:
                        headers_footers.append(hf_data)

        if headers_footers:
            node.section["headers_footers"] = headers_footers


def _parse_header_footer(xml_content, target_path, context, hf_type, display_type):
    """
    Hàm nội bộ xử lý nội dung Header/Footer với Local Context.
    """
    import xml.etree.ElementTree as ET
    from .paragraph_parser import parse_paragraph
    from .table_parser import parse_table
    from .relationship_parser import parse_relationships

    # 1. TẠO LOCAL CONTEXT ĐỂ TRÁNH LỖI ĐƯỜNG DẪN ẢNH/HYPERLINK
    local_context = context.copy()

    # target_path thường có dạng "word/header1.xml"
    # -> Cần tìm file rels tương ứng là "word/_rels/header1.xml.rels"
    parts = target_path.split("/")
    if len(parts) >= 2:
        filename = parts[-1]
        rels_path = target_path.replace(filename, f"_rels/{filename}.rels")

        rels_xml = context.get("files", {}).get(rels_path)
        if rels_xml:
            # Nạp Relationships riêng của file Header này
            local_context["relationships"] = parse_relationships(rels_xml)

    # 2. PARSE NỘI DUNG
    root = ET.fromstring(xml_content)

    result = {
        "type": hf_type,
        "displayType": display_type,
        "children": []
    }

    for child in root:
        tag = child.tag.split("}")[-1]

        if tag == "p":
            result["children"].append(parse_paragraph(child, local_context).to_dict())
        elif tag == "tbl":
            result["children"].append(parse_table(child, local_context).to_dict())

    return result
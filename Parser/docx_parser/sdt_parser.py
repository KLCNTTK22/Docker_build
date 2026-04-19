from .ast_node import ASTNode
from .xml_utils import *


def parse_sdt(sdt_elem, context):
    """
    Xử lý thẻ w:sdt (Structured Document Tag).
    Thẻ này thường bọc Mục lục (TOC), Biểu mẫu (Content Controls) hoặc Văn bản được bảo vệ.
    """
    node = ASTNode("sdt", "w:sdt")

    # ==========================================
    # 1. TRÍCH XUẤT THUỘC TÍNH (sdtPr)
    # ==========================================
    sdtPr = safe_find(sdt_elem, "w:sdtPr")
    if sdtPr is not None:

        alias = safe_find(sdtPr, "w:alias")
        if alias is not None:
            node.properties["alias"] = alias.attrib.get(qn("w:val"))

        tag = safe_find(sdtPr, "w:tag")
        if tag is not None:
            node.properties["tag"] = tag.attrib.get(qn("w:val"))

        id_elem = safe_find(sdtPr, "w:id")
        if id_elem is not None:
            node.properties["id"] = id_elem.attrib.get(qn("w:val"))

    # ==========================================
    # 2. XỬ LÝ NỘI DUNG BÊN TRONG (sdtContent)
    # ==========================================
    sdtContent = safe_find(sdt_elem, "w:sdtContent")
    if sdtContent is not None:

        # Import cục bộ để tránh lỗi vòng lặp (Circular Import)
        from .paragraph_parser import parse_paragraph
        from .table_parser import parse_table
        from .run_parser import parse_run
        from .hyperlink_parser import parse_hyperlink

        text_buffer = []

        for child in sdtContent:
            tag = child.tag.split("}")[-1]

            # Block-level (Mục lục, Khối bọc đoạn văn)
            if tag == "p":
                child_node = parse_paragraph(child, context)
                node.add_child(child_node)
                if child_node.text: text_buffer.append(child_node.text)

            elif tag == "tbl":
                node.add_child(parse_table(child, context))

            # Inline-level (Content control bọc chữ)
            elif tag == "r":
                child_node = parse_run(child, context)
                node.add_child(child_node)
                if child_node.text: text_buffer.append(child_node.text)

            elif tag == "hyperlink":
                child_node = parse_hyperlink(child, context)
                node.add_child(child_node)
                if child_node.text: text_buffer.append(child_node.text)

            # SDT lồng trong SDT
            elif tag == "sdt":
                child_node = parse_sdt(child, context)
                node.add_child(child_node)
                if child_node.text: text_buffer.append(child_node.text)

            else:
                node.add_unknown(tag)

        # Cập nhật text tổng quát cho SDT
        if text_buffer:
            node.text = "".join(text_buffer)

    return node
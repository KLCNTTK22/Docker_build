from .ast_node import ASTNode
from .xml_utils import *


def parse_smartart_data(xml_root, context):
    """
    Phân tích data[n].xml để lấy text từ các points.
    Cấu trúc: dgm:ptLst -> dgm:pt -> dgm:t -> a:p
    """
    node = ASTNode("smartartData", "dgm:dataModel")

    # Đảm bảo lấy được danh sách points bất kể xml_root là gì
    pt_list = safe_find(xml_root, ".//dgm:ptLst")
    if pt_list is None and xml_root.tag.endswith("ptLst"):
        pt_list = xml_root

    if pt_list is None:
        return node

    full_text_parts = []

    # Duyệt qua các điểm dữ liệu (points)
    for pt in safe_findall(pt_list, "dgm:pt"):

        # Chỉ lấy text từ các point mang ý nghĩa nội dung (thường là node hoặc par)
        pt_type = pt.attrib.get("type", "node")
        if pt_type not in ["node", "par", "obj"]:
            continue

        text_container = safe_find(pt, "dgm:t")
        if text_container is None:
            continue

        smart_node = ASTNode("smartartNode", "dgm:pt")
        smart_node.properties["modelId"] = pt.attrib.get("modelId")

        # Lấy hình dạng khối (geometry)
        spPr = safe_find(pt, "dgm:spPr")
        if spPr is not None:
            geom = safe_find(spPr, "a:prstGeom")
            if geom is not None:
                smart_node.properties["geometry"] = geom.attrib.get("prst")

        # Quét DrawingML Paragraphs (a:p) bên trong point
        node_text_buffer = []
        for p in safe_findall(text_container, "a:p"):
            para_node = ASTNode("paragraph", "a:p")
            p_text_parts = []

            for r in safe_findall(p, "a:r"):
                run_node = ASTNode("run", "a:r")
                rPr = safe_find(r, "a:rPr")

                if rPr is not None:
                    # Font Family
                    latin = safe_find(rPr, "a:latin")
                    if latin is not None:
                        run_node.properties["fontFamily"] = latin.attrib.get("typeface")

                    # Font Size
                    sz = rPr.attrib.get("sz")
                    if sz:
                        run_node.properties["fontSize"] = int(sz) / 100

                    # Styles
                    if rPr.attrib.get("b") == "1": run_node.properties["bold"] = True
                    if rPr.attrib.get("i") == "1": run_node.properties["italic"] = True

                    # Color
                    solidFill = safe_find(rPr, "a:solidFill")
                    if solidFill is not None:
                        srgb = safe_find(solidFill, "a:srgbClr")
                        if srgb is not None:
                            run_node.properties["color"] = srgb.attrib.get("val")

                # Text content
                t_elem = safe_find(r, "a:t")
                if t_elem is not None and t_elem.text:
                    run_node.text = t_elem.text
                    p_text_parts.append(t_elem.text)
                    para_node.add_child(run_node)

            if p_text_parts:
                para_node.text = "".join(p_text_parts)
                node_text_buffer.append(para_node.text)
                smart_node.add_child(para_node)

        if node_text_buffer:
            smart_node.text = " ".join(node_text_buffer)
            full_text_parts.append(smart_node.text)
            node.add_child(smart_node)

    # Gán text tổng hợp cho node cha để dễ quan sát trong JSON
    if full_text_parts:
        node.text = " | ".join(full_text_parts)

    return node
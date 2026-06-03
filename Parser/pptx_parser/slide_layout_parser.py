import xml.etree.ElementTree as ET
import re
from .ast_node import ASTNode
from .xml_utils import NAMESPACES
from .rels_parser import parse_rels
from .shape_parser import parse_shape_tree
from .slide_parser import parse_graphic_frame


def parse_slide_layout(xml_content, file_path, context):
    """
    Phân tích file slideLayout*.xml.
    Đóng vai trò trung gian kế thừa giữa Slide và Slide Master.
    """
    node = ASTNode(type_="slide_layout", tag="p:sldLayout")

    match = re.search(r'slideLayout(\d+)\.xml', file_path)
    layout_id = match.group(1) if match else "unknown"
    node.properties["layout_id"] = layout_id

    try:
        root = ET.fromstring(xml_content.encode('utf-8'))

        # Nạp relationships của Layout
        rels_path = file_path.replace("ppt/slideLayouts/", "ppt/slideLayouts/_rels/") + ".rels"
        rels_xml = context["files"].get(rels_path)
        rels = parse_rels(rels_xml) if rels_xml else {}

        # Ghi nhận Layout này thuộc về Master nào
        for r_id, rel_data in rels.items():
            if "slideMaster" in rel_data.get("Type", ""):
                node.properties["master_target"] = rel_data.get("Target")
                break

        # Quét hình học và Placeholder trong Layout
        sp_tree = root.find(f".//{{{NAMESPACES['p']}}}spTree")
        if sp_tree is not None:
            shape_nodes = parse_shape_tree(sp_tree, rels, context)
            for shape_node in shape_nodes:
                node.add_child(shape_node)

            # ==========================================
            # [THÊM MỚI] QUÉT GRAPHIC FRAME (BẢNG, BIỂU ĐỒ) TRONG LAYOUT
            # ==========================================
            for gf in sp_tree.findall(f"{{{NAMESPACES['p']}}}graphicFrame"):
                gf_node = parse_graphic_frame(gf, rels, context)
                # Đánh dấu đây là placeholder để UI biết
                gf_node.properties["is_placeholder"] = True 
                node.add_child(gf_node)
            # ==========================================

    except Exception as e:
        node.add_error(f"Lỗi khi parse slide layout {file_path}: {e}")

    return node
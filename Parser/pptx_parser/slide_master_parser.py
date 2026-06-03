import xml.etree.ElementTree as ET
import re
from .ast_node import ASTNode
from .xml_utils import NAMESPACES
from .rels_parser import parse_rels
from .shape_parser import parse_shape_tree


def parse_slide_master(xml_content, file_path, context):
    node = ASTNode(type_="slide_master", tag="p:sldMaster")

    match = re.search(r'slideMaster(\d+)\.xml', file_path)
    master_id = match.group(1) if match else "unknown"
    node.properties["master_id"] = master_id

    try:
        root = ET.fromstring(xml_content.encode('utf-8'))

        rels_path = file_path.replace("ppt/slideMasters/", "ppt/slideMasters/_rels/") + ".rels"
        rels_xml = context["files"].get(rels_path)
        rels = parse_rels(rels_xml) if rels_xml else {}

        # 1. KIỂM TRA HEADER & FOOTER
        hf_element = root.find(f".//{{{NAMESPACES['p']}}}hf")
        if hf_element is not None:
            hf_props = {"tag": "p:hf", "attributes": {}}
            for attr in ['dt', 'hdr', 'ftr', 'sldNum']:
                if attr in hf_element.attrib:
                    hf_props["attributes"][attr] = hf_element.attrib[attr]
            node.properties["header_footer"] = hf_props

        # 2. ĐỌC TEXT STYLES (ĐỊNH DẠNG MẶC ĐỊNH CHUNG - QUAN TRỌNG CHO KẾ THỪA)
        tx_styles = root.find(f".//{{{NAMESPACES['p']}}}txStyles")
        if tx_styles is not None:
            # SỬA: Truyền thêm context vào để có thể giải mã biến Theme
            node.properties["text_styles"] = parse_master_text_styles(tx_styles, context)

        # 3. QUÉT CÁC ĐỐI TƯỢNG TRONG SPTREE
        sp_tree = root.find(f".//{{{NAMESPACES['p']}}}spTree")
        if sp_tree is not None:
            shape_nodes = parse_shape_tree(sp_tree, rels, context)
            for shape_node in shape_nodes:
                node.add_child(shape_node)

    except Exception as e:
        node.add_error(f"Lỗi khi parse slide master {file_path}: {e}")

    return node


def parse_master_text_styles(tx_styles_elem, context):
    """
    Bóc tách các định dạng mặc định (Title, Body, Other) từ Slide Master.
    Đã nâng cấp để bóc tách thông số nhiều cấp độ (lvl1, lvl2...) và giải mã Font.
    """
    styles_dict = {}

    # Duyệt qua titleStyle, bodyStyle, otherStyle
    for style_type in tx_styles_elem:
        tag_name = style_type.tag.split('}')[-1]
        styles_dict[tag_name] = {}

        # Quét các cấp bậc (từ Level 1 đến Level 9)
        for lvl in range(1, 10):
            lvl_tag = f"lvl{lvl}pPr"
            lvl_elem = style_type.find(f"{{{NAMESPACES['a']}}}{lvl_tag}")
            
            if lvl_elem is not None:
                def_r_pr = lvl_elem.find(f"{{{NAMESPACES['a']}}}defRPr")
                if def_r_pr is not None:
                    lvl_data = {}
                    
                    # Lấy size mặc định
                    if "sz" in def_r_pr.attrib:
                        lvl_data["sz"] = def_r_pr.attrib["sz"]

                    # Lấy font mặc định
                    latin = def_r_pr.find(f"{{{NAMESPACES['a']}}}latin")
                    if latin is not None and "typeface" in latin.attrib:
                        font_raw = latin.attrib["typeface"]
                        
                        # --- LOGIC GIẢI MÃ FONT THEME ---
                        if font_raw.startswith("+"):
                            resolved_font = font_raw
                            for theme_map in context.get("theme_registry", {}).values():
                                if font_raw in theme_map:
                                    resolved_font = theme_map[font_raw]
                                    break
                            lvl_data["font_name"] = resolved_font
                        else:
                            lvl_data["font_name"] = font_raw
                        # ---------------------------------

                    if lvl_data:
                        # Vẫn gán đè trực tiếp cấp 1 ra ngoài để tương thích ngược với code JS cũ
                        if lvl == 1:
                            styles_dict[tag_name].update(lvl_data)
                        
                        # Lưu thêm object con cho từng level (phục vụ chấm điểm cấp 2, 3...)
                        styles_dict[tag_name][lvl_tag] = lvl_data

    return styles_dict
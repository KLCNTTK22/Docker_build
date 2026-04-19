import xml.etree.ElementTree as ET
from .ast_node import ASTNode
from .xml_utils import NAMESPACES


def parse_shape_tree(sp_tree, rels):
    """
    Duyệt qua tất cả các đối tượng hình học trong thẻ <p:spTree>.
    Bao gồm: p:sp (Shape), p:pic (Picture), p:graphicFrame (Table, Chart...), p:grpSp (Group)
    """
    nodes = []
    if sp_tree is None:
        return nodes

    for child in sp_tree:
        tag_name = child.tag.split('}')[-1] if '}' in child.tag else child.tag

        if tag_name == 'pic':
            nodes.append(parse_picture(child, rels))
        elif tag_name == 'sp':
            nodes.append(parse_shape_element(child, rels))

        # graphicFrame được xử lý ở slide_parser.py

    return [n for n in nodes if n is not None]


def parse_picture(pic_element, rels):
    """
    Phân tích thẻ <p:pic> (Hình ảnh / Logo).
    """
    node = ASTNode(type_="picture", tag="p:pic")

    nv_pr = pic_element.find(f".//{{{NAMESPACES['p']}}}cNvPr")
    if nv_pr is not None:
        node.attributes["id"] = nv_pr.attrib.get("id", "")
        node.attributes["name"] = nv_pr.attrib.get("name", "")

    blip = pic_element.find(f".//{{{NAMESPACES['a']}}}blip")
    if blip is not None:
        r_embed = blip.attrib.get(f"{{{NAMESPACES['r']}}}embed")
        if r_embed:
            node.properties["relationship_id"] = r_embed
            target = rels.get(r_embed, {}).get("Target")
            if target:
                node.properties["filename"] = target

    # Lấy tọa độ và kích thước, định dạng của Hình ảnh
    sp_pr = pic_element.find(f".//{{{NAMESPACES['p']}}}spPr")
    if sp_pr is not None:
        node.layout.update(parse_transform(sp_pr))
        node.style.update(parse_shape_style(sp_pr))

    return node


def parse_shape_element(sp_element, rels):
    """
    Phân tích thẻ <p:sp> (Shape thông thường).
    Xử lý: Placeholder, Hình học cơ bản, Kiểu dáng (Fill/Outline/Effects), Tọa độ, và Text Body.
    """
    node = ASTNode(type_="shape", tag="p:sp")

    # 1. Trích xuất ID, Name và Hành động Click
    nv_pr = sp_element.find(f".//{{{NAMESPACES['p']}}}cNvPr")
    if nv_pr is not None:
        node.attributes["id"] = nv_pr.attrib.get("id", "")
        node.attributes["name"] = nv_pr.attrib.get("name", "")

        hlink_click = nv_pr.find(f"{{{NAMESPACES['a']}}}hlinkClick")
        if hlink_click is not None:
            node.properties["click_action"] = {
                "action": hlink_click.attrib.get("action", ""),
                "r_id": hlink_click.attrib.get(f"{{{NAMESPACES['r']}}}id", "")
            }

    # 2. Kiểm tra Placeholder
    ph = sp_element.find(f".//{{{NAMESPACES['p']}}}ph")
    if ph is not None:
        node.properties["is_placeholder"] = True
        node.properties["placeholder"] = {
            "type": ph.attrib.get("type", "obj"),
            "idx": ph.attrib.get("idx", "0")
        }
    else:
        node.properties["is_placeholder"] = False

    # 3. Trích xuất Shape Properties (<p:spPr>): Kích thước, Tọa độ, Fill, Outline, Effects
    sp_pr = sp_element.find(f".//{{{NAMESPACES['p']}}}spPr")
    if sp_pr is not None:
        # Loại hình học (Geometry)
        prst_geom = sp_pr.find(f".//{{{NAMESPACES['a']}}}prstGeom")
        if prst_geom is not None:
            prst = prst_geom.attrib.get("prst")
            if prst:
                node.properties["geometry_type"] = prst
                if "actionButton" in prst:
                    node.properties["is_action_button"] = True

        # Tọa độ và Kích thước (Layout)
        node.layout.update(parse_transform(sp_pr))

        # Định dạng Style của Shape (Fill, Outline, Effect)
        node.style.update(parse_shape_style(sp_pr))

    # 4. Trích xuất nội dung văn bản (Text Body)
    tx_body = sp_element.find(f".//{{{NAMESPACES['p']}}}txBody")
    if tx_body is not None:
        paragraph_nodes = parse_text_body(tx_body, rels)
        for p_node in paragraph_nodes:
            node.add_child(p_node)

    return node


def parse_transform(parent_element):
    """
    Trích xuất tọa độ (x, y) và kích thước (cx, cy) từ thẻ <a:xfrm>.
    Đơn vị trong PPTX là EMU (English Metric Unit). 1 inch = 914400 EMUs.
    """
    layout = {}
    xfrm = parent_element.find(f"{{{NAMESPACES['a']}}}xfrm")
    if xfrm is not None:
        off = xfrm.find(f"{{{NAMESPACES['a']}}}off")
        if off is not None:
            layout["x"] = off.attrib.get("x")
            layout["y"] = off.attrib.get("y")

        ext = xfrm.find(f"{{{NAMESPACES['a']}}}ext")
        if ext is not None:
            layout["cx"] = ext.attrib.get("cx")
            layout["cy"] = ext.attrib.get("cy")
    return layout


def parse_shape_style(sp_pr_element):
    """
    Trích xuất thuộc tính hình học của Shape: Fill, Outline, và Effects.
    """
    style = {}

    # 1. Shape Fill (Màu nền)
    shape_fill = parse_fill(sp_pr_element)
    if shape_fill:
        style["fill"] = shape_fill

    # 2. Shape Outline (Viền)
    ln = sp_pr_element.find(f"{{{NAMESPACES['a']}}}ln")
    if ln is not None:
        style["outline"] = {}
        if "w" in ln.attrib:
            style["outline"]["width"] = ln.attrib["w"]  # Độ dày viền

        outline_fill = parse_fill(ln)
        if outline_fill:
            style["outline"]["fill"] = outline_fill

    # 3. Shape Effects (Đổ bóng, phản chiếu...)
    effect_lst = sp_pr_element.find(f"{{{NAMESPACES['a']}}}effectLst")
    if effect_lst is not None and len(effect_lst) > 0:
        style["effects"] = [eff.tag.split('}')[-1] for eff in effect_lst]

    return style


def parse_fill(parent_element):
    """
    Hàm dùng chung để trích xuất cấu trúc Fill (có thể dùng cho Text, Shape, Outline).
    Nhận diện Solid, Gradient, NoFill, Pattern.
    """
    if parent_element is None:
        return None

    solid = parent_element.find(f"{{{NAMESPACES['a']}}}solidFill")
    if solid is not None and len(solid) > 0:
        color_node = list(solid)[0]  # Thường là a:srgbClr, a:schemeClr, hoặc a:prstClr
        color_val = color_node.attrib.get("val", color_node.tag.split('}')[-1])
        return {"type": "solid", "color": color_val}

    grad = parent_element.find(f"{{{NAMESPACES['a']}}}gradFill")
    if grad is not None:
        return {"type": "gradient"}

    patt = parent_element.find(f"{{{NAMESPACES['a']}}}pattFill")
    if patt is not None:
        return {"type": "pattern"}

    no_fill = parent_element.find(f"{{{NAMESPACES['a']}}}noFill")
    if no_fill is not None:
        return {"type": "none"}

    return None


def parse_text_body(tx_body_element, rels):
    """
    Hàm dùng chung để phân tích <txBody>.
    Đã được nâng cấp để đọc trọn vẹn Text Styling (Font, Color, Size, Effects...).
    """
    paragraphs = []

    for p_elem in tx_body_element.findall(f"{{{NAMESPACES['a']}}}p"):
        p_node = ASTNode(type_="paragraph", tag="a:p")

        # 1. Alignment (Căn lề đoạn văn)
        p_pr = p_elem.find(f"{{{NAMESPACES['a']}}}pPr")
        if p_pr is not None:
            if "algn" in p_pr.attrib:
                p_node.style["align"] = p_pr.attrib["algn"]  # l (left), r (right), ctr (center), just (justify)

        # 2. Text Run và Text Styling
        for r_elem in p_elem.findall(f"{{{NAMESPACES['a']}}}r"):
            r_node = ASTNode(type_="text_run", tag="a:r")

            t_elem = r_elem.find(f"{{{NAMESPACES['a']}}}t")
            if t_elem is not None and t_elem.text:
                r_node.text = t_elem.text

            r_pr = r_elem.find(f"{{{NAMESPACES['a']}}}rPr")
            if r_pr is not None:
                # Basic Properties: Size, Bold, Italic, Underline
                # Ghi chú: sz="2400" tương đương font size 24pt
                for attr in ['b', 'i', 'u', 'sz']:
                    if attr in r_pr.attrib:
                        r_node.style[attr] = r_pr.attrib[attr]

                # Font Name (Typeface)
                latin_font = r_pr.find(f"{{{NAMESPACES['a']}}}latin")
                if latin_font is not None and "typeface" in latin_font.attrib:
                    r_node.style["font_name"] = latin_font.attrib["typeface"]

                # Text Fill (Màu chữ)
                text_fill = parse_fill(r_pr)
                if text_fill:
                    r_node.style["fill"] = text_fill

                # Text Outline (Viền chữ)
                ln = r_pr.find(f"{{{NAMESPACES['a']}}}ln")
                if ln is not None:
                    r_node.style["outline"] = parse_fill(ln)

                # Text Effects (Hiệu ứng chữ như bóng đổ, phát sáng)
                effect_lst = r_pr.find(f"{{{NAMESPACES['a']}}}effectLst")
                if effect_lst is not None and len(effect_lst) > 0:
                    r_node.style["effects"] = [eff.tag.split('}')[-1] for eff in effect_lst]

                # Hyperlink trên text
                hlink_click = r_pr.find(f"{{{NAMESPACES['a']}}}hlinkClick")
                if hlink_click is not None:
                    r_id = hlink_click.attrib.get(f"{{{NAMESPACES['r']}}}id")
                    if r_id:
                        r_node.properties["hyperlink_id"] = r_id
                        target = rels.get(r_id, {}).get("Target")
                        if target:
                            r_node.properties["hyperlink_target"] = target

            p_node.add_child(r_node)

        if p_node.children:
            paragraphs.append(p_node)

    return paragraphs
from .ast_node import ASTNode
from .xml_utils import *
from .run_properties_parser import parse_run_properties


def parse_shape(wsp, context):
    node = ASTNode("shape", "wps:wsp")

    # --- 1. Geometry & Visuals ---
    spPr = safe_find(wsp, ".//wps:spPr")
    if spPr is not None:
        geom = safe_find(spPr, "a:prstGeom")
        if geom is not None:
            node.properties["geometry"] = geom.attrib.get("prst")

    # --- 2. Text Content (WordprocessingML trong txbxContent) ---
    txbx = safe_find(wsp, ".//w:txbxContent")
    if txbx is not None:
        for p in safe_findall(txbx, "w:p"):
            para_node = _parse_styled_paragraph(p, "w", context)
            node.add_child(para_node)

    # --- 3. Text Content (DrawingML trong txBody) ---
    txBody = safe_find(wsp, ".//wps:txbody") or safe_find(wsp, ".//a:txBody")
    if txBody is not None:
        for p in safe_findall(txBody, "a:p"):
            para_node = _parse_styled_paragraph(p, "a", context)
            node.add_child(para_node)

    # --- 4. Identity ---
    cNvPr = safe_find(wsp, ".//wps:cNvPr") or safe_find(wsp, ".//wp:docPr")
    if cNvPr is not None:
        node.properties["name"] = cNvPr.attrib.get("name")
        node.properties["id"] = cNvPr.attrib.get("id")

    return node


def _parse_styled_paragraph(p_elem, ns, context):
    """
    Hàm bổ trợ trích xuất text và đầy đủ định dạng (Font, Bold, Italic, Color)
    """
    para_node = ASTNode("paragraph", f"{ns}:p")
    text_buffer = []

    for r in safe_findall(p_elem, f"{ns}:r"):
        run_node = ASTNode("run", f"{ns}:r")
        rPr = safe_find(r, f"{ns}:rPr")

        if rPr is not None:
            if ns == "w":
                # Tái sử dụng logic chuẩn của WordML
                parse_run_properties(rPr, run_node, context)
            else:
                # Logic cho DrawingML (a:rPr)
                # 1. Font & Size
                latin = safe_find(rPr, "a:latin")
                if latin is not None:
                    run_node.properties["fontFamily"] = latin.attrib.get("typeface")

                sz = rPr.attrib.get("sz")
                if sz:
                    run_node.properties["fontSize"] = int(sz) / 100

                # 2. Styles (Attribute based)
                if rPr.attrib.get("b") == "1": run_node.properties["bold"] = True
                if rPr.attrib.get("i") == "1": run_node.properties["italic"] = True
                if rPr.attrib.get("u") and rPr.attrib.get("u") != "none":
                    run_node.properties["underline"] = True

                # 3. Color (DrawingML Solid Fill)
                solidFill = safe_find(rPr, "a:solidFill")
                if solidFill is not None:
                    srgb = safe_find(solidFill, "a:srgbClr")
                    if srgb is not None:
                        run_node.properties["color"] = srgb.attrib.get("val")
                    else:
                        scheme = safe_find(solidFill, "a:schemeClr")
                        if scheme is not None:
                            run_node.properties["colorTheme"] = scheme.attrib.get("val")

        # --- TEXT ---
        t_tag = "w:t" if ns == "w" else "a:t"
        t_elem = safe_find(r, t_tag)
        if t_elem is not None and t_elem.text:
            run_node.text = t_elem.text
            text_buffer.append(t_elem.text)
            para_node.add_child(run_node)

    para_node.text = "".join(text_buffer)
    return para_node
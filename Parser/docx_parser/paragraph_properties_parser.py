from .ast_node import ASTNode
from .xml_utils import *
from .section_parser import parse_section
from .run_properties_parser import parse_run_properties


def parse_paragraph_properties(pPr, node, context):
    if pPr is None:
        return

    # --- 1. Alignment ---
    jc = safe_find(pPr, "w:jc")
    if jc is not None:
        val = jc.attrib.get(qn("w:val"))
        align_map = {"both": "justify", "center": "center", "right": "right", "left": "left",
                     "distribute": "justify-all"}
        node.layout["alignment"] = align_map.get(val, val)

    # --- 2. Spacing ---
    spacing = safe_find(pPr, "w:spacing")
    if spacing is not None:
        spacing_data = {}
        before = spacing.attrib.get(qn("w:before"))
        after = spacing.attrib.get(qn("w:after"))

        # Ép kiểu an toàn (float) thay vì int để chống lỗi với các số thập phân
        try:
            if before: spacing_data["beforePt"] = round(float(before) / 20, 2)
            if after: spacing_data["afterPt"] = round(float(after) / 20, 2)
        except ValueError:
            pass

        line = spacing.attrib.get(qn("w:line"))
        line_rule = spacing.attrib.get(qn("w:lineRule"), "auto")
        if line:
            try:
                line_val = float(line)  # 🔥 Dùng float thay vì int
                if line_rule == "auto":
                    spacing_data["lineMultiple"] = round(line_val / 240, 2)
                else:
                    spacing_data["linePt"] = round(line_val / 20, 2)
                spacing_data["lineRule"] = line_rule
            except ValueError:
                pass

        if spacing_data: node.layout["spacing"] = spacing_data

    # --- 3. Indentation ---
    ind = safe_find(pPr, "w:ind")
    if ind is not None:
        indent_data = {}
        for attr in ["left", "right", "firstLine", "hanging"]:
            val = ind.attrib.get(qn(f"w:{attr}"))
            if val:
                try:
                    indent_data[f"{attr}Pt"] = round(float(val) / 20, 2)
                except ValueError:
                    pass
        if indent_data: node.layout["indent"] = indent_data

    # --- 4. Tabs ---
    tabs = safe_find(pPr, "w:tabs")
    if tabs is not None:
        tab_list = []
        for tab in safe_findall(tabs, "w:tab"):
            pos = tab.attrib.get(qn("w:pos"), 0)
            try:
                pos_pt = round(float(pos) / 20, 2)
            except ValueError:
                pos_pt = 0

            tab_list.append({
                "positionPt": pos_pt,
                "align": tab.attrib.get(qn("w:val")),
                "leader": tab.attrib.get(qn("w:leader"))
            })
        if tab_list: node.layout["tabs"] = tab_list

    # --- 5. Paragraph-level Run Properties ---
    rPr = safe_find(pPr, "w:rPr")
    if rPr is not None:
        temp_node = ASTNode("temp", "temp")
        parse_run_properties(rPr, temp_node, context)
        if temp_node.properties:
            node.properties["paragraphRunProperties"] = temp_node.properties

    # --- 6. Style & Numbering & Section ---
    style = safe_find(pPr, "w:pStyle")
    if style is not None:
        node.properties["pStyle"] = style.attrib.get(qn("w:val"))

    numPr = safe_find(pPr, "w:numPr")
    if numPr is not None:
        ilvl = safe_find(numPr, "w:ilvl")
        numId = safe_find(numPr, "w:numId")
        node.list = {
            "numId": numId.attrib.get(qn("w:val")) if numId is not None else None,
            "level": ilvl.attrib.get(qn("w:val")) if ilvl is not None else None
        }

    sectPr = safe_find(pPr, "w:sectPr")
    if sectPr is not None:
        parse_section(sectPr, node, context)
from .xml_utils import *

def parse_cell_properties(tcPr, node):

    if tcPr is None:
        return

    # ===== CELL WIDTH =====
    tcW = safe_find(tcPr, "w:tcW")

    if tcW is not None:
        node.layout["width"] = {
            "value": tcW.attrib.get(qn("w:w")),
            "type": tcW.attrib.get(qn("w:type"))
        }

    # ===== COLUMN MERGE =====
    gridSpan = safe_find(tcPr, "w:gridSpan")

    if gridSpan is not None:
        node.layout["colspan"] = gridSpan.attrib.get(qn("w:val"))

    # ===== ROW MERGE =====
    vMerge = safe_find(tcPr, "w:vMerge")

    if vMerge is not None:
        node.layout["rowspan"] = vMerge.attrib.get(qn("w:val"))

    # =========================================================
    # 🔥 NEW: CELL SHADING
    # =========================================================
    shd = safe_find(tcPr, "w:shd")

    if shd is not None:
        fill = shd.attrib.get(qn("w:fill"))

        if fill:
            node.layout["shading"] = fill

    # =========================================================
    # 🔥 NEW: CELL BORDERS
    # =========================================================
    tcBorders = safe_find(tcPr, "w:tcBorders")

    if tcBorders is not None:

        border_data = {}

        for side in ["top", "bottom", "left", "right", "insideH", "insideV"]:

            elem = safe_find(tcBorders, f"w:{side}")

            if elem is not None:

                border_data[side] = {
                    "style": elem.attrib.get(qn("w:val")),
                    "size": elem.attrib.get(qn("w:sz")),
                    "color": elem.attrib.get(qn("w:color"))
                }

        if border_data:
            node.layout["borders"] = border_data
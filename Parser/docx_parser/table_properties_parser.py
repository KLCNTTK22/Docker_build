from .xml_utils import *

def parse_table_properties(tblPr, node):

    if tblPr is None:
        return

    # TABLE STYLE
    style = safe_find(tblPr, "w:tblStyle")
    if style is not None:
        node.style["tableStyle"] = style.attrib.get(qn("w:val"))

    # TABLE WIDTH
    tblW = safe_find(tblPr, "w:tblW")
    if tblW is not None:

        node.layout["width"] = {
            "value": tblW.attrib.get(qn("w:w")),
            "type": tblW.attrib.get(qn("w:type"))
        }

    # TABLE BORDERS
    borders = safe_find(tblPr, "w:tblBorders")

    if borders is not None:

        border_data = {}

        for side in ["top","bottom","left","right","insideH","insideV"]:

            elem = safe_find(borders, f"w:{side}")

            if elem is not None:

                border_data[side] = {
                    "style": elem.attrib.get(qn("w:val")),
                    "size": elem.attrib.get(qn("w:sz")),
                    "color": elem.attrib.get(qn("w:color"))
                }

        node.layout["borders"] = border_data
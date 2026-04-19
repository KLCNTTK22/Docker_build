from .xml_utils import *
from .ast_node import ASTNode
from .chart_parser import parse_chart
from .smartart_parser import parse_smartart
from .shape_parser import parse_shape

def parse_drawing(elem, node, context):

    # =========================
    # 1. INLINE / ANCHOR
    # =========================
    container = safe_find(elem, "wp:inline")

    if container is None:
        container = safe_find(elem, "wp:anchor")

    # 🔥 FIX 2: PHÂN BIỆT MODE
    if safe_find(elem, "wp:inline") is not None:
        node.layout["mode"] = "inline"
    elif safe_find(elem, "wp:anchor") is not None:
        node.layout["mode"] = "anchor"

    width = None
    height = None
    name = None
    x = None
    y = None

    if container is not None:

        extent = safe_find(container, "wp:extent")

        if extent is not None:
            width = extent.attrib.get("cx")
            height = extent.attrib.get("cy")

        docPr = safe_find(container, "wp:docPr")

        if docPr is not None:
            name = docPr.attrib.get("name")

        # ===== POSITION (FIX ĐỦ DATA, KHÔNG ĐOÁN) =====
        posH = safe_find(container, "wp:positionH")
        if posH is not None:

            # offset
            posOffset = safe_find(posH, "wp:posOffset")
            if posOffset is not None:
                x = posOffset.text

            # align
            align = safe_find(posH, "wp:align")
            if align is not None:
                node.layout["xAlign"] = align.text

            # relative
            rel = posH.attrib.get("relativeFrom")
            if rel:
                node.layout["xRelative"] = rel


        posV = safe_find(container, "wp:positionV")
        if posV is not None:

            posOffset = safe_find(posV, "wp:posOffset")
            if posOffset is not None:
                y = posOffset.text

            align = safe_find(posV, "wp:align")
            if align is not None:
                node.layout["yAlign"] = align.text

            rel = posV.attrib.get("relativeFrom")
            if rel:
                node.layout["yRelative"] = rel

    # =========================
    # 2 PICTURE 
    # =========================
    pic = elem.find(".//pic:pic", {
        "pic": "http://schemas.openxmlformats.org/drawingml/2006/picture"
    })

    if pic is not None:

        image_node = ASTNode("image", "pic:pic")

        # ---- NAME ----
        cNvPr = pic.find(".//pic:cNvPr", {
            "pic": "http://schemas.openxmlformats.org/drawingml/2006/picture"
        })

        if cNvPr is not None:
            image_node.properties["name"] = cNvPr.attrib.get("name")
            image_node.properties["descr"] = cNvPr.attrib.get("descr")

        # ---- BLIP (RID) ----
        blip = pic.find(".//a:blip", NS)

        if blip is not None:

            embed = blip.attrib.get(qn("r:embed"))

            if embed in context["relationships"]:
                image_node.references.append({
                    "target": context["relationships"][embed],
                    "rid": embed
                })

        # ---- LAYOUT ----
        image_node.layout["x"] = x
        image_node.layout["y"] = y
        image_node.layout["mode"] = node.layout.get("mode")

        node.add_child(image_node)
    # =========================
    # 3. GRAPHIC DATA
    # =========================
    graphicData = elem.find(".//a:graphicData", NS)

    if graphicData is not None:

        uri = graphicData.attrib.get("uri", "")

        # =====================
        # 3.1 SHAPE (ADVANCED)
        # =====================
        if "wordprocessingShape" in uri:

            wsp = graphicData.find(".//wps:wsp", NS)

            if wsp is not None:

                shape = parse_shape(wsp, context)

                if shape:
                    shape.properties["name"] = name
                    shape.layout["width"] = width
                    shape.layout["height"] = height
                    shape.layout["x"] = x
                    shape.layout["y"] = y
                    shape.layout["mode"] = node.layout.get("mode")

                    node.add_child(shape)

        # =====================
        # 3.2 INK
        # =====================
        elif "wordprocessingInk" in uri:

            content = graphicData.find(".//w14:contentPart", {
                "w14": "http://schemas.microsoft.com/office/word/2010/wordml"
            })

            if content is not None:

                rid = content.attrib.get(qn("r:id"))

                node.references.append({
                    "type": "ink",
                    "rid": rid,
                    "target": context["relationships"].get(rid),
                    "width": width,
                    "height": height,
                    "name": name
                })

    # =========================
    # 4. CHART
    # =========================
    chart_node = parse_chart(elem, context)

    if chart_node:
        node.add_child(chart_node)

    # =========================
    # 5. SMARTART
    # =========================
    smart_node = parse_smartart(elem, context)

    if smart_node:
        node.add_child(smart_node)
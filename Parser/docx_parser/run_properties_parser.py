from .xml_utils import *


def _get_w14_color(parent):
    """Hàm bổ trợ để lấy màu sắc phức tạp trong thẻ w14 (hỗ trợ cả srgb và scheme)"""
    if parent is None: return None

    srgb = safe_find(parent, "w14:srgbClr")
    if srgb is not None:
        color_data = {"val": srgb.attrib.get(qn("w14:val")), "type": "srgb"}
        alpha = safe_find(srgb, "w14:alpha")
        if alpha is not None: color_data["alpha"] = alpha.attrib.get(qn("w14:val"))
        return color_data

    scheme = safe_find(parent, "w14:schemeClr")
    if scheme is not None:
        color_data = {"val": scheme.attrib.get(qn("w14:val")), "type": "scheme"}
        alpha = safe_find(scheme, "w14:alpha")
        if alpha is not None: color_data["alpha"] = alpha.attrib.get(qn("w14:val"))
        return color_data

    return None


def parse_run_properties(rPr, node, context):
    if rPr is None:
        return

    # ==========================================
    # 1. BASIC STYLES
    # ==========================================
    if safe_find(rPr, "w:b") is not None: node.properties["bold"] = True
    if safe_find(rPr, "w:i") is not None: node.properties["italic"] = True

    u = safe_find(rPr, "w:u")
    if u is not None:
        val = u.attrib.get(qn("w:val"))
        node.properties["underline"] = val if val else True

    if safe_find(rPr, "w:strike") is not None: node.properties["strike"] = True
    if safe_find(rPr, "w:dstrike") is not None: node.properties["doubleStrike"] = True
    if safe_find(rPr, "w:caps") is not None: node.properties["caps"] = True
    if safe_find(rPr, "w:smallCaps") is not None: node.properties["smallCaps"] = True

    # ==========================================
    # 2. COLOR & HIGHLIGHT
    # ==========================================
    highlight = safe_find(rPr, "w:highlight")
    if highlight is not None:
        node.properties["highlight"] = highlight.attrib.get(qn("w:val"))

    color = safe_find(rPr, "w:color")
    if color is not None:
        node.properties["color"] = color.attrib.get(qn("w:val"))

    # ==========================================
    # 3. STYLE ID
    # ==========================================
    rStyle = safe_find(rPr, "w:rStyle")
    if rStyle is not None:
        node.properties["rStyle"] = rStyle.attrib.get(qn("w:val"))

    # ==========================================
    # 4. FONT
    # ==========================================
    fonts = safe_find(rPr, "w:rFonts")
    if fonts is not None:
        font_data = {}
        keys = ["ascii", "hAnsi", "cs", "eastAsia", "asciiTheme", "hAnsiTheme", "cstheme", "eastAsiaTheme"]
        for key in keys:
            val = fonts.attrib.get(qn(f"w:{key}"))
            if val: font_data[key] = val
        if font_data: node.properties["font"] = font_data

    # ==========================================
    # 5. LANG
    # ==========================================
    lang = safe_find(rPr, "w:lang")
    if lang is not None:
        lang_data = {}
        for key in ["val", "eastAsia", "bidi"]:
            val = lang.attrib.get(qn(f"w:{key}"))
            if val: lang_data[key] = val
        if lang_data: node.properties["lang"] = lang_data

    # ==========================================
    # 6. SIZE
    # ==========================================
    sz = safe_find(rPr, "w:sz")
    if sz is not None:
        node.properties["fontSize"] = int(sz.attrib.get(qn("w:val"))) / 2

    # ==========================================
    # 7. 🔥 ADVANCED TEXT EFFECTS (Hiệu ứng W14)
    # ==========================================

    # --- 7.1 SHADOW (Bóng đổ) ---
    shadow = safe_find(rPr, "w14:shadow")
    if shadow is not None:
        shd_data = {}
        blur = shadow.attrib.get(qn("w14:blurRad"))
        dist = shadow.attrib.get(qn("w14:dist"))

        if blur: shd_data["blurPt"] = round(int(blur) / 12700, 2)
        if dist: shd_data["distancePt"] = round(int(dist) / 12700, 2)

        shd_data["direction"] = shadow.attrib.get(qn("w14:dir"))
        shd_data["alignment"] = shadow.attrib.get(qn("w14:algn"))

        shd_color = _get_w14_color(shadow)
        if shd_color: shd_data["color"] = shd_color

        node.properties["shadow"] = shd_data

    # --- 7.2 GLOW (Phát sáng) ---
    glow = safe_find(rPr, "w14:glow")
    if glow is not None:
        glow_data = {}
        rad = glow.attrib.get(qn("w14:rad"))
        if rad: glow_data["radiusPt"] = round(int(rad) / 12700, 2)

        glw_color = _get_w14_color(glow)
        if glw_color: glow_data["color"] = glw_color

        node.properties["glow"] = glow_data

    # --- 7.3 REFLECTION (Phản chiếu) ---
    reflection = safe_find(rPr, "w14:reflection")
    if reflection is not None:
        ref_data = {}
        blur = reflection.attrib.get(qn("w14:blurRad"))
        dist = reflection.attrib.get(qn("w14:dist"))
        if blur: ref_data["blurPt"] = round(int(blur) / 12700, 2)
        if dist: ref_data["distancePt"] = round(int(dist) / 12700, 2)

        ref_data["direction"] = reflection.attrib.get(qn("w14:dir"))
        ref_data["startAlpha"] = reflection.attrib.get(qn("w14:stA"))
        ref_data["endAlpha"] = reflection.attrib.get(qn("w14:endA"))
        node.properties["reflection"] = ref_data

    # --- 7.4 TEXT OUTLINE (Viền chữ) ---
    outline = safe_find(rPr, "w14:textOutline")
    if outline is not None:
        out_data = {}
        w = outline.attrib.get(qn("w14:w"))
        if w: out_data["widthPt"] = round(int(w) / 12700, 2)

        out_data["cap"] = outline.attrib.get(qn("w14:cap"))
        out_data["compound"] = outline.attrib.get(qn("w14:cmpd"))

        fill = safe_find(outline, "w14:solidFill")
        if fill is not None:
            fill_col = _get_w14_color(fill)
            if fill_col: out_data["color"] = fill_col

        node.properties["outline"] = out_data

    # --- 7.5 TEXT FILL (Màu nền chữ: Gradient hoặc Solid đặc biệt) ---
    textFill = safe_find(rPr, "w14:textFill")
    if textFill is not None:
        fill_data = {}
        solidFill = safe_find(textFill, "w14:solidFill")
        if solidFill is not None:
            fill_data["type"] = "solid"
            fill_data["color"] = _get_w14_color(solidFill)

        gradFill = safe_find(textFill, "w14:gradFill")
        if gradFill is not None:
            fill_data["type"] = "gradient"

        node.properties["textFill"] = fill_data
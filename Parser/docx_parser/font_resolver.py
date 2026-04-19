from .style_resolver import resolve_style


def get_merged_properties(node, context):
    """
    Thực hiện Deep Merge các thuộc tính theo đúng thứ tự ưu tiên của OOXML.
    (Gộp dictionary đối với 'font' và 'lang' để không bị mất dữ liệu mảng)
    """
    merged = {}

    # 1. Document Defaults
    doc_def = context.get("default", {}).get("run", {})
    merged = _deep_merge(merged, doc_def)

    # 2. Paragraph Style (pStyle)
    p_style_id = node.properties.get("pStyle")
    if p_style_id:
        p_style = resolve_style(p_style_id, context.get("styles", {}))
        merged = _deep_merge(merged, p_style)

    # 3. Paragraph Properties (paragraphRunProperties)
    para_rPr = node.properties.get("paragraphRunProperties", {})
    merged = _deep_merge(merged, para_rPr)

    # 4. Run Style (rStyle)
    r_style_id = node.properties.get("rStyle")
    if r_style_id:
        r_style = resolve_style(r_style_id, context.get("styles", {}))
        merged = _deep_merge(merged, r_style)

    # 5. Run Properties (Định nghĩa trực tiếp)
    merged = _deep_merge(merged, node.properties)

    return merged


def _deep_merge(base, override):
    res = dict(base)
    for k, v in override.items():
        if k in ["font", "lang"] and isinstance(v, dict):
            res[k] = {**res.get(k, {}), **v}
        else:
            res[k] = v
    return res


def resolve_font(node, context):
    """
    Lấy font Latin/ASCII duy nhất dựa trên các properties đã được merged toàn diện.
    """
    merged = get_merged_properties(node, context)
    font_data = merged.get("font", {})

    if not font_data:
        return None

    # --- Ưu tiên 1: Lấy font ASCII trực tiếp ---
    if font_data.get("ascii"):
        return font_data["ascii"]

    # --- Ưu tiên 2: Giải mã từ Theme (ưu tiên hệ Latin) ---
    ascii_theme = font_data.get("asciiTheme")
    if ascii_theme:
        theme_fonts = context.get("themeFonts", {})

        # Ví dụ: asciiTheme = "minorHAnsi" -> tìm trong minorFont
        if "minor" in ascii_theme.lower():
            return theme_fonts.get("minorFont", {}).get("latin")
        elif "major" in ascii_theme.lower():
            return theme_fonts.get("majorFont", {}).get("latin")

    # --- Dự phòng: Các thuộc tính khác nếu không tìm thấy chuẩn ASCII ---
    if font_data.get("hAnsi"): return font_data["hAnsi"]
    if font_data.get("eastAsia"): return font_data["eastAsia"]
    if font_data.get("cs"): return font_data["cs"]

    return None
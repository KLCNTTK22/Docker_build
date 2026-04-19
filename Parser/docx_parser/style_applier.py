from .style_resolver import resolve_style
from .font_resolver import resolve_font


def apply_run_style(node, context):

    # ===== 1. APPLY STYLE =====
    style_id = node.properties.get("rStyle")

    if style_id:
        style_props = resolve_style(style_id, context["styles"])

        for k, v in style_props.items():
            if k not in node.properties:
                node.properties[k] = v

    # ===== 2. APPLY FONT =====
    font = resolve_font(node, context)

    if font:
        node.properties["resolvedFont"] = font

    # ===== 3. DEFAULT FONT SIZE =====
    if "fontSize" not in node.properties:
        default_size = context.get("default", {}).get("fontSize")
        if default_size:
            node.properties["fontSize"] = default_size
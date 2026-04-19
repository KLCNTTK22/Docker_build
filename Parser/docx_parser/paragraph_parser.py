from .ast_node import ASTNode
from .xml_utils import *
from .run_parser import parse_run
from .hyperlink_parser import parse_hyperlink
from .paragraph_properties_parser import parse_paragraph_properties
from .style_applier import apply_run_style
from .numbering_resolver import resolve_numbering
from .sdt_parser import parse_sdt
from .bookmark_parser import parse_bookmark_start, parse_bookmark_end


def parse_paragraph(p, context):
    node = ASTNode("paragraph", "w:p")

    # ===== PARAGRAPH PROPERTIES =====
    pPr = safe_find(p, "w:pPr")
    if pPr is not None:
        jc = safe_find(pPr, "w:jc")
        if jc is not None:
            val = jc.attrib.get(qn("w:val"))
            align_map = {"both": "justify", "center": "center", "right": "right", "left": "left",
                         "distribute": "justify-all"}
            node.layout["alignment"] = align_map.get(val, val)

    # Lấy numId, level, spacing, indent, tabs, rPr...
    parse_paragraph_properties(pPr, node, context)

    # 🔥 RESOLVE NUMBERING DETAILS
    if node.list and node.list.get("numId") and node.list.get("level"):
        res = resolve_numbering(node.list["numId"], node.list["level"], context.get("numbering", {}))
        if res:
            node.list.update(res)

    runs = []
    # Định dạng mặc định của toàn đoạn văn
    para_rPr = node.properties.get("paragraphRunProperties", {})

    # ==========================================
    # HÀM BỔ TRỢ: KẾ THỪA FONT/MÀU ĐỆ QUY
    # Đảm bảo các Run nằm sâu trong SDT hoặc Hyperlink vẫn nhận đúng định dạng
    # ==========================================
    def _process_nested_runs(nested_node):
        if nested_node.type == "run":
            # Kế thừa
            for k, v in para_rPr.items():
                if k not in nested_node.properties:
                    nested_node.properties[k] = v
            # Đưa vào danh sách để apply_run_style giải mã Font sau cùng
            runs.append(nested_node)

        for child in nested_node.children:
            _process_nested_runs(child)

    # ===== CHILDREN =====
    for child in p:
        tag = child.tag.split("}")[-1]

        if child.tag.endswith("pPr"):
            continue

        if tag == "r":
            run_node = parse_run(child, context)
            for k, v in para_rPr.items():
                if k not in run_node.properties:
                    run_node.properties[k] = v
            runs.append(run_node)
            node.add_child(run_node)

        elif tag == "hyperlink":
            hyp_node = parse_hyperlink(child, context)
            _process_nested_runs(hyp_node)  # Áp dụng đệ quy cho hyperlink
            node.add_child(hyp_node)

        elif tag == "sdt":
            # Xử lý Content Control nằm xen kẽ giữa các chữ
            sdt_node = parse_sdt(child, context)
            _process_nested_runs(sdt_node)  # Đảm bảo chữ trong SDT có đúng font/màu
            node.add_child(sdt_node)

        # ==========================================
        # 🔥 NEW: BOOKMARKS AT PARAGRAPH LEVEL
        # ==========================================
        elif tag == "bookmarkStart":
            node.add_child(parse_bookmark_start(child))

        elif tag == "bookmarkEnd":
            node.add_child(parse_bookmark_end(child))

        elif tag == "AlternateContent":
            choice = safe_find(child, "mc:Choice")
            if choice is not None:
                for c in choice:
                    c_tag = c.tag.split("}")[-1]
                    if c_tag == "r":
                        run_node = parse_run(c, context)
                        for k, v in para_rPr.items():
                            if k not in run_node.properties:
                                run_node.properties[k] = v
                        runs.append(run_node)
                        node.add_child(run_node)
                    elif c_tag == "hyperlink":
                        hyp_node = parse_hyperlink(c, context)
                        _process_nested_runs(hyp_node)
                        node.add_child(hyp_node)
                    elif c_tag == "sdt":
                        sdt_node = parse_sdt(c, context)
                        _process_nested_runs(sdt_node)
                        node.add_child(sdt_node)
                    elif c_tag == "bookmarkStart":
                        node.add_child(parse_bookmark_start(c))
                    elif c_tag == "bookmarkEnd":
                        node.add_child(parse_bookmark_end(c))
        else:
            node.add_unknown(tag)

    # ===== STYLES =====
    pStyle = node.properties.get("pStyle")
    if pStyle:
        style_def = context.get("styles", {}).get(pStyle)
        if style_def:
            node.style = style_def
            style_rPr = style_def.get("rPr", {})
            for run in runs:
                for k, v in style_rPr.items():
                    if k not in run.properties:
                        run.properties[k] = v

    for run in runs:
        apply_run_style(run, context)

    return node
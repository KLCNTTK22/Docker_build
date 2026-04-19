from .ast_node import ASTNode
from .xml_utils import *
from .run_properties_parser import parse_run_properties
from .drawing_parser import parse_drawing
from .toc_parser import parse_toc_field
from .bookmark_parser import parse_bookmark_start, parse_bookmark_end


def parse_run(run, context):
    node = ASTNode("run", "w:r")

    # ===== PROPERTIES =====
    rPr = safe_find(run, "w:rPr")
    parse_run_properties(rPr, node, context)

    # ===== CHILD ELEMENTS =====
    for child in run:

        tag = child.tag.split("}")[-1]

        if tag == "rPr":
            continue

        # ---- TEXT ----
        if tag == "t":
            text = child.text or ""
            if child.attrib.get("{http://www.w3.org/XML/1998/namespace}space") != "preserve":
                text = text.strip()

            if text:
                if node.text:
                    node.text += text
                else:
                    node.text = text

        # ==========================================
        # 🔥 NEW: FIELDS (fldChar, instrText)
        # ==========================================
        elif tag == "fldChar":
            fld_node = ASTNode("fieldChar", "w:fldChar")
            fld_node.properties["fldCharType"] = child.attrib.get(qn("w:fldCharType"))
            node.add_child(fld_node)

        elif tag == "instrText":
            instr_node = ASTNode("instructionText", "w:instrText")
            text = child.text or ""
            instr_node.text = text

            if "TOC" in text:
                toc_node = parse_toc_field(text)
                if toc_node and "options" in toc_node.properties:
                    instr_node.properties["tocOptions"] = toc_node.properties["options"]

            node.add_child(instr_node)

        # ==========================================
        # 🔥 KHÔI PHỤC LẠI: FOOTNOTES & ENDNOTES
        # ==========================================
        elif tag == "footnoteReference":
            ref_id = child.attrib.get(qn("w:id"))
            fn_node = ASTNode("footnote", "w:footnoteReference")
            fn_node.properties["id"] = ref_id

            if "footnotes" in context and ref_id in context["footnotes"]:
                for fn_child in context["footnotes"][ref_id]:
                    fn_node.add_child(fn_child)
                    if fn_child.text:
                        fn_node.text = (fn_node.text or "") + fn_child.text

            node.add_child(fn_node)

        elif tag == "endnoteReference":
            ref_id = child.attrib.get(qn("w:id"))
            en_node = ASTNode("endnote", "w:endnoteReference")
            en_node.properties["id"] = ref_id

            if "endnotes" in context and ref_id in context["endnotes"]:
                for en_child in context["endnotes"][ref_id]:
                    en_node.add_child(en_child)
                    if en_child.text:
                        en_node.text = (en_node.text or "") + en_child.text

            node.add_child(en_node)

        elif tag == "footnoteRef":
            node.add_child(ASTNode("footnoteRefSymbol", "w:footnoteRef"))

        elif tag == "endnoteRef":
            node.add_child(ASTNode("endnoteRefSymbol", "w:endnoteRef"))

        # ==========================================
        # 🔥 NEW: BOOKMARKS
        # ==========================================
        elif tag == "bookmarkStart":
            node.add_child(parse_bookmark_start(child))

        elif tag == "bookmarkEnd":
            node.add_child(parse_bookmark_end(child))

        # ---- ALTERNATE CONTENT ----
        elif tag == "AlternateContent":
            choice = safe_find(child, "mc:Choice")
            if choice is not None:
                for c in choice:
                    c_tag = c.tag.split("}")[-1]
                    if c_tag == "drawing":
                        parse_drawing(c, node, context)

        # ---- DRAWING ----
        elif tag == "drawing":
            parse_drawing(child, node, context)

        # ---- BREAKS & OTHERS ----
        elif tag == "br":
            br_type = child.attrib.get(qn("w:type"), "textWrapping")
            if br_type == "page":
                node.add_child(ASTNode("pageBreak", "w:br"))
            elif br_type == "column":
                node.add_child(ASTNode("columnBreak", "w:br"))
            else:
                node.add_child(ASTNode("lineBreak", "w:br"))

        elif tag == "tab":
            node.text = (node.text or "") + "\t"

        elif tag == "cr":
            node.add_child(ASTNode("carriageReturn", "w:cr"))

        elif tag == "lastRenderedPageBreak":
            node.add_child(ASTNode("renderedPageBreak", "w:lastRenderedPageBreak"))

        elif tag == "noBreakHyphen":
            node.text = (node.text or "") + "-"

        else:
            node.add_unknown(tag)

    return node
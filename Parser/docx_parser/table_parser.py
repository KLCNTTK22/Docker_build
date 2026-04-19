from .ast_node import ASTNode
from .xml_utils import *

from .paragraph_parser import parse_paragraph
from .table_properties_parser import parse_table_properties
from .cell_properties_parser import parse_cell_properties


def parse_table(tbl, context):

    table_node = ASTNode("table", "w:tbl")

    try:

        # TABLE PROPERTIES
        tblPr = safe_find(tbl, "w:tblPr")
        parse_table_properties(tblPr, table_node)

        rows = safe_findall(tbl, "w:tr")

        for r in rows:

            row_node = ASTNode("table_row", "w:tr")

            trPr = safe_find(r, "w:trPr")

            if trPr is not None:
                jc = safe_find(trPr, "w:jc")

                if jc is not None:
                    val = jc.attrib.get(qn("w:val"))
                    if val:
                        row_node.layout["alignment"] = val

            cells = safe_findall(r, "w:tc")

            for c in cells:

                cell_node = ASTNode("table_cell", "w:tc")

                # CELL PROPERTIES
                tcPr = safe_find(c, "w:tcPr")
                parse_cell_properties(tcPr, cell_node)

                # PARAGRAPHS IN CELL
                paragraphs = safe_findall(c, "w:p")

                for p in paragraphs:
                    cell_node.add_child(parse_paragraph(p, context))

                row_node.add_child(cell_node)

            table_node.add_child(row_node)

    except Exception as e:
        table_node.add_error(e)

    return table_node
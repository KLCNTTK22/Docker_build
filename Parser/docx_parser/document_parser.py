import xml.etree.ElementTree as ET

from .ast_node import ASTNode
from .xml_utils import *
from .paragraph_parser import parse_paragraph
from .table_parser import parse_table
from .section_parser import parse_section
from .sdt_parser import parse_sdt

def parse_document(xml, context):

    root = ET.fromstring(xml)
    doc_node = ASTNode("document", "w:document")
    if "metadata" in context and context["metadata"]:
        doc_node.properties["metadata"] = context["metadata"]
    body = safe_find(root, "w:body")

    if body is not None:
        for child in body:

            tag = child.tag.split("}")[-1]

            if tag == "p":
                doc_node.add_child(parse_paragraph(child, context))

            elif tag == "tbl":
                doc_node.add_child(parse_table(child, context))

            elif tag == "sdt":
                # Xử lý SDT bọc các Paragraph (như TOC - Mục lục)
                doc_node.add_child(parse_sdt(child, context))

            elif tag == "sectPr":
                parse_section(child, doc_node, context)

            else:
                doc_node.add_unknown(tag)

    return doc_node
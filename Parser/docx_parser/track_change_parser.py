from .ast_node import ASTNode
from .xml_utils import *

def parse_insert(elem):

    node = ASTNode("insert", "w:ins")

    node.attributes = {
        "author": elem.attrib.get(qn("w:author")),
        "date": elem.attrib.get(qn("w:date"))
    }

    return node


def parse_delete(elem):

    node = ASTNode("delete", "w:del")

    node.attributes = {
        "author": elem.attrib.get(qn("w:author")),
        "date": elem.attrib.get(qn("w:date"))
    }

    return node
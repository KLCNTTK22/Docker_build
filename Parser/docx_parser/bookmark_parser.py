from .ast_node import ASTNode
from .xml_utils import *

def parse_bookmark_start(elem):

    node = ASTNode("bookmarkStart", "w:bookmarkStart")

    node.attributes = {
        "id": elem.attrib.get(qn("w:id")),
        "name": elem.attrib.get(qn("w:name"))
    }

    return node


def parse_bookmark_end(elem):

    node = ASTNode("bookmarkEnd", "w:bookmarkEnd")

    node.attributes = {
        "id": elem.attrib.get(qn("w:id"))
    }

    return node
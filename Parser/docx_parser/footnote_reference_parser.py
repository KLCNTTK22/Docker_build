from .ast_node import ASTNode
from .xml_utils import *

def parse_footnote_reference(elem):

    node = ASTNode("footnoteReference", "w:footnoteReference")

    node.references.append({
        "type": "footnote",
        "id": elem.attrib.get(qn("w:id"))
    })

    return node
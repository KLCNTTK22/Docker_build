from .ast_node import ASTNode
from .xml_utils import *
from .toc_parser import parse_toc_field

def parse_field_simple(elem):

    instr = elem.attrib.get(qn("w:instr"))

    toc = parse_toc_field(instr)

    if toc:
        return toc

    node = ASTNode("field", "w:fldSimple")

    node.properties["instruction"] = instr

    return node
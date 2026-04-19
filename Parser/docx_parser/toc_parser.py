from .ast_node import ASTNode
from .xml_utils import *

def parse_toc_field(instr):

    if not instr:
        return None

    if "TOC" not in instr:
        return None

    node = ASTNode("toc", "w:fldSimple")

    node.properties["instruction"] = instr

    # parse options
    options = {}

    if "\\o" in instr:
        options["headingLevels"] = instr.split("\\o")[1].split()[0]

    if "\\h" in instr:
        options["hyperlinks"] = True

    if "\\z" in instr:
        options["hidePageNumbersInWeb"] = True

    if "\\u" in instr:
        options["useOutlineLevels"] = True

    node.properties["options"] = options

    return node
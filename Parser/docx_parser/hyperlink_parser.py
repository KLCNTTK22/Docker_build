from .ast_node import ASTNode
from .xml_utils import *
from .run_parser import parse_run

def parse_hyperlink(elem, context):

    node = ASTNode("hyperlink", "w:hyperlink")

    rid = elem.attrib.get(qn("r:id"))

    if rid and rid in context["relationships"]:
        node.references.append({
            "type": "hyperlink",
            "url": context["relationships"][rid]
        })

    for r in safe_findall(elem, "w:r"):
        node.add_child(parse_run(r, context))

    return node
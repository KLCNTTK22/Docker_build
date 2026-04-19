from .ast_node import ASTNode
from .xml_utils import *

def parse_chart(drawing, context):

    graphicData = drawing.find(".//a:graphicData", NS)

    if graphicData is None:
        return None

    uri = graphicData.attrib.get("uri")

    if "chart" not in uri:
        return None

    node = ASTNode("chart", "a:graphicData")

    chart = graphicData.find(".//c:chart", {
        "c": "http://schemas.openxmlformats.org/drawingml/2006/chart"
    })

    rid = None

    if chart is not None:
        rid = chart.attrib.get(qn("r:id"))

    if rid and rid in context["relationships"]:
        node.references.append({
            "type": "chart",
            "target": context["relationships"][rid],
            "rid": rid
        })

    return node
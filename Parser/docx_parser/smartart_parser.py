import xml.etree.ElementTree as ET
from .ast_node import ASTNode
from .xml_utils import *
from .smartart_data_parser import parse_smartart_data

def parse_smartart(drawing, context):
    """
    Phân giải SmartArt và xử lý rId để mở file data[n].xml chuẩn xác
    """
    graphicData = drawing.find(".//a:graphicData", NS)
    if graphicData is None or "diagram" not in graphicData.attrib.get("uri", ""):
        return None

    node = ASTNode("smartart", "a:graphicData")

    # Tìm liên kết rId trong dgm:relIds
    rel = drawing.find(".//dgm:relIds", NS)
    if rel is None:
        rel = drawing.find(".//{http://schemas.openxmlformats.org/drawingml/2006/diagram}relIds")

    if rel is None:
        return node

    # RID trỏ tới Data Model (dm)
    data_rid = rel.attrib.get(qn("r:dm"))
    if not data_rid:
        return node

    relationships = context.get("relationships", {})
    files = context.get("files", {})

    target_path = relationships.get(data_rid)
    if target_path:
        # 🔥 FIX: Xử lý đường dẫn tương đối chuẩn xác
        # Các rels trong word/_rels/ trỏ tương đối từ thư mục 'word/'
        if target_path.startswith("../"):
            # Ví dụ: ../customXml/item1.xml -> customXml/item1.xml
            full_path = target_path.replace("../", "")
        elif not target_path.startswith("word/"):
            full_path = f"word/{target_path}"
        else:
            full_path = target_path

        xml_content = files.get(full_path)

        if xml_content:
            try:
                xml_root = ET.fromstring(xml_content)
                data_node = parse_smartart_data(xml_root, context)
                if data_node:
                    node.add_child(data_node)
                    node.text = data_node.text
            except Exception as e:
                node.add_error(f"SmartArt XML Error: {str(e)}")
        else:
            node.add_error(f"File not found in zip: {full_path}")

    return node
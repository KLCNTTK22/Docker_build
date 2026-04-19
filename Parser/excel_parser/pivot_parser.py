import xml.etree.ElementTree as ET
from .ast_node import ASTNode
from .xml_utils import NAMESPACES


def parse_pivot_table(xml_content, pivot_id):
    """
    Phân tích file xl/pivotTables/pivotTableX.xml
    Trả về một ASTNode đại diện cho Pivot Table
    """
    if not xml_content:
        return None

    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError:
        return None

    pivot_node = ASTNode(type_="pivotTable", tag="pivotTableDefinition")
    pivot_node.properties = {
        "id": pivot_id,
        "name": root.attrib.get("name", "")
    }

    # 1. Vị trí đặt Pivot Table
    location = root.find('main:location', NAMESPACES)
    if location is not None:
        pivot_node.layout["ref"] = location.attrib.get("ref")

    # 2. Lấy danh sách toàn bộ Pivot Fields (Để biết field nào có index là bao nhiêu)
    # Lấy tên field thông qua cache thì phức tạp, thường đề thi ta quan tâm "Cấu trúc" hơn
    pivot_fields = []
    p_fields_node = root.find('main:pivotFields', NAMESPACES)
    if p_fields_node is not None:
        for p_field in p_fields_node.findall('main:pivotField', NAMESPACES):
            # Các field thường đi kèm với danh sách items, nhưng để chấm điểm ta chỉ cần phân tích nó nằm ở vùng nào
            pivot_fields.append(p_field.attrib)

    # 3. Phân tích Row Fields (Kéo vào vùng Rows)
    row_fields = root.find('main:rowFields', NAMESPACES)
    if row_fields is not None:
        rows = []
        for field in row_fields.findall('main:field', NAMESPACES):
            rows.append(field.attrib.get('x'))  # x là index của trường dữ liệu
        pivot_node.properties["row_fields_index"] = rows

    # 4. Phân tích Data Fields (Kéo vào vùng Values - SUM, COUNT...)
    data_fields_node = root.find('main:dataFields', NAMESPACES)
    if data_fields_node is not None:
        data_fields = []
        for df in data_fields_node.findall('main:dataField', NAMESPACES):
            data_fields.append({
                "name": df.attrib.get("name"),
                "fld": df.attrib.get("fld"),  # Trỏ tới index của field
                "subtotal": df.attrib.get("subtotal", "sum")  # Hàm tính toán: sum, count, average...
            })
        pivot_node.properties["data_fields"] = data_fields

    return pivot_node
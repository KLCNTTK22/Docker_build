import xml.etree.ElementTree as ET
from .xml_utils import NAMESPACES


def parse_workbook(xml_content):
    """
    Phân tích nội dung file xl/workbook.xml
    Trả về danh sách các sheets, chứa tên, sheetId và relsId
    """
    if not xml_content:
        return []

    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError:
        return []

    sheets = []
    sheets_node = root.find('main:sheets', NAMESPACES)

    if sheets_node is not None:
        for sheet in sheets_node.findall('main:sheet', NAMESPACES):
            # Trong XML: r:id="rId1", ta cần lấy đúng Namespace 'r' để truy xuất attributes
            r_id_key = f"{{{NAMESPACES['r']}}}id"

            sheets.append({
                "name": sheet.attrib.get('name'),
                "sheetId": sheet.attrib.get('sheetId'),
                "rId": sheet.attrib.get(r_id_key)
            })

    return sheets
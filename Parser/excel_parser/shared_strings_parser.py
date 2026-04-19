import xml.etree.ElementTree as ET

from .xml_utils import NAMESPACES


def parse_shared_strings(xml_content):
    """
    Phân tích nội dung file xl/sharedStrings.xml
    Trả về một mảng (List) các chuỗi.
    """
    if not xml_content:
        return []

    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError:
        return []

    shared_strings = []

    for si in root.findall('main:si', NAMESPACES):
        text_parts = []
        # Quét mọi thẻ <t> bên trong (Bao gồm cả text thường và Rich text)
        for t_node in si.findall('.//main:t', NAMESPACES):
            if t_node.text:
                text_parts.append(t_node.text)

        full_string = "".join(text_parts)
        shared_strings.append(full_string)

    return shared_strings
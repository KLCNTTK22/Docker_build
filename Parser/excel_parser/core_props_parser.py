import xml.etree.ElementTree as ET
from .xml_utils import NAMESPACES


def parse_core_props(xml_content):
    """
    Phân tích file docProps/core.xml
    Trả về dictionary chứa các metadata của tài liệu.
    """
    if not xml_content:
        return {}

    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError:
        return {}

    props = {}

    # Lấy thông tin người tạo
    creator = root.find('dc:creator', NAMESPACES)
    if creator is not None and creator.text:
        props['creator'] = creator.text

    # Lấy thông tin người chỉnh sửa cuối
    last_modified_by = root.find('cp:lastModifiedBy', NAMESPACES)
    if last_modified_by is not None and last_modified_by.text:
        props['lastModifiedBy'] = last_modified_by.text

    # Lấy ngày tạo
    created = root.find('dcterms:created', NAMESPACES)
    if created is not None and created.text:
        props['created'] = created.text

    # Lấy ngày chỉnh sửa
    modified = root.find('dcterms:modified', NAMESPACES)
    if modified is not None and modified.text:
        props['modified'] = modified.text

    return props
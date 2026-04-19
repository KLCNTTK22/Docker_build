import xml.etree.ElementTree as ET
from .xml_utils import *


def parse_core_properties(xml_content):
    """
    Phân tích docProps/core.xml để trích xuất Metadata của tài liệu.
    """
    if not xml_content:
        return {}

    root = ET.fromstring(xml_content)

    metadata = {}

    # Hàm bổ trợ lấy chuỗi text an toàn
    def get_text(tag, namespace):
        elem = root.find(f".//{namespace}:{tag}", NS)
        return elem.text if elem is not None else None

    # Trích xuất các trường thông tin quan trọng
    metadata["creator"] = get_text("creator", "dc")
    metadata["lastModifiedBy"] = get_text("lastModifiedBy", "cp")
    metadata["created"] = get_text("created", "dcterms")
    metadata["modified"] = get_text("modified", "dcterms")
    metadata["revision"] = get_text("revision", "cp")

    # Chỉ trả về các trường có dữ liệu (lọc bỏ None)
    return {k: v for k, v in metadata.items() if v}
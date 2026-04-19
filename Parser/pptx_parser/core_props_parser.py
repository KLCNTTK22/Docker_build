import xml.etree.ElementTree as ET
from .xml_utils import NAMESPACES


def parse_core_props(xml_content):
    """
    Trích xuất metadata cốt lõi từ file docProps/core.xml.
    (Chứa thông tin tác giả, người sửa cuối, ngày tạo, phiên bản...)
    """
    props = {}
    try:
        # Parse XML từ string
        root = ET.fromstring(xml_content.encode('utf-8'))

        # Danh sách các thẻ thường gặp và quan trọng cần trích xuất
        tags_to_extract = [
            ('dc', 'title'),
            ('dc', 'creator'),
            ('dc', 'description'),
            ('dc', 'subject'),
            ('cp', 'lastModifiedBy'),
            ('cp', 'revision'),
            ('dcterms', 'created'),
            ('dcterms', 'modified')
        ]

        for prefix, tag_name in tags_to_extract:
            # Xây dựng tag kèm namespace theo chuẩn của ElementTree (vd: {http://...}creator)
            full_tag = f"{{{NAMESPACES[prefix]}}}{tag_name}"
            element = root.find(full_tag)

            if element is not None and element.text:
                # Lưu vào dict với key giữ nguyên dạng prefix:tag (vd: dc:creator)
                # Việc này giúp đồng bộ cấu trúc với AST mà ta đã thống nhất
                key = f"{prefix}:{tag_name}"
                props[key] = element.text

    except Exception as e:
        print(f"[Cảnh báo] Lỗi khi parse core.xml: {e}")

    return props
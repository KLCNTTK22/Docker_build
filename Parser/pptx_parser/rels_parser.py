import xml.etree.ElementTree as ET

RELS_NS = "http://schemas.openxmlformats.org/package/2006/relationships"


def parse_rels(xml_content):
    """
    Trích xuất thông tin từ các file .rels (Relationships).
    Trả về dictionary ánh xạ từ Id (ví dụ: rId1) sang thông tin chi tiết (Target, Type, TargetMode).
    """
    relationships = {}

    if not xml_content:
        return relationships

    try:
        # Parse XML từ string
        root = ET.fromstring(xml_content.encode('utf-8'))

        # Tìm tất cả các thẻ <Relationship>
        for rel in root.findall(f"{{{RELS_NS}}}Relationship"):
            r_id = rel.attrib.get("Id")
            if r_id:
                relationships[r_id] = {
                    "Id": r_id,
                    "Type": rel.attrib.get("Type", ""),
                    "Target": rel.attrib.get("Target", ""),
                    # TargetMode thường là "Internal" (file bên trong zip).
                    # Nếu là Hyperlink trỏ ra web ngoài, nó sẽ là "External".
                    "TargetMode": rel.attrib.get("TargetMode", "Internal")
                }

    except Exception as e:
        print(f"[Cảnh báo] Lỗi khi parse file .rels: {e}")

    return relationships
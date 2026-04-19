import xml.etree.ElementTree as ET
from .xml_utils import *


def parse_notes(xml_content, context, note_type="footnote"):
    """
    Phân tích file footnotes.xml hoặc endnotes.xml.
    Trả về Dictionary: { "id": [Danh sách các Node con] }
    """
    if not xml_content:
        return {}

    # Import cục bộ bằng relative import
    from .paragraph_parser import parse_paragraph
    from .table_parser import parse_table

    root = ET.fromstring(xml_content)
    notes = {}

    tag_name = "w:footnote" if note_type == "footnote" else "w:endnote"

    for note in root.findall(f".//{tag_name}", NS):
        note_id = note.attrib.get(qn("w:id"))
        note_type_attr = note.attrib.get(qn("w:type"))

        # Bỏ qua các separator (đường gạch ngang)
        if note_type_attr in ["separator", "continuationSeparator"]:
            continue

        children = []
        for child in note:
            tag = child.tag.split("}")[-1]

            if tag == "p":
                children.append(parse_paragraph(child, context))
            elif tag == "tbl":
                children.append(parse_table(child, context))

        notes[note_id] = children

    return notes
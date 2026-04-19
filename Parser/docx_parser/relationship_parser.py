import xml.etree.ElementTree as ET

def parse_relationships(xml):

    rels = {}

    root = ET.fromstring(xml)

    for rel in root:

        rid = rel.attrib.get("Id")
        target = rel.attrib.get("Target")

        rels[rid] = target

    return rels
import xml.etree.ElementTree as ET

NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "wp": "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing",
    "w14": "http://schemas.microsoft.com/office/word/2010/wordml",
    "wps": "http://schemas.microsoft.com/office/word/2010/wordprocessingShape",
    "dgm": "http://schemas.openxmlformats.org/drawingml/2006/diagram",
    "pic": "http://schemas.openxmlformats.org/drawingml/2006/picture",
    "mc": "http://schemas.openxmlformats.org/markup-compatibility/2006",
    "v": "urn:schemas-microsoft-com:vml",
    "o": "urn:schemas-microsoft-com:office:office",
    "cp": "http://schemas.openxmlformats.org/package/2006/metadata/core-properties",
    "dc": "http://purl.org/dc/elements/1.1/",
    "dcterms": "http://purl.org/dc/terms/"
}

def qn(tag):
    prefix, tagroot = tag.split(":")
    uri = NS[prefix]
    return f"{{{uri}}}{tagroot}"

def safe_find(elem, path):
    try:
        return elem.find(path, NS)
    except:
        return None

def safe_findall(elem, path):
    try:
        return elem.findall(path, NS)
    except:
        return []
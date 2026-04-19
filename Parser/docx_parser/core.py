import zipfile
import json

from .document_parser import parse_document
from .relationship_parser import parse_relationships
from .styles_parser import parse_styles
from .numbering_parser import parse_numbering
from .theme_parser import parse_theme
from .notes_parser import parse_notes
from .clean import clean_word_json
from .properties_core_parser import parse_core_properties


def load_docx(path):
    files = {}
    with zipfile.ZipFile(path) as z:
        for name in z.namelist():
            if name.endswith(".xml") or name.endswith(".rels"):
                try:
                    files[name] = z.read(name).decode("utf-8")
                except:
                    pass
    return files


def build_context(files):
    context = {
        "relationships": {},
        "styles": {},
        "numbering": {},
        "themeFonts": {},
        "footnotes": {},
        "endnotes": {},
        "metadata": {},
        "files": files
    }

    # Theme
    theme_xml = files.get("word/theme/theme1.xml")
    if theme_xml:
        context["themeFonts"] = parse_theme(theme_xml)

    # Relationships
    rels_xml = files.get("word/_rels/document.xml.rels")
    if rels_xml:
        context["relationships"] = parse_relationships(rels_xml)

    # Styles
    styles_xml = files.get("word/styles.xml")
    if styles_xml:
        styles_data = parse_styles(styles_xml)
        context["styles"] = styles_data["styles"]
        context["default"] = styles_data["default"]

    # Numbering
    numbering_xml = files.get("word/numbering.xml")
    if numbering_xml:
        context["numbering"] = parse_numbering(numbering_xml)

    # Notes (Footnotes & Endnotes)
    footnotes_xml = files.get("word/footnotes.xml")
    if footnotes_xml:
        context["footnotes"] = parse_notes(footnotes_xml, context, "footnote")

    endnotes_xml = files.get("word/endnotes.xml")
    if endnotes_xml:
        context["endnotes"] = parse_notes(endnotes_xml, context, "endnote")

    # Meta data
    core_xml = files.get("docProps/core.xml")
    if core_xml:
        context["metadata"] = parse_core_properties(core_xml)

    return context


def parse_docx(path, clean=True):
    files = load_docx(path)
    context = build_context(files)

    document_xml = files.get("word/document.xml")
    if not document_xml:
        raise ValueError("document.xml not found in docx")

    ast = parse_document(document_xml, context)

    if ast is None:
        return None

    data = ast.to_dict()

    if clean:
        data = clean_word_json(data)

    return data


def parse_docx_to_file(input_path, output_path, clean=True):
    data = parse_docx(input_path, clean=clean)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    return data
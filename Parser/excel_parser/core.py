import zipfile
import json
import re

from .ast_node import ASTNode
from .shared_strings_parser import parse_shared_strings
from .workbook_parser import parse_workbook
from .sheet_parser import parse_sheet
from .styles_parser import parse_styles
from .chart_parser import parse_chart
from .pivot_parser import parse_pivot_table
from .core_props_parser import parse_core_props
from .clean import clean_json


def load_xlsx(path):
    files = {}
    with zipfile.ZipFile(path) as z:
        for name in z.namelist():
            if name.endswith(".xml") or name.endswith(".rels"):
                try:
                    files[name] = z.read(name).decode("utf-8")
                except Exception:
                    pass
    return files


def build_context(files):
    context = {
        "shared_strings": [],
        "workbook_sheets": [],
        "styles": {},
        "files": files
    }

    shared_strings_xml = files.get("xl/sharedStrings.xml")
    if shared_strings_xml:
        context["shared_strings"] = parse_shared_strings(shared_strings_xml)

    workbook_xml = files.get("xl/workbook.xml")
    if workbook_xml:
        context["workbook_sheets"] = parse_workbook(workbook_xml)

    styles_xml = files.get("xl/styles.xml")
    if styles_xml:
        context["styles"] = parse_styles(styles_xml)

    return context


def parse_xlsx(path, clean=True):
    files = load_xlsx(path)
    context = build_context(files)

    ast_root = ASTNode(type_="workbook", tag="workbook")
    ast_root.properties["shared_strings_count"] = len(context["shared_strings"])

    # --- ĐỌC CORE PROPERTIES (Metadata) ---
    core_xml = files.get("docProps/core.xml")
    if core_xml:
        core_props = parse_core_props(core_xml)
        if core_props:
            ast_root.properties["core_properties"] = core_props

    # --- 1. XỬ LÝ SHEETS ---
    for sheet_info in context["workbook_sheets"]:
        rid_match = re.search(r'\d+', sheet_info.get("rId", ""))
        target_id = rid_match.group() if rid_match else sheet_info.get("sheetId")

        sheet_xml_path = f"xl/worksheets/sheet{target_id}.xml"
        sheet_xml = files.get(sheet_xml_path)

        if sheet_xml:
            sheet_node = parse_sheet(sheet_xml, context, sheet_info)
            if sheet_node:
                ast_root.add_child(sheet_node)

    # --- 2. XỬ LÝ CHARTS (PHASE 4) ---
    # Quét tất cả các file trong cấu trúc zip có chứa "xl/charts/chart"
    chart_files = [f for f in files.keys() if f.startswith("xl/charts/chart") and f.endswith(".xml")]
    for chart_file in chart_files:
        # Tách id từ tên file (vd: chart1.xml -> 1)
        match = re.search(r'chart(\d+)\.xml', chart_file)
        chart_id = match.group(1) if match else "unknown"

        chart_node = parse_chart(files[chart_file], chart_id)
        if chart_node:
            ast_root.add_child(chart_node)

    # --- 3. XỬ LÝ PIVOT TABLES (PHASE 4) ---
    pivot_files = [f for f in files.keys() if f.startswith("xl/pivotTables/pivotTable") and f.endswith(".xml")]
    for pivot_file in pivot_files:
        match = re.search(r'pivotTable(\d+)\.xml', pivot_file)
        pivot_id = match.group(1) if match else "unknown"

        pivot_node = parse_pivot_table(files[pivot_file], pivot_id)
        if pivot_node:
            ast_root.add_child(pivot_node)

    data = ast_root.to_dict()

    if clean:
        data = clean_json(data)

    return data


def parse_xlsx_to_file(input_path, output_path, clean=True):
    data = parse_xlsx(input_path, clean=clean)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return data

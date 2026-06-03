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
                    # LOGIC BỌC THÉP 1: Dọn dẹp thẻ <?xml ...?> để chống sập ElementTree
                    content = z.read(name).decode("utf-8")
                    content = re.sub(r'^<\?xml[^>]+>\s*', '', content)
                    files[name] = content
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
    ast_root.properties["shared_strings_count"] = len(context.get("shared_strings", []))

    # --- ĐỌC CORE PROPERTIES (Metadata - Bỏ qua an toàn nếu mất thư mục docProps) ---
    core_xml = files.get("docProps/core.xml")
    if core_xml:
        core_props = parse_core_props(core_xml)
        if core_props:
            ast_root.properties["core_properties"] = core_props

    # ---> LOGIC BỌC THÉP 2: ĐỘC LẬP TÌM DANH SÁCH SHEET BẰNG REGEX <---
    wb_xml = files.get("xl/workbook.xml", "")
    sheets_info = []

    # Quét tàn bạo mọi thẻ <sheet> bất chấp Namespace
    for match in re.finditer(r'<[^:]*:?sheet\s+([^>]+)/?>', wb_xml, re.IGNORECASE):
        attrs = match.group(1)
        name_m = re.search(r'name="([^"]+)"', attrs, re.IGNORECASE)
        id_m = re.search(r'sheetId="([^"]+)"', attrs, re.IGNORECASE)
        rid_m = re.search(r'id="([^"]+)"', attrs, re.IGNORECASE)

        if name_m:
            sheets_info.append({
                "name": name_m.group(1),
                "sheetId": id_m.group(1) if id_m else "unknown",
                "rId": rid_m.group(1) if rid_m else ""
            })

    # Fallback nếu Regex vẫn không tìm thấy thì dùng context cũ
    if not sheets_info:
        sheets_info = context.get("workbook_sheets", [])

    # ---> LOGIC BỌC THÉP 3: ĐỌC SỔ DANH BẠ (_rels) ĐỂ TÌM ĐƯỜNG DẪN THỰC TẾ <---
    rels_xml = files.get("xl/_rels/workbook.xml.rels", "")
    rid_map = {}
    for match in re.finditer(r'<[^:]*:?Relationship\s+([^>]+)/?>', rels_xml, re.IGNORECASE):
        attrs = match.group(1)
        id_m = re.search(r'Id="([^"]+)"', attrs, re.IGNORECASE)
        target_m = re.search(r'Target="([^"]+)"', attrs, re.IGNORECASE)
        if id_m and target_m:
            rid_map[id_m.group(1)] = target_m.group(1)

    # --- 1. XỬ LÝ SHEETS ---
    for sheet_info in sheets_info:
        r_id = sheet_info.get("rId", "")
        target_file = rid_map.get(r_id)

        if target_file:
            target_file = target_file.lstrip('/')
            sheet_xml_path = f"xl/{target_file}" if not target_file.startswith("xl/") else target_file
        else:
            rid_match = re.search(r'\d+', r_id)
            target_id = rid_match.group() if rid_match else sheet_info.get("sheetId")
            sheet_xml_path = f"xl/worksheets/sheet{target_id}.xml"

        sheet_xml = files.get(sheet_xml_path)

        if sheet_xml:
            sheet_node = parse_sheet(sheet_xml, context, sheet_info)
            if sheet_node:
                ast_root.add_child(sheet_node)

    # --- 2. XỬ LÝ CHARTS (PHASE 4) ---
    chart_files = [f for f in files.keys() if f.startswith("xl/charts/chart") and f.endswith(".xml")]
    for chart_file in chart_files:
        match = re.search(r'chart(\d+)\.xml', chart_file)
        chart_id = match.group(1) if match else "unknown"
        chart_node = parse_chart(files[chart_file], chart_id)
        if chart_node: ast_root.add_child(chart_node)

    # --- 3. XỬ LÝ PIVOT TABLES (PHASE 4) ---
    pivot_files = [f for f in files.keys() if f.startswith("xl/pivotTables/pivotTable") and f.endswith(".xml")]
    for pivot_file in pivot_files:
        match = re.search(r'pivotTable(\d+)\.xml', pivot_file)
        pivot_id = match.group(1) if match else "unknown"
        pivot_node = parse_pivot_table(files[pivot_file], pivot_id)
        if pivot_node: ast_root.add_child(pivot_node)

    data = ast_root.to_dict()
    if clean: data = clean_json(data)
    return data


def parse_xlsx_to_file(input_path, output_path, clean=True):
    data = parse_xlsx(input_path, clean=clean)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return data
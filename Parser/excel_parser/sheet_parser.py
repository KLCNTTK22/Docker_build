import xml.etree.ElementTree as ET
from .ast_node import ASTNode
from .xml_utils import NAMESPACES


def get_tag_name(element):
    return element.tag.split('}')[-1]


def parse_sheet(xml_content, context, sheet_info):
    if not xml_content: return None

    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError as e:
        err_node = ASTNode(type_="worksheet", tag="worksheet")
        err_node.add_error(f"XML Parse Error: {e}")
        return err_node

    sheet_node = ASTNode(type_="worksheet", tag="worksheet")
    sheet_node.properties = {"name": sheet_info.get("name"), "sheetId": sheet_info.get("sheetId")}

    # --- KHỞI TẠO SỔ TAY LƯU CÔNG THỨC (SHARED FORMULA) CHO SHEET NÀY ---
    context["shared_formulas"] = {}

    IGNORED_TAGS = ['dimension', 'sheetViews', 'sheetFormatPr', 'cols', 'pageMargins', 'extLst', 'sheetPr']

    for child in root:
        tag_name = get_tag_name(child)

        try:
            if tag_name in IGNORED_TAGS:
                continue

            elif tag_name == 'sheetData':
                for row_elem in child.findall('main:row', NAMESPACES):
                    row_node = parse_row(row_elem, context)
                    sheet_node.add_child(row_node)

            elif tag_name == 'autoFilter':
                filter_data = {"ref": child.attrib.get("ref")}
                filter_cols = []
                for f_col in child.findall('main:filterColumn', NAMESPACES):
                    col_id = f_col.attrib.get('colId')
                    filters = f_col.find('main:filters', NAMESPACES)
                    if filters is not None:
                        for f_val in filters.findall('main:filter', NAMESPACES):
                            filter_cols.append({"colId": col_id, "val": f_val.attrib.get('val')})
                if filter_cols: filter_data["columns"] = filter_cols
                sheet_node.section["autoFilter"] = filter_data

            elif tag_name == 'conditionalFormatting':
                cf_data = {"sqref": child.attrib.get("sqref"), "rules": []}
                for rule_elem in child.findall('main:cfRule', NAMESPACES):
                    rule_data = {"type": rule_elem.attrib.get("type"), "operator": rule_elem.attrib.get("operator", ""),
                                 "priority": rule_elem.attrib.get("priority", "")}
                    formula_elem = rule_elem.find('main:formula', NAMESPACES)
                    if formula_elem is not None and formula_elem.text: rule_data["formula"] = formula_elem.text

                    dxf_id = rule_elem.attrib.get("dxfId")
                    if dxf_id is not None:
                        rule_data["dxfId"] = dxf_id
                        try:
                            idx = int(dxf_id)
                            dxfs_context = context.get("styles", {}).get("dxfs", [])
                            if 0 <= idx < len(dxfs_context):
                                rule_data["format"] = dxfs_context[idx]
                        except ValueError:
                            pass

                    cf_data["rules"].append(rule_data)

                if "conditionalFormatting" not in sheet_node.section:
                    sheet_node.section["conditionalFormatting"] = []
                sheet_node.section["conditionalFormatting"].append(cf_data)

            elif tag_name == 'sortState':
                sheet_node.section["sortState"] = child.attrib.get("ref")

            # --- XỬ LÝ MERGE CELLS (GỘP Ô) ---
            elif tag_name == 'mergeCells':
                merged_list = []
                for merge_cell in child.findall('main:mergeCell', NAMESPACES):
                    ref = merge_cell.attrib.get('ref')
                    if ref:
                        merged_list.append(ref)

                if merged_list:
                    # Đưa vào layout của sheet
                    sheet_node.layout["mergeCells"] = merged_list

            else:
                sheet_node.add_unknown(tag_name)

        except Exception as e:
            sheet_node.add_error(f"Error parsing tag <{tag_name}>: {str(e)}")

    return sheet_node


def parse_row(row_elem, context):
    row_node = ASTNode(type_="row", tag="row")
    row_node.attributes = {"r": row_elem.attrib.get("r")}
    if row_elem.attrib.get("hidden") == "1": row_node.layout["hidden"] = True

    for child in row_elem:
        tag_name = get_tag_name(child)
        try:
            if tag_name == 'c':
                cell_node = parse_cell(child, context)
                row_node.add_child(cell_node)
            elif tag_name == 'extLst':
                continue
            else:
                row_node.add_unknown(tag_name)
        except Exception as e:
            row_node.add_error(f"Error parsing row tag <{tag_name}>: {str(e)}")

    return row_node


def parse_cell(cell_elem, context):
    cell_node = ASTNode(type_="cell", tag="c")
    cell_type = cell_elem.attrib.get("t")
    style_idx = cell_elem.attrib.get("s")
    cell_node.attributes = {"r": cell_elem.attrib.get("r")}
    cell_node.properties["is_dynamic_formula"] = False

    if cell_type: cell_node.attributes["t"] = cell_type

    if style_idx:
        cell_node.attributes["s"] = style_idx
        try:
            s_id = int(style_idx)
            styles_context = context.get("styles", {}).get("cellXfs", [])
            if 0 <= s_id < len(styles_context):
                cell_style = styles_context[s_id]
                if cell_style:
                    cell_node.style = cell_style
                    if "numFmtId" in cell_style:
                        cell_node.properties["numFmtId"] = cell_style["numFmtId"]
        except ValueError:
            cell_node.add_error(f"Invalid style index: {style_idx}")

    for child in cell_elem:
        tag_name = get_tag_name(child)
        try:
            if tag_name == 'f':
                formula_text = child.text
                f_type = child.attrib.get("t")
                si = child.attrib.get("si")

                # --- LOGIC MỚI: XỬ LÝ SHARED FORMULA ---
                if f_type == "shared" and si is not None:
                    if formula_text:
                        # Đây là ô Master: Lưu công thức vào sổ tay
                        context["shared_formulas"][si] = formula_text
                    else:
                        # Đây là ô Copy: Lấy từ sổ tay ra đắp vào
                        formula_text = context.get("shared_formulas", {}).get(si, "")

                f_node = ASTNode(type_="formula", tag="f", text=formula_text)
                cell_node.add_child(f_node)
                cell_node.properties["is_dynamic_formula"] = True

            elif tag_name == 'v':
                val_text = child.text
                if cell_type == "s":
                    try:
                        idx = int(val_text)
                        shared_strings = context.get("shared_strings", [])
                        if 0 <= idx < len(shared_strings):
                            val_text = shared_strings[idx]
                    except ValueError:
                        cell_node.add_error(f"Invalid shared string index: {val_text}")
                v_node = ASTNode(type_="value", tag="v", text=val_text)
                cell_node.add_child(v_node)
            elif tag_name == 'is':
                text_parts = [t.text for t in child.findall('.//main:t', NAMESPACES) if t.text]
                if text_parts:
                    v_node = ASTNode(type_="value", tag="is", text="".join(text_parts))
                    cell_node.add_child(v_node)
            elif tag_name == 'extLst':
                continue
            else:
                cell_node.add_unknown(tag_name)
        except Exception as e:
            cell_node.add_error(f"Error parsing cell tag <{tag_name}>: {str(e)}")

    return cell_node
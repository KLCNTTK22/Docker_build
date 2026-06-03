import json

from Parser.excel_parser.core import parse_xlsx


def extract_all_text(node):
    if not isinstance(node, dict): return ""
    text = str(node.get("text", "")) if node.get("text") else ""
    for child in node.get("children", []):
        text += extract_all_text(child)
    return text


def parse_col_index(rule):
    val = rule.get("col_index", -1)
    if isinstance(val, int): return val

    val_str = str(val).strip().upper()
    if val_str.isdigit(): return int(val_str)

    if val_str.isalpha():
        num = 0
        for c in val_str:
            if 'A' <= c <= 'Z':
                num = num * 26 + (ord(c) - ord('A') + 1)
        return num - 1  # 0-based index
    return -1


def get_dynamic_col_index(rule, anchor_row_node):
    # Hỗ trợ cả key cũ "col_header" và key mới "target_column"
    expected_header = str(rule.get("target_column", rule.get("col_header", ""))).strip().lower()
    
    if expected_header and isinstance(anchor_row_node, dict):
        cells = [c for c in anchor_row_node.get("children", []) if isinstance(c, dict) and c.get("type") == "cell"]
        for i, cell in enumerate(cells):
            cell_text = str(extract_all_text(cell)).strip().lower()
            if expected_header in cell_text:
                return i

    return parse_col_index(rule)


def get_cell_data(row_node, col_index):
    try:
        if not isinstance(row_node, dict): return None
        cells = [c for c in row_node.get("children", []) if isinstance(c, dict) and c.get("type") == "cell"]
        if col_index < 0 or col_index >= len(cells): return None

        cell = cells[col_index]
        is_dynamic = cell.get("properties", {}).get("is_dynamic_formula", False)
        r_coord = cell.get("attributes", {}).get("r", "Unknown")

        value, formula = "", ""
        for child in cell.get("children", []):
            if not isinstance(child, dict): continue
            if child.get("tag") == "v" or child.get("type") == "value": 
                value = child.get("text", child.get("value", ""))
            if child.get("tag") == "f" or child.get("type") == "formula": 
                formula = child.get("text", child.get("value", ""))

        return {"is_dynamic": is_dynamic, "value": value, "formula": formula, "coord": r_coord}
    except Exception:
        return None


def resolve_ref_to_text(parsed_data, ref_str):
    try:
        if "!" not in ref_str: return ""
        sheet_name, cell_coord = ref_str.split("!")
        sheet_name = sheet_name.replace("'", "") 
        cell_coord = cell_coord.replace("$", "").split(":")[0] 

        for child in parsed_data.get("children", []):
            if child.get("type") == "worksheet" and child.get("properties", {}).get("name") == sheet_name:
                for row in child.get("children", []):
                    if row.get("type") == "row":
                        for cell in row.get("children", []):
                            if cell.get("attributes", {}).get("r") == cell_coord:
                                for v in cell.get("children", []):
                                    if v.get("tag") == "v" or v.get("type") == "value":
                                        return str(v.get("text", v.get("value", ""))).strip().lower()
        return ""
    except Exception:
        return ""


def find_anchor_final(parsed_data, locator):
    try:
        if not isinstance(locator, dict): return None, None, False
        loc_type = locator.get("type")
        expected_sheet = locator.get("sheet_name")
        enforce_sheet = locator.get("enforce_sheet_name", False)

        if loc_type == "global": return parsed_data, None, False

        sheets = [s for s in parsed_data.get("children", []) if isinstance(s, dict) and s.get("type") == "worksheet"]

        # --- LOGIC MỚI: TÌM VÙNG DỮ LIỆU BẰNG TẬP HỢP TỪ KHÓA ---
        if loc_type in ["header_signature", "data_region"]:
            req_headers = [str(h).strip().lower() for h in locator.get("required_headers", [])]
            if not req_headers: return None, None, False

            for sheet in sheets:
                sheet_name_actual = str(sheet.get("properties", {}).get("name", "")).lower()
                if expected_sheet and enforce_sheet and expected_sheet.lower() not in sheet_name_actual:
                    continue
                
                rows = [r for r in sheet.get("children", []) if isinstance(r, dict) and r.get("type") == "row"]
                for row in rows:
                    row_text = extract_all_text(row).lower()
                    # Kiểm tra xem dòng này có chứa TẤT CẢ các headers yêu cầu không
                    if all(h in row_text for h in req_headers):
                        is_wrong_sheet = bool(expected_sheet and expected_sheet.lower() not in sheet_name_actual)
                        return row, sheet, is_wrong_sheet
            return None, None, False

        # --- LOGIC CŨ ---
        text_contain = str(locator.get("text_contains", "")).lower()
        if expected_sheet:
            for sheet in sheets:
                if expected_sheet.lower() in str(sheet.get("properties", {}).get("name", "")).lower():
                    if loc_type == "worksheet" and (not text_contain or text_contain in extract_all_text(sheet).lower()):
                        return sheet, parsed_data, False
                    if loc_type == "row":
                        for row in sheet.get("children", []):
                            if isinstance(row, dict) and row.get("type") == "row" and text_contain in extract_all_text(row).lower():
                                return row, sheet, False

        for sheet in sheets:
            if loc_type == "worksheet" and (not text_contain or text_contain in extract_all_text(sheet).lower()):
                return sheet, parsed_data, True if (expected_sheet and enforce_sheet) else False
            if loc_type == "row":
                for row in sheet.get("children", []):
                    if isinstance(row, dict) and row.get("type") == "row" and text_contain in extract_all_text(row).lower():
                        return row, sheet, True if (expected_sheet and enforce_sheet) else False

        return None, None, False
    except Exception:
        return None, None, False


def check_vertical_column(parent_sheet, start_row_node, col_idx, expected_count, check_func):
    try:
        if not parent_sheet or not isinstance(parent_sheet, dict): return 1.0, ""
        sheet_name = parent_sheet.get("properties", {}).get("name", "Unknown")
        rows = [r for r in parent_sheet.get("children", []) if isinstance(r, dict) and r.get("type") == "row"]

        try:
            anchor_idx = rows.index(start_row_node)
            start_idx = anchor_idx + 1  
        except ValueError:
            return 1.0, ""

        if expected_count <= 0: expected_count = 1
        end_idx = min(start_idx + expected_count, len(rows))

        total_score = 0.0
        first_error_msg = ""

        for i in range(start_idx, end_idx):
            row = rows[i]
            cell_data = get_cell_data(row, col_idx)
            coord = cell_data.get("coord", f"dòng {i + 1}") if cell_data else f"dòng {i + 1}"

            if not cell_data or str(cell_data.get("value", "")).strip() == "":
                if not first_error_msg:
                    first_error_msg = f"Dữ liệu ngắt quãng tại {coord} (Sheet: {sheet_name})"
                continue

            cell_score, msg = check_func(cell_data)
            total_score += cell_score

            if cell_score < 1.0 and not first_error_msg:
                first_error_msg = f"{msg} tại ô {coord} (Sheet: {sheet_name})"

        final_ratio = total_score / expected_count
        if final_ratio == 1.0:
            return 1.0, f"Hợp lệ nguyên cột ({expected_count} ô)"
        return final_ratio, f"Đạt {round(final_ratio * 100, 1)}%. {first_error_msg}"

    except Exception as e:
        return 0.0, f"Lỗi quét dọc: {str(e)}"


def evaluate_action_deep(target_node, parent_sheet, rule, parsed_data):
    action = rule.get("action")
    if not isinstance(target_node, dict): return 0.0, "Dữ liệu mỏ neo bị lỗi"

    try:
        # =====================================================================
        # LOGIC HYBRID TỐI ƯU HÓA: CHẤM GẮT VÀ CHẤM LỎNG KẾT HỢP
        # =====================================================================
        if action == "VERIFY_COLUMN_HYBRID":
            col_idx = get_dynamic_col_index(rule, target_node)
            if col_idx < 0: return 0.0, f"Không tìm thấy cột: {rule.get('target_column')}"

            rows = [r for r in parent_sheet.get("children", []) if isinstance(r, dict) and r.get("type") == "row"]
            try:
                start_idx = rows.index(target_node) + 1
            except ValueError:
                return 0.0, "Không tìm thấy thân bảng dữ liệu"

            expected_total = int(rule.get("expected_total_rows", 10))
            strict_check = rule.get("strict_check", {})
            loose_check = rule.get("loose_check", {})

            check_limit = int(strict_check.get("check_limit", 4))
            expected_values = strict_check.get("expected_values", [])
            allowed_funcs = [str(f).strip().upper() for f in strict_check.get("allowed_functions", [])]
            require_dynamic = loose_check.get("require_dynamic_formula", True)

            passed_count = 0
            actual_checked = 0
            errors = []

            for i in range(expected_total):
                if start_idx + i >= len(rows):
                    errors.append(f"Bảng thiếu dòng ({actual_checked}/{expected_total})")
                    break

                current_row = rows[start_idx + i]
                cell_data = get_cell_data(current_row, col_idx)
                
                if not cell_data:
                    errors.append(f"Ô trống ở mục tin số {i+1}")
                    continue

                actual_checked += 1
                val = str(cell_data.get("value", "")).strip().lower()
                formula = str(cell_data.get("formula", "")).strip().upper()
                is_dynamic = cell_data.get("is_dynamic")

                if i < check_limit:
                    # --- STRICT MODE ---
                    expected_val = str(expected_values[i]).strip().lower() if i < len(expected_values) else ""
                    
                    # Fuzzy match cho Value
                    val_match = False
                    if expected_val:
                        val_match = (expected_val == val) or (expected_val in val) or (val in expected_val if val else False)
                    else:
                        val_match = True # Bỏ qua check value nếu mảng rubric cung cấp bị thiếu
                    
                    # Function match
                    func_match = True
                    if allowed_funcs:
                        func_match = any(f in formula for f in allowed_funcs)

                    if val_match and func_match:
                        passed_count += 1
                    else:
                        if not val_match and not func_match:
                            errors.append(f"Mục {i+1} sai kết quả ({val}) và sai hàm")
                        elif not val_match:
                            errors.append(f"Mục {i+1} sai KQ (Đáng lẽ: {expected_val}, Thực tế: {val})")
                        else:
                            errors.append(f"Mục {i+1} vi phạm yêu cầu hàm ({allowed_funcs})")
                else:
                    # --- LOOSE MODE ---
                    if require_dynamic:
                        if is_dynamic or formula != "":
                            passed_count += 1
                        else:
                            errors.append(f"Mục {i+1} gõ tay tĩnh, không dùng công thức")
                    else:
                        passed_count += 1 

            ratio = passed_count / expected_total if expected_total > 0 else 0.0
            if ratio >= 0.99:
                return 1.0, f"Hợp lệ toàn bộ {expected_total} ô (Hybrid Pass)"
            return ratio, f"Đạt {passed_count}/{expected_total}. Lỗi: {'; '.join(errors[:2])}"

        elif action == "VERIFY_VALUE":
            col_idx = get_dynamic_col_index(rule, target_node)
            if col_idx < 0: return 0.0, f"Không tìm thấy cột: {rule.get('target_column')}"

            rows = [r for r in parent_sheet.get("children", []) if isinstance(r, dict) and r.get("type") == "row"]
            try:
                anchor_idx = rows.index(target_node)
                data_node = rows[anchor_idx + 1] if anchor_idx + 1 < len(rows) else target_node
            except (ValueError, IndexError):
                data_node = target_node

            cell_data = get_cell_data(data_node, col_idx)
            if not cell_data: return 0.0, f"Không tìm thấy dữ liệu cột"

            actual_val = str(cell_data["value"]).strip().lower()
            expected_val = str(rule.get("expected", "")).strip().lower()
            if expected_val in actual_val or actual_val in expected_val:
                return 1.0, cell_data["value"]
            return 0.0, f"Sai KQ: {cell_data['value']} (Tại ô {cell_data['coord']})"

        elif action == "VERIFY_DYNAMIC_FORMULA":
            col_idx = get_dynamic_col_index(rule, target_node)
            if col_idx < 0: return 0.0, f"Không tìm thấy cột chỉ định"

            exp_count = int(rule.get("expected_count", 1))

            def eval_dynamic(c):
                if c.get("is_dynamic") is True:
                    return 1.0, ""
                return 0.0, "Không dùng công thức động"

            return check_vertical_column(parent_sheet, target_node, col_idx, exp_count, eval_dynamic)

        elif action == "VERIFY_FUNCTION_NAME":
            col_idx = get_dynamic_col_index(rule, target_node)
            if col_idx < 0: return 0.0, f"Không tìm thấy cột chỉ định"

            exp_count = int(rule.get("expected_count", 1))
            
            allowed_funcs = [str(f).strip().upper() for f in rule.get("allowed_functions", [])]
            if not allowed_funcs and rule.get("expected_function"):
                allowed_funcs = [str(rule.get("expected_function")).strip().upper()]

            expected_ref = str(rule.get("expected_reference", "")).strip().upper().replace(" ", "")

            def eval_func(c):
                formula = str(c.get("formula", "")).replace(" ", "").upper()
                
                matched_func = None
                for func in allowed_funcs:
                    if func in formula:
                        matched_func = func
                        break
                
                if not matched_func:
                    return 0.0, f"Sai hàm (Phải dùng {allowed_funcs})"

                if expected_ref and expected_ref not in formula:
                    return 0.5, f"Dùng đúng {matched_func} nhưng sai vùng tham chiếu"

                return 1.0, ""

            ratio, msg = check_vertical_column(parent_sheet, target_node, col_idx, exp_count, eval_func)
            if ratio == 1.0:
                cell_data = get_cell_data(target_node, col_idx)
                return 1.0, f"Hợp lệ: {cell_data.get('formula', '')}"
            return ratio, msg

        elif action == "VERIFY_CONDITIONAL_FORMATTING":
            expected_val = str(rule.get("expected_value", "")).strip()
            sheet_node = parent_sheet if target_node.get("type") == "row" else target_node
            cfs = sheet_node.get("section", {}).get("conditionalFormatting", [])
            for cf in cfs:
                cf_str = json.dumps(cf, ensure_ascii=False)
                if expected_val in cf_str: return 1.0, "Tìm thấy Rule CF"
            return 0.0, "Không tìm thấy Rule CF phù hợp"

        elif action == "VERIFY_FILTER_EXISTS":
            has_filter = "autoFilter" in target_node.get("section", {})
            return 1.0 if has_filter else 0.0, f"AutoFilter: {has_filter}"

        elif action == "VERIFY_EXTRACTED_DATA":
            expected_val = str(rule.get("expected_value", "")).strip().lower()
            forbidden_vals = [str(x).strip().lower() for x in rule.get("forbidden_values", [])]
            if not expected_val or not forbidden_vals:
                return 0.0, "Thiếu tham số expected_value hoặc forbidden_values"

            for sheet in parsed_data.get("children", []):
                if not isinstance(sheet, dict) or sheet.get("type") != "worksheet": continue

                sheet_text = extract_all_text(sheet).lower()
                if expected_val in sheet_text:
                    is_pure = True
                    for fv in forbidden_vals:
                        if fv and fv in sheet_text:
                            is_pure = False
                            break
                    if is_pure:
                        sheet_name = sheet.get("properties", {}).get("name", "Unknown")
                        return 1.0, f"Đã trích lọc chuẩn xác ra Sheet: {sheet_name}"
            return 0.0, f"Không có sheet chứa trích lọc '{expected_val}'"

        elif action == "VERIFY_PIVOT_TABLE":
            field_type = str(rule.get("field_type", "data")).strip().lower()
            expected_subtotal = str(rule.get("expected_subtotal", "sum")).strip().lower()
            
            source_col_header = rule.get("source_col_header")
            if source_col_header:
                dynamic_idx = get_dynamic_col_index({"col_header": source_col_header}, target_node)
                if dynamic_idx < 0:
                    return 0.0, f"Bảng gốc bị thiếu cột '{source_col_header}'"
                expected_fld = str(dynamic_idx)
            else:
                expected_fld = str(rule.get("expected_fld", "")).strip()

            best_ratio = 0.0
            best_msg = "Không có cấu trúc PivotTable"
            found_any = False

            for child in parsed_data.get("children", []):
                if not isinstance(child, dict) or child.get("type") != "pivotTable": continue
                found_any = True
                curr_ratio = 0.5
                curr_msg = "Có Pivot Table"

                if field_type == "row":
                    row_fields = child.get("properties", {}).get("row_fields_index", [])
                    if expected_fld in [str(x) for x in row_fields]:
                        return 1.0, f"Kéo đúng trường {expected_fld} vào vùng Row" 
                    curr_msg += " (Thiếu trường Row yêu cầu)"

                elif field_type == "col":
                    col_fields = child.get("properties", {}).get("col_fields_index", [])
                    if expected_fld in [str(x) for x in col_fields]:
                        return 1.0, f"Kéo đúng trường {expected_fld} vào vùng Column"
                    curr_msg += " (Thiếu trường Column yêu cầu)"

                else:  # DATA
                    data_fields = child.get("properties", {}).get("data_fields", [])
                    matched_field = False
                    for df in data_fields:
                        if not isinstance(df, dict): continue
                        act_fld = str(df.get("fld", "")).strip()
                        act_sub = str(df.get("subtotal", "")).strip().lower()

                        if act_fld == expected_fld and act_sub == expected_subtotal:
                            return 1.0, f"Kéo đúng cột {act_fld} và dùng hàm {act_sub}"
                        elif act_fld == expected_fld:
                            curr_ratio = 0.8
                            curr_msg = f"Đúng cột nhưng sai hàm ({act_sub})"
                            matched_field = True

                    if not matched_field:
                        curr_msg += " (Thiếu trường Data yêu cầu)"

                if curr_ratio > best_ratio:
                    best_ratio = curr_ratio
                    best_msg = curr_msg

            if not found_any: return 0.0, "Không có cấu trúc PivotTable"
            return best_ratio, best_msg

        elif action == "VERIFY_OBJECT_EXISTS":
            expected_obj = str(rule.get("expected_object", "")).strip().lower()
            
            for sheet in parsed_data.get("children", []):
                if not isinstance(sheet, dict) or sheet.get("type") != "worksheet": continue
                unknowns = [str(u).lower() for u in sheet.get("unknown", [])]
                if expected_obj in unknowns:
                    return 1.0, f"Tìm thấy đối tượng {expected_obj} trong Sheet"
            
            for child in parsed_data.get("children", []):
                if isinstance(child, dict) and child.get("type") == expected_obj:
                    return 1.0, f"Tìm thấy đối tượng {expected_obj}"
                    
            return 0.0, f"Không tìm thấy {expected_obj}"

        elif action == "VERIFY_CHART_TYPE":
            expected_type = str(rule.get("expected_type", "")).strip().lower()
            for child in parsed_data.get("children", []):
                if isinstance(child, dict) and child.get("type") == "chart":
                    chart_types = [str(t).lower() for t in child.get("properties", {}).get("chart_types", [])]
                    if expected_type in chart_types:
                        return 1.0, f"Đúng loại biểu đồ {expected_type}"
                    elif expected_type.replace("chart", "") in "".join(chart_types):
                        return 0.5, f"Sai định dạng (dùng biến thể của {expected_type})"
            return 0.0, "Không tìm thấy biểu đồ khớp yêu cầu định dạng"

        elif action == "VERIFY_CHART_SERIES_KEYWORDS":
            expected_series_keywords = [s.strip().lower() for s in rule.get("expected_series_keywords", [])]
            if not expected_series_keywords: return 0.0, "Thiếu tham số expected_series_keywords"
            
            best_ratio = 0.0
            best_msg = "Không tìm thấy dữ liệu khớp"

            for child in parsed_data.get("children", []):
                if isinstance(child, dict) and child.get("type") == "chart":
                    series_nodes = [s for s in child.get("children", []) if s.get("type") == "chart_series"]
                    
                    actual_series_names = []
                    for s_node in series_nodes:
                        ref_str = s_node.get("properties", {}).get("name_ref", "")
                        actual_text = resolve_ref_to_text(parsed_data, ref_str)
                        if actual_text: actual_series_names.append(actual_text)

                    match_count = 0
                    for expected_kw in expected_series_keywords:
                        for actual_name in actual_series_names:
                            if expected_kw in actual_name:
                                match_count += 1
                                break

                    ratio = match_count / len(expected_series_keywords) if expected_series_keywords else 0.0
                    msg = f"Nguồn DL chuẩn ({match_count}/{len(expected_series_keywords)})" if ratio == 1.0 else f"Nguồn sai, đang vẽ: {', '.join(actual_series_names) if actual_series_names else 'Không rõ'}"
                    
                    if ratio == 1.0: return 1.0, msg
                    if ratio > best_ratio:
                        best_ratio = ratio
                        best_msg = msg

            return best_ratio, best_msg

        return 0.0, f"Action '{action}' không hỗ trợ"
    except Exception as e:
        return 0.0, f"Lỗi Python (Action {action}): {str(e)}"


def grade_submission(rubric, parsed_data):
    total_score = 0.0
    grading_report = []

    workbook_properties = {}
    if isinstance(parsed_data, dict):
        workbook_properties = parsed_data.get("properties", {})

    if not isinstance(rubric, list):
        return {
            "final_score": 0,
            "properties": workbook_properties,
            "report": [{"criteria": "Lỗi", "status": "FAILED", "message": "Rubric lỗi."}]
        }

    for criteria in rubric:
        if not isinstance(criteria, dict): continue
        criteria_name = criteria.get("criteria_name", "Unknown Criteria")

        # --- HỖ TRỢ CẢ RUBRIC MỚI (region_definition) VÀ CŨ (anchor_locator) ---
        locator = criteria.get("anchor_locator")
        if not locator and "region_definition" in criteria:
            locator = criteria["region_definition"].get("locator")

        target_node, parent_sheet, is_wrong_sheet = find_anchor_final(parsed_data, locator if locator else {})

        if not target_node:
            grading_report.append({
                "criteria": criteria_name,
                "status": "FAILED",
                "score": 0.0,
                "max_score": criteria.get("allocated_points", 0),
                "message": "Không tìm thấy vùng dữ liệu Mỏ neo dựa trên Tiêu đề yêu cầu."
            })
            continue

        criteria_score = 0.0
        rule_details = []

        for rule in criteria.get("rules", []):
            if not isinstance(rule, dict): continue
            max_rule_pts = float(rule.get("points", 0))
            ratio, actual_msg = evaluate_action_deep(target_node, parent_sheet, rule, parsed_data)
            earned_pts = max_rule_pts * ratio

            if ratio == 1.0:
                rule_details.append(
                    {"desc": rule.get("description", ""), "passed": True, "score": earned_pts, "actual": actual_msg})
            elif ratio > 0.0:
                rule_details.append({"desc": rule.get("description", ""), "passed": "PARTIAL", "score": earned_pts,
                                     "actual": actual_msg})
            else:
                rule_details.append(
                    {"desc": rule.get("description", ""), "passed": False, "score": 0.0, "actual": actual_msg})
            criteria_score += earned_pts

        penalty_msg = ""
        if is_wrong_sheet and criteria_score > 0:
            penalty = criteria_score * 0.2
            criteria_score -= penalty
            penalty_msg = " (Bị phạt -20% do để sai Sheet quy định)"

        criteria_score = round(criteria_score, 2)
        total_score += criteria_score
        max_alloc = float(criteria.get("allocated_points", 0))
        status = "SUCCESS" if criteria_score >= max_alloc and max_alloc > 0 else (
            "PARTIAL" if criteria_score > 0 else "FAILED")

        grading_report.append({
            "criteria": criteria_name,
            "status": status,
            "score": criteria_score,
            "max_score": max_alloc,
            "message": penalty_msg.strip(),
            "details": rule_details
        })

    return {
        "final_score": round(total_score, 2),
        "properties": workbook_properties,
        "report": grading_report
    }


def write_result_to_file(result, output_path):
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    student_json_data = parse_xlsx("Excel/Files/example.xlsx")
    with open("Excel/Rubrics/rubric1.json", "r", encoding="utf-8") as f:
        rubric = json.load(f)

    result = grade_submission(rubric, student_json_data)
    write_result_to_file(result, "Excel/Results/result_example.json")
    print(f"Hoàn tất chấm điểm. Tổng điểm: {result['final_score']}")
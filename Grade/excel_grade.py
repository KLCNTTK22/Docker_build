import json

from Parser.excel_parser.core import parse_xlsx


def extract_all_text(node):
    if not isinstance(node, dict): return ""
    text = str(node.get("text", "")) if node.get("text") else ""
    for child in node.get("children", []):
        text += extract_all_text(child)
    return text


def parse_col_index(rule):
    """
    HÀM MỚI: Tự động phiên dịch cột chữ (A, B, C) sang số (0, 1, 2)
    Đảm bảo Python không bao giờ bị crash nếu LLM trả về chữ cái.
    """
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
            if child.get("tag") == "v": value = child.get("text", "")
            if child.get("tag") == "f": formula = child.get("text", "")

        return {"is_dynamic": is_dynamic, "value": value, "formula": formula, "coord": r_coord}
    except Exception:
        return None


def find_anchor_final(parsed_data, locator):
    try:
        if not isinstance(locator, dict): return None, None, False
        loc_type = locator.get("type")
        text_contain = str(locator.get("text_contains", "")).lower()
        expected_sheet = locator.get("sheet_name")
        enforce_sheet = locator.get("enforce_sheet_name", False)

        if loc_type == "global": return parsed_data, None, False

        sheets = [s for s in parsed_data.get("children", []) if isinstance(s, dict) and s.get("type") == "worksheet"]

        if expected_sheet:
            for sheet in sheets:
                if expected_sheet.lower() in str(sheet.get("properties", {}).get("name", "")).lower():
                    if loc_type == "worksheet" and (
                            not text_contain or text_contain in extract_all_text(sheet).lower()):
                        return sheet, parsed_data, False
                    if loc_type == "row":
                        for row in sheet.get("children", []):
                            if isinstance(row, dict) and row.get("type") == "row" and text_contain in extract_all_text(
                                    row).lower():
                                return row, sheet, False

        for sheet in sheets:
            if loc_type == "worksheet" and (not text_contain or text_contain in extract_all_text(sheet).lower()):
                return sheet, parsed_data, True if (expected_sheet and enforce_sheet) else False
            if loc_type == "row":
                for row in sheet.get("children", []):
                    if isinstance(row, dict) and row.get("type") == "row" and text_contain in extract_all_text(
                            row).lower():
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
            start_idx = anchor_idx + 1  # Bỏ qua dòng Header
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

            # check_func giờ đây trả về 2 giá trị: (điểm_của_ô, lời_nhắn_lỗi)
            cell_score, msg = check_func(cell_data)
            total_score += cell_score

            # Lưu lại lời nhắn lỗi của ô đầu tiên bị sai/thiếu điểm để đưa vào Report
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
        if action == "VERIFY_VALUE":
            col_idx = parse_col_index(rule)

            rows = [r for r in parent_sheet.get("children", []) if isinstance(r, dict) and r.get("type") == "row"]
            try:
                anchor_idx = rows.index(target_node)
                data_node = rows[anchor_idx + 1] if anchor_idx + 1 < len(rows) else target_node
            except (ValueError, IndexError):
                data_node = target_node

            cell_data = get_cell_data(data_node, col_idx)
            if not cell_data: return 0.0, f"Không tìm thấy cột (Index: {col_idx})"

            actual_val = str(cell_data["value"]).strip().lower()
            expected_val = str(rule.get("expected", "")).strip().lower()
            if expected_val in actual_val or actual_val in expected_val:
                return 1.0, cell_data["value"]
            return 0.0, f"Sai KQ: {cell_data['value']} (Tại ô {cell_data['coord']})"

        elif action == "VERIFY_DYNAMIC_FORMULA":

            col_idx = parse_col_index(rule)

            exp_count = int(rule.get("expected_count", 1))

            def eval_dynamic(c):

                if c.get("is_dynamic") is True:
                    return 1.0, ""

                return 0.0, "Không dùng công thức động"

            ratio, msg = check_vertical_column(parent_sheet, target_node, col_idx, exp_count, eval_dynamic)

            return ratio, msg

        elif action == "VERIFY_FUNCTION_NAME":

            col_idx = parse_col_index(rule)

            exp_count = int(rule.get("expected_count", 1))

            expected_func = str(rule.get("expected_function", "")).strip().upper()

            # Bổ sung logic lấy mảng tham chiếu từ JSON (nếu có)

            expected_ref = str(rule.get("expected_reference", "")).strip().upper().replace(" ", "")

            def eval_func(c):

                formula = str(c.get("formula", "")).replace(" ", "").upper()

                if expected_func not in formula:
                    return 0.0, f"Sai hàm (Không có {expected_func})"

                # Hàm đúng, nhưng kiểm tra thêm mảng tham chiếu nếu Rubric có yêu cầu

                if expected_ref and expected_ref not in formula:
                    return 0.5, f"Dùng đúng {expected_func} nhưng sai vùng tham chiếu"

                return 1.0, ""  # Điểm tuyệt đối cho ô này

            ratio, msg = check_vertical_column(parent_sheet, target_node, col_idx, exp_count, eval_func)

            if ratio == 1.0:
                cell_data = get_cell_data(target_node, col_idx)

                return 1.0, f"Hợp lệ: {expected_func} ({cell_data.get('formula', '')})"

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
            return 0.0, f"Không có sheet riêng nào chứa trích lọc '{expected_val}'"


        elif action == "VERIFY_PIVOT_TABLE":

            field_type = str(rule.get("field_type", "data")).strip().lower()

            expected_fld = str(rule.get("expected_fld", "")).strip()

            expected_subtotal = str(rule.get("expected_subtotal", "sum")).strip().lower()

            best_ratio = 0.0

            best_msg = "Không có cấu trúc PivotTable"

            found_any = False

            # QUÉT TẤT CẢ PIVOT TABLE TÌM ĐIỂM CAO NHẤT

            for child in parsed_data.get("children", []):

                if not isinstance(child, dict) or child.get("type") != "pivotTable": continue

                found_any = True

                curr_ratio = 0.5

                curr_msg = "Có Pivot Table"

                if field_type == "row":

                    row_fields = child.get("properties", {}).get("row_fields_index", [])

                    if expected_fld in [str(x) for x in row_fields]:
                        return 1.0, f"Kéo đúng trường {expected_fld} vào vùng Row"  # Hoàn hảo 100%, thoát luôn!

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

                # Ghi nhớ lại thành tích tốt nhất nếu chưa đạt 1.0

                if curr_ratio > best_ratio:
                    best_ratio = curr_ratio

                    best_msg = curr_msg

            if not found_any: return 0.0, "Không có cấu trúc PivotTable"

            return best_ratio, best_msg


        elif action == "VERIFY_CHART":

            expected_type = str(rule.get("expected_type", "")).strip().lower()

            expected_ref = str(rule.get("expected_data_ref_contains", "")).strip().replace(" ", "").lower()

            best_ratio = 0.0

            best_msg = "Không tìm thấy biểu đồ"

            found_any = False

            for child in parsed_data.get("children", []):

                if not isinstance(child, dict) or child.get("type") != "chart": continue

                found_any = True

                curr_ratio = 0.4

                msg_parts = ["Có vẽ biểu đồ"]

                chart_types = [str(t).lower() for t in child.get("properties", {}).get("chart_types", [])]

                chart_types_str = "".join(chart_types)

                # CHẤM 1: KIỂM TRA LOẠI BIỂU ĐỒ

                if expected_type in chart_types:

                    curr_ratio += 0.3

                    msg_parts.append(f"(Đúng loại {expected_type})")

                elif expected_type.replace("chart", "") in chart_types_str:

                    curr_ratio += 0.15

                    msg_parts.append(f"(Sai định dạng 3D/biến thể của {expected_type})")

                else:

                    msg_parts.append(f"(Sai loại: {chart_types_str})")

                # CHẤM 2: KIỂM TRA NGUỒN DỮ LIỆU

                if expected_ref:

                    series_data = child.get("children", [])

                    series_str = json.dumps(series_data, ensure_ascii=False).replace(" ", "").lower()

                    if expected_ref in series_str:

                        curr_ratio += 0.3

                        msg_parts.append("(Nguồn DL chuẩn)")

                    else:

                        # --- LOGIC MỚI: RÚT TRÍCH NGUỒN THỰC TẾ ĐỂ BÁO LỖI ---

                        actual_refs = []

                        for ser in series_data:

                            if isinstance(ser, dict) and ser.get("type") == "chart_series":

                                val_ref = ser.get("properties", {}).get("value_ref", "")

                                if val_ref: actual_refs.append(val_ref)

                        actual_ref_str = ", ".join(actual_refs) if actual_refs else "Không rõ vùng dữ liệu"

                        msg_parts.append(f"(Nguồn sai, đang trỏ về: {actual_ref_str})")

                else:

                    curr_ratio += 0.3  # Bù điểm nếu rubric không yêu cầu check nguồn

                curr_msg = " ".join(msg_parts)

                if curr_ratio >= 0.99:  # Thay cho == 1.0 để tránh lỗi dấu phẩy động

                    return 1.0, curr_msg

                if curr_ratio > best_ratio:
                    best_ratio = curr_ratio

                    best_msg = curr_msg

            if not found_any: return 0.0, "Không tìm thấy biểu đồ"

            return best_ratio, best_msg

        elif action == "VERIFY_OBJECT_EXISTS":
            expected_obj = str(rule.get("expected_object", "")).strip().lower()
            for sheet in parsed_data.get("children", []):
                if not isinstance(sheet, dict) or sheet.get("type") != "worksheet": continue
                unknowns = [str(u).lower() for u in sheet.get("unknown", [])]
                if expected_obj in unknowns:
                    return 1.0, f"Tìm thấy đối tượng {expected_obj} trong Sheet"
            return 0.0, f"Không tìm thấy {expected_obj}"

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

        target_node, parent_sheet, is_wrong_sheet = find_anchor_final(parsed_data, criteria.get("anchor_locator", {}))

        if not target_node:
            grading_report.append({
                "criteria": criteria_name,
                "status": "FAILED",
                "score": 0.0,
                "max_score": criteria.get("allocated_points", 0),
                "message": "Không tìm thấy vùng dữ liệu Mỏ neo."
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

    # Trả về kết quả có kẹp thêm properties
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

    # Giả lập load file Rubric
    with open("Excel/Rubrics/rubric1.json", "r", encoding="utf-8") as f:
        rubric = json.load(f)

    result = grade_submission(rubric, student_json_data)
    write_result_to_file(result, "Excel/Results/result_example.json")
    print(f"Hoàn tất chấm điểm. Tổng điểm: {result['final_score']}")
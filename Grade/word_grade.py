import json
from Parser.docx_parser.core import parse_docx

def extract_all_text(node):
    """Đệ quy để gom toàn bộ chuỗi text bên trong một node và các node con."""
    if not isinstance(node, dict):
        return ""

    text = str(node.get("text", "")) if node.get("text") else ""
    for child in node.get("children", []):
        text += extract_all_text(child)
    return text


def get_nested_value(obj, path):
    """Trích xuất giá trị từ JSON bằng đường dẫn dot notation (VD: 'layout.margin.top')."""
    if not path:
        return obj

    keys = path.split('.')
    val = obj
    try:
        for key in keys:
            if isinstance(val, list):
                val = val[int(key)]  # Xử lý index mảng (VD: children.0)
            elif isinstance(val, dict):
                val = val[key]  # Xử lý key object
            else:
                return None
        return val
    except (KeyError, TypeError, IndexError, ValueError):
        return None


def find_anchor(parsed_data, locator):
    """
    Tìm node mỏ neo. Trả về (vị_trí_index, danh_sách_chứa_node).
    Nếu là w:document, trả về ('ROOT', obj_gốc).
    """
    # Xử lý ngoại lệ cho node gốc (Document)
    if locator.get("tag") == "w:document":
        return "ROOT", parsed_data

    document_children = parsed_data.get("children", [])
    for index, node in enumerate(document_children):
        if not isinstance(node, dict):
            continue

        match = True
        if "tag" in locator and node.get("tag") != locator["tag"]:
            match = False
        if "type" in locator and node.get("type") != locator["type"]:
            match = False
        if "text_contains" in locator:
            full_text = extract_all_text(node)
            if locator["text_contains"] not in full_text:
                match = False

        if match:
            return index, document_children

    return -1, None


def evaluate_rule(actual_value, rule):
    """Đánh giá 1 luật dựa trên match_flag."""
    flag = rule["match_flag"]

    if flag == "STRICT":
        if str(actual_value).lower() == str(rule.get("expected_value", "")).lower():
            return True

    elif flag == "TOLERANT":
        if "accepted_range" in rule:
            try:
                val = float(actual_value)
                min_val, max_val = rule["accepted_range"]
                if min_val <= val <= max_val:
                    return True
            except (ValueError, TypeError):
                pass
        elif "accepted_values" in rule:
            if str(actual_value) in [str(x) for x in rule["accepted_values"]]:
                return True

    elif flag == "PRESENCE_ONLY":
        expected = rule.get("expected_value")
        if expected is not None and expected != "":
            return deep_search_value(actual_value, expected)
        else:
            return actual_value is not None and actual_value != ""

    return False


def deep_search_value(node, expected_val):
    """Tìm kiếm xem một giá trị (chữ thường, tìm chuỗi con) có tồn tại BẤT CỨ ĐÂU trong node này không"""
    if expected_val is None:
        return False

    # Chuẩn hóa giá trị tìm kiếm: đưa về chữ thường và cắt khoảng trắng 2 đầu
    expected_str = str(expected_val).strip().lower()

    if isinstance(node, dict):
        for k, v in node.items():
            if isinstance(v, str):
                # Dùng toán tử `in` để tìm chuỗi con thay vì `==`
                if expected_str in v.lower():
                    return True
            elif isinstance(v, (int, float, bool)):
                if expected_str == str(v).lower():
                    return True

            # Đệ quy đi sâu vào trong
            if deep_search_value(v, expected_val):
                return True
    elif isinstance(node, list):
        for item in node:
            if deep_search_value(item, expected_val):
                return True
    else:
        # Nếu là các giá trị nguyên thủy ở tầng cuối cùng
        if isinstance(node, str):
            if expected_str in node.lower():
                return True
        else:
            if str(node).lower() == expected_str:
                return True

    return False


def write_result_to_file(result, output_path):
    """Ghi kết quả chấm điểm ra file JSON."""
    output_data = {
        "properties": result.get("properties", {}),
        "final_score": result["final_score"],
        "report": result["report"]
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)


def grade_submission(rubric, parsed_data):
    """Hệ thống chấm điểm chính (Rule Engine)."""
    total_score = 0.0
    grading_report = []

    for criteria in rubric:
        criteria_name = criteria["criteria_name"]
        idx, parent_array = find_anchor(parsed_data, criteria["anchor_locator"])

        if idx == -1:
            grading_report.append({
                "criteria": criteria_name,
                "status": "FAILED_ANCHOR",
                "score": 0.0,
                "max_score": criteria["allocated_points"],
                "message": "Không tìm thấy đoạn văn/đối tượng được yêu cầu."
            })
            continue

        criteria_score = 0.0
        rule_details = []

        for rule in criteria["rules"]:
            offset = rule.get("relative_offset", 0)

            # Xác định Target Node
            if idx == "ROOT":
                target_node = parent_array  # Lấy luôn node gốc
            else:
                target_idx = idx + offset
                if target_idx < 0 or target_idx >= len(parent_array):
                    rule_details.append(
                        {"desc": rule["description"], "passed": False, "reason": "Lệch offset ra ngoài phạm vi bài."})
                    continue
                target_node = parent_array[target_idx]

            # Lấy giá trị và chấm
            actual_value = get_nested_value(target_node, rule["property_path"])
            passed = evaluate_rule(actual_value, rule)

            if passed:
                criteria_score += rule["points"]
                rule_details.append({"desc": rule["description"], "passed": True, "actual": actual_value})
            else:
                rule_details.append(
                    {"desc": rule["description"], "passed": False, "expected": rule.get("expected_value"),
                     "actual": actual_value})

        total_score += criteria_score
        grading_report.append({
            "criteria": criteria_name,
            "status": "SUCCESS" if criteria_score == criteria["allocated_points"] else "PARTIAL/FAILED",
            "score": criteria_score,
            "max_score": criteria["allocated_points"],
            "details": rule_details
        })

    return {
        "properties": parsed_data.get("properties", {}),
        "final_score": total_score,
        "report": grading_report
    }


if __name__ == "__main__":
    student_json_data = parse_docx("Word/Files/example.docx")

    with open("Word/Rubrics/rubric2.json", "r", encoding="utf-8") as f:
        rubric = json.load(f)

    result = grade_submission(rubric, student_json_data)

    write_result_to_file(result, "Word/Results/result_examplev2.json")
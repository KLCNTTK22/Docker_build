import json
import difflib

# (Các hàm extract_all_text, get_nested_value, find_anchor, deep_search_value, evaluate_rule giữ nguyên 100% như cũ)

def extract_all_text(node):
    if not isinstance(node, dict): return ""
    text = str(node.get("text", "")) if node.get("text") else ""
    for child in node.get("children", []): text += extract_all_text(child)
    return text

def get_nested_value(obj, path):
    if not path: return obj
    keys = path.split('.')
    val = obj
    try:
        for key in keys:
            if isinstance(val, list):
                if key == 'length': return len(val) # Hỗ trợ lấy độ dài mảng
                val = val[int(key)]
            elif isinstance(val, dict):
                val = val[key]
            else:
                return None
        return val
    except (KeyError, TypeError, IndexError, ValueError):
        return None

def find_anchor(parsed_data, locator):
    if locator.get("tag") == "w:document": return "ROOT", parsed_data
    document_children = parsed_data.get("children", [])
    for index, node in enumerate(document_children):
        if not isinstance(node, dict): continue
        match = True
        if "tag" in locator and node.get("tag") != locator["tag"]: match = False
        if "type" in locator and node.get("type") != locator["type"]: match = False
        if "text_contains" in locator:
            if locator["text_contains"] not in extract_all_text(node): match = False
        if match: return index, document_children
    return -1, None

def deep_check_key_value(node, locator):
    if isinstance(node, dict):
        match = True
        if "tag" in locator and node.get("tag") != locator["tag"]: match = False
        if "pStyle" in locator and node.get("properties", {}).get("pStyle") != locator["pStyle"]: match = False
        if match: return node
        for k, v in node.items():
            res = deep_check_key_value(v, locator)
            if res: return res
    elif isinstance(node, list):
        for item in node:
            res = deep_check_key_value(item, locator)
            if res: return res
    return None

def evaluate_rule(actual_value, rule):
    flag = rule.get("match_flag")
    if not flag: return True # Nếu không có cờ, đây chỉ là Scope Rule, mặc định qua

    if flag == "STRICT":
        return str(actual_value).lower() == str(rule.get("expected_value", "")).lower()
    elif flag == "TOLERANT":
        if "accepted_range" in rule:
            try:
                val = float(actual_value)
                return rule["accepted_range"][0] <= val <= rule["accepted_range"][1]
            except: pass
        elif "accepted_values" in rule:
            return str(actual_value) in [str(x) for x in rule["accepted_values"]]
    elif flag == "PRESENCE_ONLY":
        expected = rule.get("expected_value")
        return deep_search_value(actual_value, expected) if expected else (actual_value is not None)
    elif flag == "FUZZY_TEXT":
        if actual_value is None: return False
        return difflib.SequenceMatcher(None, str(rule.get("expected_value", "")).lower(), str(actual_value).lower()).ratio() >= rule.get("required_ratio", 0.8)
    return False

def deep_search_value(node, expected_val):
    if expected_val is None: return False
    expected_str = str(expected_val).strip().lower()
    if isinstance(node, dict):
        for k, v in node.items():
            if isinstance(v, str) and expected_str in v.lower(): return True
            elif isinstance(v, (int, float, bool)) and expected_str == str(v).lower(): return True
            if deep_search_value(v, expected_val): return True
    elif isinstance(node, list):
        for item in node:
            if deep_search_value(item, expected_val): return True
    else:
        if isinstance(node, str) and expected_str in node.lower(): return True
        elif str(node).lower() == expected_str: return True
    return False

# ==========================================
# [MỚI] HÀM ĐỆ QUY XỬ LÝ NESTED RULES
# ==========================================
def process_rules(target_node, rules):
    """
    Xử lý danh sách rules đối với một target_node cụ thể.
    Trả về tổng điểm đạt được và chi tiết báo cáo.
    """
    score = 0.0
    details = []

    for rule in rules:
        # Nếu rule này là một Scope Rule (Dùng để thu hẹp phạm vi cho nested_rules)
        if "nested_rules" in rule:
            new_target = None
            
            # Khởi tạo Scope bằng scope_index (Ví dụ chọn hàng số 0, ô số 1)
            if "scope_index" in rule:
                children = target_node.get("children", [])
                if 0 <= rule["scope_index"] < len(children):
                    new_target = children[rule["scope_index"]]
            
            # Khởi tạo Scope bằng scope_locator (Tìm con theo thuộc tính)
            elif "scope_locator" in rule:
                if rule.get("search_mode") == "FORWARD":
                    new_target = deep_check_key_value(target_node, rule["scope_locator"])
                else:
                    new_target = get_nested_value(target_node, rule.get("scope_locator", ""))
            
            if new_target is None:
                details.append({"desc": rule["description"], "passed": False, "reason": "Không tìm thấy Scope yêu cầu."})
                continue
            
            # Gọi đệ quy để chấm các luật con bên trong Scope mới
            child_score, child_details = process_rules(new_target, rule["nested_rules"])
            score += child_score
            details.extend(child_details)
            continue
            
        # Nếu là Rule chấm điểm bình thường
        property_path = rule.get("property_path", "")
        if rule.get("match_flag") == "FUZZY_TEXT":
            actual_value = extract_all_text(target_node) # Gom toàn bộ chữ trong đoạn đó
        else:
            actual_value = get_nested_value(target_node, property_path)
            
        passed = evaluate_rule(actual_value, rule)
        # -------------------------

        if passed:
            score += rule.get("points", 0)
            details.append({"desc": rule.get("description", "Rule"), "passed": True, "actual": actual_value})
        else:
            details.append({"desc": rule.get("description", "Rule"), "passed": False, "expected": rule.get("expected_value"), "actual": actual_value})

    return score, details


def grade_submission(rubric, parsed_data):
    total_score = 0.0
    grading_report = []

    for criteria in rubric:
        criteria_name = criteria["criteria_name"]
        
        # 1. Tìm Mỏ Neo lớn nhất
        idx, parent_array = find_anchor(parsed_data, criteria["anchor_locator"])

        if idx == -1:
            grading_report.append({
                "criteria": criteria_name,
                "status": "FAILED_ANCHOR",
                "score": 0.0,
                "max_score": criteria.get("allocated_points", 0),
                "message": "Không tìm thấy mỏ neo chính của tiêu chí."
            })
            continue

        target_node = parent_array if idx == "ROOT" else parent_array[idx]

        # 2. Đẩy Target Node lớn vào hàm đệ quy để tự nó bóc tách Nested Rules
        criteria_score, rule_details = process_rules(target_node, criteria.get("rules", []))
        
        total_score += criteria_score
        grading_report.append({
            "criteria": criteria_name,
            "status": "SUCCESS" if criteria_score >= criteria.get("allocated_points", 0) else "PARTIAL/FAILED",
            "score": criteria_score,
            "max_score": criteria.get("allocated_points", 0),
            "details": rule_details
        })

    return {
        "properties": parsed_data.get("properties", {}),
        "final_score": total_score,
        "report": grading_report
    }


def write_result_to_file(result, output_path):
    """Ghi kết quả chấm điểm ra file JSON."""
    output_data = {
        "properties": result.get("properties", {}),
        "final_score": result["final_score"],
        "report": result["report"]
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

# (Phần code test giữ nguyên của bạn)
if __name__ == "__main__":
    from Parser.docx_parser.core import parse_docx
    student_json_data = parse_docx("Word/Files/example.docx")
    with open("Word/Rubrics/rubric2.json", "r", encoding="utf-8") as f:
        rubric = json.load(f)
    result = grade_submission(rubric, student_json_data)
    write_result_to_file(result, "Word/Results/result_examplev2.json")
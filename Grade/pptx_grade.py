import json
from Parser.pptx_parser.core import parse_pptx

def get_all_text_in_node(node):
    """Đệ quy lấy toàn bộ text bên trong một node để đối chiếu."""
    if not isinstance(node, dict): return ""
    text = ""
    if node.get("type") == "text_run":
        text += str(node.get("text", "")) + " "

    if "children" in node:
        for child in node["children"]:
            text += get_all_text_in_node(child)
    return text.strip()


def get_nested_value(node, path):
    """Lấy giá trị an toàn, hỗ trợ quét xuyên qua List (mảng) mà không bị None."""
    if not path: return node
    keys = path.split('.')
    current = node

    for i, key in enumerate(keys):
        if isinstance(current, list):
            sub_path = ".".join(keys[i:])
            results = []
            for item in current:
                val = get_nested_value(item, sub_path)
                if isinstance(val, list):
                    results.extend(val)
                elif val is not None:
                    results.append(val)
            return results if results else None

        if isinstance(current, dict):
            if key in current:
                current = current[key]
            elif "properties" in current and key in current["properties"]:
                current = current["properties"][key]
            elif "attributes" in current and key in current["attributes"]:
                current = current["attributes"][key]
            else:
                return None
        else:
            return None

    return current


def find_nodes(current_node, locator, parent_chain=None):
    """Đệ quy tìm TẤT CẢ các node thỏa mãn rule/locator, có theo dõi parent_chain."""
    if parent_chain is None:
        parent_chain = []

    matches = []
    is_match = True

    if "element_type" in locator and current_node.get("type") != locator["element_type"]:
        is_match = False

    if is_match and "must_contain_text" in locator:
        node_text = get_all_text_in_node(current_node)
        if locator["must_contain_text"].lower() not in node_text.lower():
            is_match = False

    if is_match and "parent_type" in locator:
        if locator["parent_type"] not in parent_chain:
            is_match = False

    props = current_node.get("properties", {})

    if is_match and "is_placeholder" in locator:
        if props.get("is_placeholder") != locator["is_placeholder"]:
            is_match = False

    if is_match and "placeholder_type" in locator:
        if props.get("placeholder", {}).get("type") != locator["placeholder_type"]:
            is_match = False

    if is_match and "is_action_button" in locator:
        if props.get("is_action_button") != locator["is_action_button"]:
            is_match = False

    if is_match:
        matches.append(current_node)

    if "children" in current_node:
        current_type = current_node.get("type")
        new_chain = parent_chain + [current_type] if current_type else parent_chain
        for child in current_node["children"]:
            matches.extend(find_nodes(child, locator, new_chain))

    return matches


# ==========================================
# ENGINE CHẤM ĐIỂM CHÍNH (GRADING ENGINE)
# ==========================================

def grade_submission(rubric_array, student_data):
    total_score = 0.0
    # Tính điểm tối đa từ tổng allocated_points của các nhóm
    max_possible_score = sum(group.get("allocated_points", 0.0) for group in rubric_array)
    grading_details = []

    # Cache lại các danh sách node cấp cao để tìm kiếm nhanh
    slides = [node for node in student_data.get("children", []) if node.get("type") == "slide"]
    slide_masters = [node for node in student_data.get("children", []) if node.get("type") == "slide_master"]

    # Duyệt qua từng Group criteria
    for group in rubric_array:
        group_name = group.get("criteria_name", "Unknown Criteria")
        anchor = group.get("anchor_locator", {})
        
        # 1. Xác định phạm vi tìm kiếm (Anchor Pool)
        anchor_pool = []
        anchor_type = anchor.get("type")
        
        if anchor_type == "global":
            anchor_pool = [student_data]
        elif anchor_type == "slide_master":
            anchor_pool = slide_masters
        elif anchor_type == "slide":
            text_contains = anchor.get("text_contains", "").lower()
            if text_contains:
                anchor_pool = [s for s in slides if text_contains in get_all_text_in_node(s).lower()]
            else:
                anchor_pool = slides
        else:
            anchor_pool = [student_data]

        # 2. Xử lý các Rule bên trong Group
        for rule in group.get("rules", []):
            rule_desc = rule.get("description", "")
            points = rule.get("points", 0.0)
            action = rule.get("action", "VERIFY_PROPERTY")
            
            awarded_points = 0.0
            status = "FAILED"
            message = ""
            best_partial_val = None

            # Tìm tất cả các node thỏa mãn điều kiện của rule bên trong anchor_pool
            target_pool = []
            for anchor_node in anchor_pool:
                target_pool.extend(find_nodes(anchor_node, rule))

            prop_path = rule.get("property_to_check", "")
            expected = str(rule.get("expected_value", ""))
            match_type = rule.get("match_type", "EXACT")

            # ----------------------------------------------------
            # ACTION 1: VERIFY_COUNT (Đếm số lượng Element/Property)
            # ----------------------------------------------------
            if action == "VERIFY_COUNT":
                expected_count = int(rule.get("expected_count", 0))
                actual_count = 0

                if not prop_path:
                    actual_count = len(target_pool)
                else:
                    for node in target_pool:
                        val = get_nested_value(node, prop_path)
                        if isinstance(val, list):
                            actual_count = max(actual_count, len(val))
                        elif val is not None:
                            actual_count = max(actual_count, 1)

                if actual_count >= expected_count:
                    awarded_points = points
                    status = "PASSED"
                    message = f"Đạt số lượng. Thực tế: {actual_count}/{expected_count}."
                elif actual_count >= expected_count / 2.0:
                    awarded_points = points * 0.5
                    status = "PARTIAL"
                    message = f"Đạt một phần số lượng (>= 50%). Thực tế: {actual_count}/{expected_count}."
                else:
                    awarded_points = 0.0
                    status = "FAILED"
                    message = f"Không đạt số lượng. Thực tế: {actual_count}/{expected_count}."

            # ----------------------------------------------------
            # ACTION 2 & 3: VERIFY_EXISTS / VERIFY_PROPERTY
            # ----------------------------------------------------
            else:
                if not target_pool:
                    message = "Không tìm thấy Element yêu cầu trong bài nộp."
                    status = "FAILED"
                else:
                    passed = False
                    for node in target_pool:
                        # Kiểm tra xem Element có tồn tại hay không
                        if action == "VERIFY_EXISTS" and not prop_path:
                            passed = True
                            break

                        actual_val = get_nested_value(node, prop_path)
                        actual_vals = actual_val if isinstance(actual_val, list) else [actual_val]

                        for val in actual_vals:
                            if val is None:
                                continue

                            if action == "VERIFY_EXISTS":
                                if expected.lower() == "true": passed = bool(val)
                                elif expected.lower() == "false": passed = not bool(val)
                                else: passed = True

                            elif action == "VERIFY_PROPERTY":
                                if match_type == "EXACT":
                                    passed = str(val).strip().lower() == expected.strip().lower()
                                elif match_type == "CONTAINS":
                                    passed = expected.lower() in str(val).lower()

                            if passed: break

                        if not passed and actual_vals:
                            best_partial_val = actual_vals[0]

                        if passed: break

                    if passed:
                        awarded_points = points
                        status = "PASSED"
                        message = "Hoàn thành tốt."
                    else:
                        if best_partial_val is not None:
                            message = f"Sai yêu cầu. Giá trị thực tế: '{best_partial_val}'. Kỳ vọng: '{expected}'"
                        else:
                            message = f"Sai yêu cầu. Không tìm thấy giá trị kỳ vọng: '{expected}'"

            # Cộng điểm và lưu chi tiết
            total_score += awarded_points
            grading_details.append({
                "group_name": group_name,
                "description": rule_desc,
                "max_points": points,
                "awarded_points": round(awarded_points, 2),
                "status": status,
                "message": message
            })

    return {
        "final_score": round(total_score, 2),
        "max_possible_score": round(max_possible_score, 2),
        "properties": student_data.get("properties", {}),
        "details": grading_details
    }


def write_result_to_file(result, output_path):
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    student_json_data = parse_pptx("PowerPoint/Files/example.pptx")
    with open("PowerPoint/Rubrics/rubric.json", "r", encoding="utf-8") as f:
        rubric_array = json.load(f)

    result = grade_submission(rubric_array, student_json_data)
    write_result_to_file(result, "PowerPoint/Results/result_example.json")
    print(f"🏆 Tổng điểm: {result['final_score']} / {result['max_possible_score']}")
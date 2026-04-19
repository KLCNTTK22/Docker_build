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
    """Đệ quy tìm TẤT CẢ các node thỏa mãn target_locator, có theo dõi parent_chain."""
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

    # Bỏ qua kiểm tra nếu locator không chỉ định parent_type (Linh hoạt vị trí)
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

def grade_submission(rubric, student_data):
    total_score = 0.0
    max_possible_score = rubric.get("rubric_metadata", {}).get("total_points", 10.0)
    grading_details = []

    slides = [node for node in student_data.get("children", []) if node.get("type") == "slide"]

    for criterion in rubric["criteria"]:
        crit_id = criterion["criterion_id"]
        points = criterion["points"]
        locator = criterion["target_locator"]
        eval_rule = criterion["evaluation"]

        awarded_points = 0.0
        status = "FAILED"
        message = ""
        best_partial_val = None

        target_pool = []
        if "slide_must_contain_text" in locator:
            target_slides = [s for s in slides if
                             locator["slide_must_contain_text"].lower() in get_all_text_in_node(s).lower()]
            for slide in target_slides:
                target_pool.extend(find_nodes(slide, locator))
        else:
            target_pool.extend(find_nodes(student_data, locator))

        prop_path = eval_rule.get("property_to_check", "")
        if prop_path and "property_path" in locator:
            prop_path = f"{locator['property_path']}.{prop_path}"
        expected = str(eval_rule.get("expected_value", ""))
        match_type = eval_rule.get("match_type", "EXACT")
        strictness = eval_rule.get("strictness", "HARD")

        # ----------------------------------------------------
        # 1. XỬ LÝ RIÊNG MATCH TYPE "COUNT" (Đếm có điều kiện % điểm)
        # ----------------------------------------------------
        if match_type == "COUNT":
            expected_count = int(expected) if expected.isdigit() else 0
            actual_count = 0

            if not prop_path:
                # Đếm trực tiếp số lượng object tìm thấy (VD: đếm số slide, số action_button)
                actual_count = len(target_pool)
            else:
                # Đếm số lượng item trong property của object (VD: số lượng series trong chart)
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

            total_score += awarded_points
            grading_details.append({
                "criterion_id": crit_id,
                "description": criterion["description"],
                "max_points": points,
                "awarded_points": round(awarded_points, 2),
                "status": status,
                "message": message
            })
            continue  # Chuyển sang criteria tiếp theo

        # ----------------------------------------------------
        # 2. XỬ LÝ CÁC MATCH TYPE KHÁC (EXACT, CONTAINS, EXISTS)
        # ----------------------------------------------------
        if not target_pool:
            message = "Không tìm thấy Element yêu cầu trong bài nộp."
            status = "FAILED"
        else:
            passed = False
            for node in target_pool:
                # Nếu chỉ muốn check Object có tồn tại không (VD: check chèn logo)
                if not prop_path and match_type == "EXISTS":
                    passed = True
                    break

                actual_val = get_nested_value(node, prop_path)
                actual_vals = actual_val if isinstance(actual_val, list) else [actual_val]

                for val in actual_vals:
                    if val is None:
                        continue

                    if match_type == "EXISTS":
                        if expected.lower() == "true":
                            passed = bool(val)
                        elif expected.lower() == "false":
                            passed = not bool(val)
                        else:
                            passed = True

                    elif match_type == "EXACT":
                        if strictness == "SOFT":
                            passed = str(val).strip().lower() == expected.strip().lower()
                        else:
                            passed = str(val) == expected

                    elif match_type == "CONTAINS":
                        passed = expected.lower() in str(val).lower()

                    if passed:
                        break

                if not passed and actual_vals:
                    best_partial_val = actual_vals[0]

                if passed:
                    break

            # Tính điểm cuối
            if passed:
                awarded_points = points
                status = "PASSED"
                message = f"Hoàn thành tốt. ({match_type})."
            else:
                if strictness == "SOFT" and best_partial_val is not None:
                    if expected.lower() in str(best_partial_val).lower():
                        awarded_points = points * 0.8
                        status = "PARTIAL"
                        message = f"Gần đúng (SOFT match). Giá trị thực tế: {best_partial_val}"
                    else:
                        message = f"Sai yêu cầu. Giá trị thực tế: {best_partial_val}. Kỳ vọng: {expected}"
                else:
                    message = f"Sai yêu cầu. Kỳ vọng: {expected}"

        total_score += awarded_points
        grading_details.append({
            "criterion_id": crit_id,
            "description": criterion["description"],
            "max_points": points,
            "awarded_points": round(awarded_points, 2),
            "status": status,
            "message": message
        })

    return {
        "final_score": round(total_score, 2),
        "max_possible_score": max_possible_score,
        "properties": student_data.get("properties", {}),
        "details": grading_details
    }


def write_result_to_file(result, output_path):
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    student_json_data = parse_pptx("PowerPoint/Files/example.pptx")
    with open("PowerPoint/Rubrics/rubric.json", "r", encoding="utf-8") as f:
        rubric = json.load(f)

    result = grade_submission(rubric, student_json_data)
    write_result_to_file(result, "PowerPoint/Results/result_example.json")
    print(f"🏆 Tổng điểm: {result['final_score']} / {result['max_possible_score']}")
import json
import re

# ==========================================
# CÁC HÀM TIỆN ÍCH TRÍCH XUẤT AST (KHÔNG HARDCODE)
# ==========================================
def normalize_anchor_text(text):
    """Xóa SẠCH khoảng trắng, tab, newline để mỏ neo (Anchor) bắt dính 100%."""
    if not text: return ""
    return re.sub(r'\s+', '', str(text)).lower()

def normalize_text(text):
    """Chuẩn hóa khoảng trắng đơn để đối khớp luật (Rule)."""
    if not text: return ""
    return re.sub(r'\s+', ' ', str(text)).strip().lower()

def get_all_text_in_node(node):
    """Đệ quy gom toàn bộ text bị phân mảnh bên trong một node."""
    if not isinstance(node, dict): return ""
    text = ""
    if node.get("type") == "text_run":
        text += str(node.get("text", "")) + " "
    if "children" in node:
        for child in node["children"]:
            text += get_all_text_in_node(child)
    return text.strip()

def extract_value_by_path(node, path_str):
    """
    Trích xuất giá trị theo đường dẫn tuyệt đối (dot-notation).
    Sử dụng Regex để không cắt nhầm dấu chấm (.) bên trong URL Namespace.
    """
    if not path_str or not isinstance(node, (dict, list)): return []
    
    # Ẩn URL Namespace để không bị split nhầm
    path_str = path_str.replace("{http://schemas.microsoft.com/office/powerpoint/2010/main}", "{PPTX_MAIN}")
    keys = re.split(r'\.(?![^{]*\})', path_str)
    keys = [k.replace("{PPTX_MAIN}", "{http://schemas.microsoft.com/office/powerpoint/2010/main}") for k in keys]
    
    def traverse(current, key_index):
        if key_index >= len(keys): 
            return [current] if current is not None else []
            
        key = keys[key_index]
        results = []
        
        if isinstance(current, list):
            if key.isdigit():
                # XỬ LÝ THÔNG MINH (WILDCARD ARRAY): Đệ quy quét trong toàn mảng
                for item in current:
                    results.extend(traverse(item, key_index + 1))
            else:
                for item in current:
                    results.extend(traverse(item, key_index))
                    
        elif isinstance(current, dict):
            if key in current: 
                results.extend(traverse(current[key], key_index + 1))
            # Quét linh hoạt các thẻ bọc phổ biến mà không hardcode
            elif "properties" in current and key in current["properties"]: 
                results.extend(traverse(current["properties"][key], key_index + 1))
            elif "attributes" in current and key in current["attributes"]: 
                results.extend(traverse(current["attributes"][key], key_index + 1))
            elif "style" in current and key in current["style"]: 
                results.extend(traverse(current["style"][key], key_index + 1))
                
        return results

    return traverse(node, 0)

def search_value_in_tree(node, path_str):
    """Đệ quy quét toàn bộ cấu trúc con để tìm một đường dẫn."""
    direct_vals = extract_value_by_path(node, path_str)
    if direct_vals: return direct_vals
    
    results = []
    if isinstance(node, dict):
        for k, v in node.items():
            if k in ["children", "properties", "style", "attributes"]:
                if isinstance(v, (dict, list)):
                    res = search_value_in_tree(v, path_str)
                    if res: results.extend(res)
    elif isinstance(node, list):
        for item in node:
            res = search_value_in_tree(item, path_str)
            if res: results.extend(res)
    return results

# ==========================================
# THUẬT TOÁN 1: TÌM KIẾM THEO MỎ NEO (ANCHOR LOCATOR)
# ==========================================
def find_nodes(current_node, locator):
    """Đệ quy tìm các node thỏa mãn định vị mỏ neo (Anchor)."""
    matches = []
    is_match = True
    
    if "type" in locator and current_node.get("type") != locator["type"]: is_match = False
    if is_match and "tag" in locator and current_node.get("tag") != locator["tag"]: is_match = False
        
    if is_match and "text_contains" in locator:
        node_text = normalize_anchor_text(get_all_text_in_node(current_node))
        search_text = normalize_anchor_text(locator["text_contains"])
        if search_text not in node_text: is_match = False
            
    if is_match and "properties" in locator:
        def match_dict(target, source):
            for k, v in target.items():
                s_v = source.get(k)
                if isinstance(v, dict):
                    if not isinstance(s_v, dict): return False
                    if not match_dict(v, s_v): return False
                else:
                    if str(s_v).lower() != str(v).lower(): return False
            return True
        node_props = current_node.get("properties", {})
        if not match_dict(locator["properties"], node_props): is_match = False
            
    if is_match: matches.append(current_node)
    
    if "children" in current_node:
        for child in current_node["children"]:
            matches.extend(find_nodes(child, locator))
            
    return matches

def resolve_anchor(anchor, parent_pool, is_root, student_data):
    """Khớp mỏ neo (Anchor) để lấy danh sách khối cần chấm."""
    if is_root:
        a_type = anchor.get("type")
        if a_type in ["presentation", "global"]: return [student_data], 1.0
        elif a_type == "slide_master":
            masters = [n for n in student_data.get("children", []) if n.get("type") == "slide_master"]
            return masters, 1.0
        elif a_type == "slide":
            slides = [n for n in student_data.get("children", []) if n.get("type") == "slide"]
            target_index = anchor.get("properties", {}).get("slide_index")
            if not target_index: target_index = anchor.get("slide_index")
            text_contains = anchor.get("text_contains", "")
            
            target_slides = []
            if target_index is not None:
                for s in slides:
                    if s.get("properties", {}).get("slide_index") == int(target_index):
                        target_slides.append(s)
            
            if text_contains and not target_slides:
                norm_target = normalize_anchor_text(text_contains)
                fallback = [s for s in slides if norm_target in normalize_anchor_text(get_all_text_in_node(s))]
                if fallback: 
                    target_slides = fallback
                    return _build_virtual_slides(target_slides, student_data), 0.6 
                    
            if target_slides:
                return _build_virtual_slides(target_slides, student_data), 1.0
            return [], 1.0
        else:
            return find_nodes(student_data, anchor), 1.0
    else:
        if anchor.get("type") == "master_style": return parent_pool, 1.0
        found = []
        for p in parent_pool: found.extend(find_nodes(p, anchor))
        return found, 1.0

def get_inherited_children(student_data, slide_node):
    """Lấy danh sách các phần tử từ Layout và Master mà Slide đang kế thừa."""
    inherited = []
    try:
        layout_target = slide_node.get("properties", {}).get("layout_target", "")
        match_layout = re.search(r'slideLayout(\d+)\.xml', layout_target)
        layout_id = match_layout.group(1) if match_layout else None
        
        master_target = None
        
        # Lấy từ Layout
        if layout_id:
            for child in student_data.get("children", []):
                if child.get("type") == "slide_layout" and child.get("properties", {}).get("layout_id") == layout_id:
                    inherited.extend(child.get("children", []))
                    master_target = child.get("properties", {}).get("master_target", "")
                    break
                    
        # Lấy từ Master
        match_master = re.search(r'slideMaster(\d+)\.xml', master_target) if master_target else None
        master_id = match_master.group(1) if match_master else "1"
        
        for child in student_data.get("children", []):
            if child.get("type") == "slide_master" and child.get("properties", {}).get("master_id") == master_id:
                inherited.extend(child.get("children", []))
                break
    except Exception:
        pass
        
    return inherited

def _build_virtual_slides(slides, student_data):
    """Hợp nhất Slide với Master và Layout để tạo Slide ảo (Flattened Inheritance)"""
    virtual_slides = []
    for s in slides:
        inherited = get_inherited_children(student_data, s)
        v_slide = s.copy()
        v_slide["children"] = s.get("children", []) + inherited
        virtual_slides.append(v_slide)
    return virtual_slides

# ==========================================
# THUẬT TOÁN 2: XÁC ĐỊNH BỐ CỤC KHÔNG GIAN
# ==========================================
def get_spatial_zone(layout):
    if not layout: return "UNKNOWN"
    try:
        x, y = float(layout.get("x", 0)), float(layout.get("y", 0))
        cx, cy = float(layout.get("cx", 0)), float(layout.get("cy", 0))
        center_x, center_y = x + cx / 2, y + cy / 2
        SLIDE_W, SLIDE_H = 12192000, 6858000  
        zones = []
        if center_x < SLIDE_W * 0.33: zones.append("LEFT")
        elif center_x > SLIDE_W * 0.66: zones.append("RIGHT")
        else: zones.append("CENTER_X")
        if center_y < SLIDE_H * 0.33: zones.append("TOP")
        elif center_y > SLIDE_H * 0.66: zones.append("BOTTOM")
        else: zones.append("CENTER_Y")
        return "_".join(zones)
    except: return "UNKNOWN"

def reconstruct_matrix(matched_items, slide_height=6858000):
    if not matched_items: return []
    items_with_centers = []
    for item_id, node in matched_items:
        layout = node.get("layout", {})
        try:
            bx = float(layout.get("x", 0)) + float(layout.get("cx", 0)) / 2
            by = float(layout.get("y", 0)) + float(layout.get("cy", 0)) / 2
            items_with_centers.append({"id": item_id, "bx": bx, "by": by})
        except: continue
    if not items_with_centers: return []
    items_with_centers.sort(key=lambda item: item["by"])
    
    threshold = slide_height * 0.15
    rows, current_row = [], [items_with_centers[0]]
    for item in items_with_centers[1:]:
        if item["by"] - current_row[0]["by"] <= threshold: current_row.append(item)
        else:
            rows.append(current_row)
            current_row = [item]
    rows.append(current_row)
    
    actual_matrix = []
    for row in rows:
        row.sort(key=lambda item: item["bx"])
        actual_matrix.append([item["id"] for item in row])
    return actual_matrix

def verify_item_position(item_id, expected_matrix, actual_matrix):
    exp_row_idx, exp_col_idx, act_row_idx, act_col_idx = -1, -1, -1, -1
    for r_idx, row in enumerate(expected_matrix):
        if item_id in row: exp_row_idx, exp_col_idx = r_idx, row.index(item_id); break
    for r_idx, row in enumerate(actual_matrix):
        if item_id in row: act_row_idx, act_col_idx = r_idx, row.index(item_id); break
    if act_row_idx == -1: return False, "Thiếu khối trong bài làm"
    
    exp_row, act_row = expected_matrix[exp_row_idx], actual_matrix[act_row_idx]
    for peer in [x for x in exp_row if x != item_id]:
        if any(peer in r for r in actual_matrix):
            if peer not in act_row: return False, f"Không cùng hàng ngang với khối {peer}"
            if (exp_row.index(peer) < exp_col_idx) != (act_row.index(peer) < act_col_idx): return False, f"Sai thứ tự Trái/Phải so với khối {peer}"
    for r_idx, row in enumerate(expected_matrix):
        for cid in row:
            if any(cid in r for r in actual_matrix):
                for a_r_idx, a_row in enumerate(actual_matrix):
                    if cid in a_row:
                        if r_idx < exp_row_idx and a_r_idx >= act_row_idx: return False, f"Phải nằm DƯỚI khối {cid}"
                        if r_idx > exp_row_idx and a_r_idx <= act_row_idx: return False, f"Phải nằm TRÊN khối {cid}"
    return True, "Đúng vị trí"

# ==========================================
# ENGINE CHẤM ĐIỂM CHÍNH (ĐỆ QUY ĐA TẦNG)
# ==========================================
def grade_submission(rubric_array, student_data):
    total_score = 0.0
    grading_details = []

    def process_criteria_group(group, parent_pool, is_root, current_multiplier, group_anchor=None):
        nonlocal total_score
        group_name = group.get("criteria_name", "Tiêu chí")
        anchor = group.get("anchor_locator", {})
        if not anchor: anchor = group_anchor

        current_pool, score_mult = resolve_anchor(anchor, parent_pool, is_root, student_data)
        final_mult = current_multiplier * score_mult
        penalty_msg = " [Phạt 40%: Mất Anchor]" if score_mult < 1.0 else ""

        for rule in group.get("rules", []):
            rule_desc = rule.get("description", "")
            points = rule.get("points", 0.0)
            action = rule.get("action", "VERIFY_PROPERTY")
            prop_path = rule.get("property_to_check", "")
            expected = str(rule.get("expected_value", ""))
            match_type = rule.get("match_type", "EXACT")

            status, message, awarded_points, best_partial_val = "FAILED", "", 0.0, None

            if action == "VERIFY_MATRIX_LAYOUT":
                items_def = rule.get("items_definition", {})
                exp_mat_raw = rule.get("expected_matrix", [])
                expected_matrix = json.loads(exp_mat_raw) if isinstance(exp_mat_raw, str) else exp_mat_raw

                matched_items = []
                for item_id, locator in items_def.items():
                    found_nodes = []
                    for anchor_node in current_pool: found_nodes.extend(find_nodes(anchor_node, locator))
                    if found_nodes: matched_items.append((int(item_id), found_nodes[0]))

                actual_matrix = reconstruct_matrix(matched_items)
                total_items = len(items_def)
                passed_count = sum(
                    1 for iid in items_def.keys() if verify_item_position(int(iid), expected_matrix, actual_matrix)[0])

                awarded_points = (passed_count / total_items * points) * final_mult if total_items > 0 else 0
                status = "PASSED" if passed_count == total_items else ("PARTIAL" if passed_count > 0 else "FAILED")
                message = f"Đúng {passed_count}/{total_items} khối bố cục."

            elif action == "VERIFY_COUNT":
                expected_count = int(rule.get("expected_count", 0))
                actual_count = 0
                for node in current_pool:
                    vals = extract_value_by_path(node, prop_path) if prop_path else [node]
                    
                    # FIX: Xử lý thông minh khi dữ liệu là thuộc tính đếm được
                    if isinstance(vals, list) and len(vals) == 1:
                        v = vals[0]
                        if isinstance(v, (int, float)): count_in_node = int(v)
                        elif isinstance(v, str) and v.isdigit(): count_in_node = int(v)
                        else: count_in_node = len(vals)
                    elif isinstance(vals, list): 
                        count_in_node = len(vals)
                    else: 
                        count_in_node = 1 if vals is not None else 0
                        
                    actual_count = max(actual_count, count_in_node)

                if actual_count >= expected_count:
                    awarded_points, status = points * final_mult, "PASSED"
                    message = f"Đạt số lượng (Yêu cầu: {expected_count}, Thực tế: {actual_count})."
                elif actual_count >= expected_count / 2:
                    awarded_points, status = (points * 0.5) * final_mult, "PARTIAL"
                    message = f"Chưa đủ số lượng. Thực tế: {actual_count}/{expected_count}."
                else:
                    message = f"Không đạt số lượng. Thực tế: {actual_count}/{expected_count}."

            elif action in ["VERIFY_PROPERTY", "VERIFY_EXISTS", "VERIFY_LAYOUT"]:
                passed = False
                if not current_pool:
                    message = "Lỗi: Không tìm thấy mỏ neo để đối chiếu (Mất khối)."
                else:
                    for node in current_pool:
                        raw_vals = []

                        if action == "VERIFY_LAYOUT":
                            raw_vals = [get_spatial_zone(node.get("layout", {}))]

                        elif prop_path == "text" or prop_path.endswith(".text"):
                            if prop_path == "text":
                                raw_vals = [normalize_text(get_all_text_in_node(node))]
                            else:
                                p_path = prop_path.replace(".text", "")
                                parents = extract_value_by_path(node, p_path) or search_value_in_tree(node, p_path)
                                if parents: 
                                    raw_vals = [normalize_text(" ".join(get_all_text_in_node(p) for p in parents))]

                        else:
                            # 1. Trích xuất chính xác theo Node
                            raw_vals = extract_value_by_path(node, prop_path)
                            
                            # 2. Cứu hộ Global (VD: Theme)
                            if not raw_vals:
                                global_vals = extract_value_by_path(student_data, prop_path)
                                if global_vals: raw_vals.extend(global_vals)
                            
                            # 3. Cứu hộ khuyết Level (Slide Master)
                            if not raw_vals and "pPr" in prop_path:
                                fb_path = re.sub(r'\.lvl\d+pPr', '', prop_path)
                                fb_vals = extract_value_by_path(node, fb_path)
                                if fb_vals: raw_vals.extend(fb_vals)
                                    
                            # 4. Quét tổng lực
                            if not raw_vals:
                                raw_vals = search_value_in_tree(node, prop_path)

                        actual_vals = []
                        for v in raw_vals:
                            if isinstance(v, list):
                                actual_vals.extend(v)
                                if all(isinstance(x, str) for x in v):
                                    actual_vals.append(",".join(v))
                            else:
                                actual_vals.append(v)

                        for val in actual_vals:
                            if val is None: continue
                            if action == "VERIFY_EXISTS":
                                passed = bool(val) if expected.lower() not in ["false"] else not bool(val)
                            else:
                                str_val = normalize_text(val) if isinstance(val, str) else str(val).strip().lower()
                                str_exp = normalize_text(expected) if isinstance(expected, str) else str(expected).strip().lower()
                                passed = (str_val == str_exp) if match_type == "EXACT" else (str_exp in str_val)
                            if passed: break
                        
                        if not passed and actual_vals and actual_vals[0] is not None and str(actual_vals[0]).strip() != "":
                            best_partial_val = str(actual_vals[0]).strip()
                        if passed: break

                if passed:
                    awarded_points, status, message = points * final_mult, "PASSED", "Hoàn thành."
                elif not message:
                    message = f"Yêu cầu: '{expected}'"
                    if best_partial_val is not None: 
                        message = f"Ghi nhận: '{best_partial_val}' | " + message
                    else:
                        message = f"Ghi nhận: [Không có/Khuyết dữ liệu] | " + message

            total_score += awarded_points
            grading_details.append({
                "group_name": group_name, "description": rule_desc, "max_points": points,
                "awarded_points": round(awarded_points, 2), "status": status, "message": message + penalty_msg
            })

        for sub_group in group.get("sub_criteria", []):
            process_criteria_group(sub_group, current_pool, is_root=False, current_multiplier=final_mult)

    max_possible_score = sum(group.get("allocated_points", 0.0) for group in rubric_array)
    for main_group in rubric_array: process_criteria_group(main_group, [], is_root=True, current_multiplier=1.0)

    return {
        "final_score": round(total_score, 2), "max_possible_score": round(max_possible_score, 2),
        "properties": student_data.get("properties", {}), "details": grading_details
    }

def write_result_to_file(result, output_path):
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    with open("PowerPoint/Results/ast_example.json", "r", encoding="utf-8") as f:
        student_json_data = json.load(f)

    with open("PowerPoint/Rubrics/rubric_graduation_project.json", "r", encoding="utf-8") as f:
        rubric_array = json.load(f)

    result = grade_submission(rubric_array, student_json_data)
    write_result_to_file(result, "PowerPoint/Results/result_example.json")
    print(f"🏆 Tổng điểm: {result['final_score']} / {result['max_possible_score']}")
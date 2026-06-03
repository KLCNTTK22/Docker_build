import xml.etree.ElementTree as ET
from .ast_node import ASTNode
from .xml_utils import NAMESPACES
from .rels_parser import parse_rels
from .shape_parser import parse_shape_tree, parse_text_body


def parse_slide(xml_content, file_path, slide_index, context):
    """
    Phân tích file slide*.xml.
    Bao gồm: Layout target, Transition, Shapes, GraphicFrames (Table, Chart, SmartArt) và Animations.
    """
    node = ASTNode(type_="slide", tag="p:sld")
    node.properties["slide_index"] = int(slide_index)

    try:
        root = ET.fromstring(xml_content.encode('utf-8'))

        # 1. NẠP FILE RELATIONSHIPS CỦA SLIDE NÀY
        # Vd: ppt/slides/slide1.xml -> ppt/slides/_rels/slide1.xml.rels
        rels_path = file_path.replace("ppt/slides/", "ppt/slides/_rels/") + ".rels"
        rels_xml = context["files"].get(rels_path)
        rels = parse_rels(rels_xml) if rels_xml else {}

        # Ghi nhận Layout Target (Slide này dùng bố cục nào)
        for r_id, rel_data in rels.items():
            if "slideLayout" in rel_data.get("Type", ""):
                node.properties["layout_target"] = rel_data.get("Target")
                break

        # 2. XỬ LÝ TRANSITION (HIỆU ỨNG CHUYỂN TRANG)
        # Transition có thể nằm thẳng trong <p:sld> hoặc trong <mc:AlternateContent>
        transition = root.find(f".//{{{NAMESPACES['p']}}}transition")
        if transition is not None:
            trans_node = ASTNode(type_="transition", tag="p:transition")
            trans_node.attributes = dict(transition.attrib)

            # Lấy thẻ con đầu tiên để biết tên loại hiệu ứng (vd: p:push, p:fade)
            for child in transition:
                effect_tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
                trans_node.properties["effect_type"] = f"p:{effect_tag}"
                trans_node.properties["effect_attributes"] = dict(child.attrib)
                break  # Thường chỉ lấy hiệu ứng cốt lõi đầu tiên

            node.add_child(trans_node)

        # 3. ĐỌC CÂY HÌNH HỌC (SHAPE TREE) VÀ GRAPHIC FRAME
        sp_tree = root.find(f".//{{{NAMESPACES['p']}}}spTree")
        if sp_tree is not None:
            # Đọc các shape và picture cơ bản bằng parser dùng chung
            shape_nodes = parse_shape_tree(sp_tree, rels, context)
            for shape_node in shape_nodes:
                node.add_child(shape_node)

            # Bổ sung trích xuất GraphicFrame (Table, Chart, SmartArt)
            for gf in sp_tree.findall(f"{{{NAMESPACES['p']}}}graphicFrame"):
                gf_node = parse_graphic_frame(gf, rels, context)
                node.add_child(gf_node)

        # 4. ĐỌC TIMING VÀ GẮN ANIMATION VÀO ĐÚNG SHAPE
        timing_map = parse_timing(root)
        if timing_map:
            # Duyệt qua các shape con vừa parse được
            for child in node.children:
                if child.type in ["shape", "picture", "graphic_frame"]:
                    # Lấy ID của shape hiện tại
                    spid = child.attributes.get("id")
                    if spid and spid in timing_map:
                        # Gắn list các hiệu ứng vào property của Shape này
                        child.properties["animations"] = timing_map[spid]

    except Exception as e:
        node.add_error(f"Lỗi khi parse slide {file_path}: {e}")

    return node


def parse_graphic_frame(gf_element, rels, context):
    """
    Phân tích thẻ <p:graphicFrame> chứa Table, Chart, hoặc SmartArt.
    """
    node = ASTNode(type_="graphic_frame", tag="p:graphicFrame")

    # 1. Trích xuất ID và Name
    nv_pr = gf_element.find(f".//{{{NAMESPACES['p']}}}cNvPr")
    if nv_pr is not None:
        node.attributes["id"] = nv_pr.attrib.get("id", "")
        node.attributes["name"] = nv_pr.attrib.get("name", "")

    # ==========================================
    # [THÊM MỚI] 1.5 LẤY TỌA ĐỘ (LAYOUT) CỦA GRAPHIC FRAME
    # ==========================================
    xfrm = gf_element.find(f".//{{{NAMESPACES['p']}}}xfrm")
    if xfrm is not None:
        off = xfrm.find(f"{{{NAMESPACES['a']}}}off")
        ext = xfrm.find(f"{{{NAMESPACES['a']}}}ext")
        if off is not None:
            node.layout["x"] = off.attrib.get("x")
            node.layout["y"] = off.attrib.get("y")
        if ext is not None:
            node.layout["cx"] = ext.attrib.get("cx")
            node.layout["cy"] = ext.attrib.get("cy")
    # ==========================================

    graphic_data = gf_element.find(f".//{{{NAMESPACES['a']}}}graphicData")
    if graphic_data is not None:
        uri = graphic_data.attrib.get("uri", "")

        # 1. BẢNG (TABLE)
        tbl = graphic_data.find(f"{{{NAMESPACES['a']}}}tbl")
        if tbl is not None or "table" in uri:
            node.properties["frame_type"] = "table"
            if tbl is not None:
                node.add_child(parse_table(tbl, rels, context))

        # 2. BIỂU ĐỒ (CHART)
        chart_ref = graphic_data.find(f"{{{NAMESPACES['c']}}}chart")
        if chart_ref is not None or "chart" in uri:
            node.properties["frame_type"] = "chart"
            if chart_ref is not None:
                r_id = chart_ref.attrib.get(f"{{{NAMESPACES['r']}}}id")
                if r_id:
                    node.properties["relationship_id"] = r_id
                    target = rels.get(r_id, {}).get("Target")
                    if target:
                        # File chart thực tế thường nằm ở: ppt/charts/chart1.xml
                        chart_path = target.replace("../", "ppt/")
                        chart_xml = context["files"].get(chart_path)
                        if chart_xml:
                            node.add_child(parse_chart_data(chart_xml))

        # 3. SMARTART (DIAGRAM)
        smartart_ref = graphic_data.find(f"{{{NAMESPACES['dgm']}}}relIds")
        if smartart_ref is not None or "diagram" in uri:
            node.properties["frame_type"] = "smartart"
            if smartart_ref is not None:
                # Lấy các rId cấu thành SmartArt (Data, Layout, Style, Color)
                for attr_name, prop_name in [("dm", "data_rel_id"), ("lo", "layout_rel_id"), ("qs", "style_rel_id"),
                                             ("cs", "color_rel_id")]:
                    r_id = smartart_ref.attrib.get(f"{{{NAMESPACES['r']}}}{attr_name}")
                    if r_id:
                        node.properties[prop_name] = r_id

                # Truy xuất file DataModel để lấy cấu trúc node và chữ
                dm_id = node.properties.get("data_rel_id")
                if dm_id:
                    target = rels.get(dm_id, {}).get("Target")
                    if target:
                        # File data thường nằm ở: ppt/diagrams/data1.xml
                        data_path = target.replace("../", "ppt/")
                        data_xml = context["files"].get(data_path)
                        if data_xml:
                            node.add_child(parse_smartart_data(data_xml, rels, context))

    return node


def parse_table(tbl_element, rels, context):
    """
    Trích xuất dữ liệu Bảng: gộp ô (rowSpan, gridSpan), thuộc tính fill, và chữ bên trong.
    """
    node = ASTNode(type_="table", tag="a:tbl")

    # Đếm số cột
    tbl_grid = tbl_element.find(f"{{{NAMESPACES['a']}}}tblGrid")
    if tbl_grid is not None:
        grid_cols = tbl_grid.findall(f"{{{NAMESPACES['a']}}}gridCol")
        node.properties["cols_count"] = len(grid_cols)

    # Duyệt từng dòng
    for tr_elem in tbl_element.findall(f"{{{NAMESPACES['a']}}}tr"):
        tr_node = ASTNode(type_="table_row", tag="a:tr")
        tr_node.attributes["h"] = tr_elem.attrib.get("h", "")

        # Duyệt từng ô
        for tc_elem in tr_elem.findall(f"{{{NAMESPACES['a']}}}tc"):
            tc_node = ASTNode(type_="table_cell", tag="a:tc")

            # Trích xuất thông tin gộp ô (Merge Cells)
            if "rowSpan" in tc_elem.attrib:
                tc_node.attributes["rowSpan"] = tc_elem.attrib["rowSpan"]
            if "gridSpan" in tc_elem.attrib:
                tc_node.attributes["gridSpan"] = tc_elem.attrib["gridSpan"]

            # Trích xuất thuộc tính định dạng (Background Fill)
            tc_pr = tc_elem.find(f"{{{NAMESPACES['a']}}}tcPr")
            if tc_pr is not None:
                solid_fill = tc_pr.find(f"{{{NAMESPACES['a']}}}solidFill")
                if solid_fill is not None and len(solid_fill) > 0:
                    color_elem = list(solid_fill)[0]  # Thường là a:schemeClr hoặc a:srgbClr
                    tc_node.properties["fill_color"] = color_elem.attrib.get("val", color_elem.tag.split('}')[-1])

            # Trích xuất nội dung văn bản (tận dụng hàm parse_text_body từ shape_parser)
            tx_body = tc_elem.find(f"{{{NAMESPACES['a']}}}txBody")
            if tx_body is not None:
                paragraphs = parse_text_body(tx_body, rels, context)
                for p in paragraphs:
                    tc_node.add_child(p)

            tr_node.add_child(tc_node)

        node.add_child(tr_node)

    return node


def parse_chart_data(xml_content):
    """
    Trích xuất dữ liệu Biểu đồ (Loại biểu đồ, Data Series).
    """
    node = ASTNode(type_="chart_data", tag="c:chartSpace")
    try:
        root = ET.fromstring(xml_content.encode('utf-8'))
        chart = root.find(f".//{{{NAMESPACES['c']}}}chart")
        if chart is None:
            return node

        plot_area = chart.find(f".//{{{NAMESPACES['c']}}}plotArea")
        if plot_area is not None:
            # Quét để tìm loại biểu đồ (barChart, pieChart, lineChart, doughnutChart...)
            for child in plot_area:
                tag_name = child.tag.split('}')[-1] if '}' in child.tag else child.tag
                if tag_name.endswith("Chart"):
                    node.properties["chart_type"] = tag_name

                    # Trích xuất dữ liệu Series
                    series_list = []
                    for ser in child.findall(f"{{{NAMESPACES['c']}}}ser"):
                        ser_data = {
                            "tag": "c:ser",
                            "idx": ser.find(f"{{{NAMESPACES['c']}}}idx").attrib.get("val", "") if ser.find(
                                f"{{{NAMESPACES['c']}}}idx") is not None else "",
                            "name": "",
                            "values": []
                        }

                        # Lấy tên Series
                        tx = ser.find(f"{{{NAMESPACES['c']}}}tx")
                        if tx is not None:
                            v = tx.find(f".//{{{NAMESPACES['c']}}}v")
                            if v is not None:
                                ser_data["name"] = v.text

                        # Lấy các giá trị (Data Values)
                        val = ser.find(f"{{{NAMESPACES['c']}}}val")
                        if val is not None:
                            for v in val.findall(f".//{{{NAMESPACES['c']}}}v"):
                                ser_data["values"].append(v.text)

                        series_list.append(ser_data)

                    node.properties["series"] = series_list
                    break  # Thường chỉ xử lý loại biểu đồ chính đầu tiên

    except Exception as e:
        node.add_error(f"Lỗi khi parse chart: {e}")

    return node


def parse_smartart_data(xml_content, rels, context):
    """
    Trích xuất dữ liệu SmartArt (Diagram) từ file ppt/diagrams/data*.xml.
    Quét danh sách điểm (Point List) để lấy các node văn bản bên trong.
    """
    node = ASTNode(type_="smartart_data", tag="dgm:dataModel")
    try:
        root = ET.fromstring(xml_content.encode('utf-8'))

        # Danh sách các điểm (node) cấu thành SmartArt
        pt_lst = root.find(f".//{{{NAMESPACES['dgm']}}}ptLst")
        if pt_lst is not None:
            for pt in pt_lst.findall(f"{{{NAMESPACES['dgm']}}}pt"):
                pt_node = ASTNode(type_="smartart_node", tag="dgm:pt")
                pt_node.attributes["modelId"] = pt.attrib.get("modelId", "")

                # Loại node (pres, doc, asst, node...)
                pr_set = pt.find(f"{{{NAMESPACES['dgm']}}}prSet")
                if pr_set is not None:
                    pt_node.properties["ptType"] = pr_set.attrib.get("ptType", "")

                # Trích xuất nội dung văn bản nằm trong thẻ <dgm:t> (đóng vai trò như txBody)
                t_elem = pt.find(f"{{{NAMESPACES['dgm']}}}t")
                if t_elem is not None:
                    # Vì <dgm:t> chứa trực tiếp <a:p> (Paragraph) nên dùng chung hàm parse_text_body rất hoàn hảo
                    paragraphs = parse_text_body(t_elem, rels, context)
                    for p in paragraphs:
                        pt_node.add_child(p)

                node.add_child(pt_node)

    except Exception as e:
        node.add_error(f"Lỗi khi parse smartart: {e}")

    return node


def parse_timing(root):
    """
    Quét thẻ <p:timing> ở cuối Slide để tìm các animation được gán cho các shape.
    Do ElementTree không hỗ trợ thuộc tính .parent, ta duyệt trực tiếp các thẻ <p:cTn>
    (Common Time Node) để bắt thông tin, và tìm <p:spTgt> bên trong nó để lấy ID Shape.
    Trả về: Dictionary map `spid` -> danh sách các cấu hình animation.
    """
    timing_map = {}
    timing = root.find(f".//{{{NAMESPACES['p']}}}timing")

    if timing is None:
        return timing_map

    # Duyệt qua toàn bộ các Common Time Node (chứa thông tin hiệu ứng)
    for ctn in timing.findall(f".//{{{NAMESPACES['p']}}}cTn"):
        # Chỉ lấy các cTn có định hướng tới một Shape cụ thể (spTgt)
        sp_tgt = ctn.find(f".//{{{NAMESPACES['p']}}}spTgt")
        if sp_tgt is not None:
            spid = sp_tgt.attrib.get("spid")
            if spid:
                if spid not in timing_map:
                    timing_map[spid] = []

                # Trích xuất dữ liệu gốc của Animation
                # presetClass thường là: entr (Entrance), exit (Exit), emph (Emphasis)
                anim_info = {
                    "tag": "p:cTn",
                    "presetID": ctn.attrib.get("presetID", ""),
                    "presetClass": ctn.attrib.get("presetClass", ""),
                    "nodeType": ctn.attrib.get("nodeType", "")
                }

                # Cố gắng lấy thêm thông tin chi tiết về chiều/hiệu ứng nếu có (p:animEffect)
                # (Thuộc tính này có thể nằm ngang hàng hoặc là cha của cTn tùy cấu trúc,
                # nhưng để giữ thiết kế raw thô, ta lưu lại cTn attributes là đủ để Rubric tra cứu)

                timing_map[spid].append(anim_info)

    return timing_map
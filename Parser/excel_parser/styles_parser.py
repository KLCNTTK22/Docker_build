import xml.etree.ElementTree as ET
from .xml_utils import NAMESPACES


def parse_styles(xml_content):
    if not xml_content:
        return {}

    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError:
        return {}

    parsed_fonts = []
    parsed_fills = []
    parsed_borders = []
    cell_xfs_list = []

    # 1. Quét kho FONTS (Bổ sung lấy mã màu)
    fonts_node = root.find('main:fonts', NAMESPACES)
    if fonts_node is not None:
        for font in fonts_node.findall('main:font', NAMESPACES):
            font_data = {}
            if font.find('main:b', NAMESPACES) is not None: font_data['bold'] = True
            if font.find('main:i', NAMESPACES) is not None: font_data['italic'] = True
            if font.find('main:u', NAMESPACES) is not None: font_data['underline'] = True

            # Lấy màu sắc (Có thể là RGB hoặc Theme ID)
            color_node = font.find('main:color', NAMESPACES)
            if color_node is not None:
                if color_node.attrib.get('rgb'):
                    font_data['color_rgb'] = color_node.attrib.get('rgb')
                elif color_node.attrib.get('theme'):
                    font_data['color_theme'] = color_node.attrib.get('theme')

            parsed_fonts.append(font_data)

    # 2. Quét kho FILLS (Bổ sung lấy màu nền)
    fills_node = root.find('main:fills', NAMESPACES)
    if fills_node is not None:
        for fill in fills_node.findall('main:fill', NAMESPACES):
            fill_data = {}
            pattern = fill.find('main:patternFill', NAMESPACES)
            if pattern is not None:
                p_type = pattern.attrib.get('patternType', 'none')
                fill_data['patternType'] = p_type

                # Trong Excel, màu đổ nền "Solid" thường được lưu ở fgColor của pattern!
                fg_color = pattern.find('main:fgColor', NAMESPACES)
                if fg_color is not None:
                    if fg_color.attrib.get('rgb'):
                        fill_data['bg_color_rgb'] = fg_color.attrib.get('rgb')
                    elif fg_color.attrib.get('theme'):
                        fill_data['bg_color_theme'] = fg_color.attrib.get('theme')
                    fill_data['has_color'] = True

            parsed_fills.append(fill_data)

    # 3. Quét kho BORDERS
    borders_node = root.find('main:borders', NAMESPACES)
    if borders_node is not None:
        for border in borders_node.findall('main:border', NAMESPACES):
            border_data = {}
            for edge in ['left', 'right', 'top', 'bottom']:
                edge_node = border.find(f'main:{edge}', NAMESPACES)
                if edge_node is not None and edge_node.attrib.get('style'):
                    border_data[edge] = True
            parsed_borders.append(border_data)

    # 4. Quét BẢNG ÁNH XẠ (CellXfs)
    cellxfs_node = root.find('main:cellXfs', NAMESPACES)
    if cellxfs_node is not None:
        for xf in cellxfs_node.findall('main:xf', NAMESPACES):
            xf_data = {}

            # Lưu numFmtId cho việc kiểm tra định dạng Số/Tiền tệ/Ngày tháng
            xf_data["numFmtId"] = xf.attrib.get('numFmtId', '0')

            font_id = int(xf.attrib.get('fontId', 0))
            fill_id = int(xf.attrib.get('fillId', 0))
            border_id = int(xf.attrib.get('borderId', 0))

            if font_id < len(parsed_fonts) and parsed_fonts[font_id]:
                xf_data["font"] = parsed_fonts[font_id]

            if fill_id < len(parsed_fills):
                f_data = parsed_fills[fill_id]
                if f_data.get("patternType") not in ["none", "gray125"] or f_data.get("has_color"):
                    xf_data["fill"] = f_data

            if border_id < len(parsed_borders) and parsed_borders[border_id]:
                xf_data["border"] = parsed_borders[border_id]

            alignment = xf.find('main:alignment', NAMESPACES)
            if alignment is not None:
                align_data = {}
                if alignment.attrib.get('horizontal'): align_data['horizontal'] = alignment.attrib.get('horizontal')
                if alignment.attrib.get('vertical'): align_data['vertical'] = alignment.attrib.get('vertical')
                if alignment.attrib.get('wrapText') in ['1', 'true']: align_data['wrapText'] = True
                if align_data: xf_data["alignment"] = align_data

            cell_xfs_list.append(xf_data)

    # 5. Quét kho DXFS (Dùng cho Conditional Formatting)
    dxfs_list = []
    dxfs_node = root.find('main:dxfs', NAMESPACES)
    if dxfs_node is not None:
        for dxf in dxfs_node.findall('main:dxf', NAMESPACES):
            dxf_data = {}
            font_color = dxf.find('.//main:font/main:color', NAMESPACES)
            if font_color is not None and font_color.attrib.get('rgb'):
                dxf_data['font_color'] = font_color.attrib.get('rgb')

            bg_color = dxf.find('.//main:patternFill/main:bgColor', NAMESPACES)
            if bg_color is not None and bg_color.attrib.get('rgb'):
                dxf_data['bg_color'] = bg_color.attrib.get('rgb')

            dxfs_list.append(dxf_data)

    return {
        "cellXfs": cell_xfs_list,
        "dxfs": dxfs_list
    }
import xml.etree.ElementTree as ET
from .ast_node import ASTNode
from .xml_utils import NAMESPACES


def parse_chart(xml_content, chart_id):
    """
    Phân tích file xl/charts/chartX.xml
    Trả về một ASTNode chứa thông tin biểu đồ.
    """
    if not xml_content:
        return None

    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError:
        return None

    chart_node = ASTNode(type_="chart", tag="chartSpace")
    chart_node.properties = {"id": chart_id}

    chart = root.find('.//c:chart', NAMESPACES)
    if chart is None:
        return chart_node

    plot_area = chart.find('c:plotArea', NAMESPACES)
    if plot_area is not None:
        # 1. Xác định CÁC LOẠI biểu đồ có trong PlotArea (vd: barChart, lineChart, pieChart)
        # Excel có thể có biểu đồ kết hợp (Combo chart) nên cần quét hết
        chart_types = []
        for child in plot_area:
            # child.tag có dạng '{http://.../chart}barChart'
            tag_name = child.tag.split('}')[-1]
            if tag_name.endswith('Chart'):
                chart_types.append(tag_name)

                # 2. Phân tích DỮ LIỆU (Series) của biểu đồ này
                for series in child.findall('c:ser', NAMESPACES):
                    series_node = ASTNode(type_="chart_series", tag="ser")

                    # Lấy tên của Series (Nếu có tham chiếu)
                    tx_f = series.find('.//c:tx//c:f', NAMESPACES)
                    if tx_f is not None and tx_f.text:
                        series_node.properties["name_ref"] = tx_f.text

                    # Lấy vùng dữ liệu Categories (Trục X)
                    cat_f = series.find('.//c:cat//c:f', NAMESPACES)
                    if cat_f is not None and cat_f.text:
                        series_node.properties["category_ref"] = cat_f.text

                    # Lấy vùng dữ liệu Values (Trục Y)
                    val_f = series.find('.//c:val//c:f', NAMESPACES)
                    if val_f is not None and val_f.text:
                        series_node.properties["value_ref"] = val_f.text

                    chart_node.add_child(series_node)

        chart_node.properties["chart_types"] = list(set(chart_types))

    return chart_node
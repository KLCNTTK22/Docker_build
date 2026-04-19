import xml.etree.ElementTree as ET
from .xml_utils import NAMESPACES


def parse_app_props(xml_content):
    """
    Trích xuất cấu hình ứng dụng từ file docProps/app.xml.
    (Chứa số lượng slide, chữ, kích thước format...)
    """
    props = {}
    try:
        root = ET.fromstring(xml_content.encode('utf-8'))

        # Thẻ app.xml mặc định sử dụng namespace extended-properties ('ep')
        ep_ns = NAMESPACES['ep']

        # Duyệt qua tất cả các thẻ con trực tiếp của thẻ gốc <Properties>
        for child in root:
            # Loại bỏ phần URL namespace để lấy tên thẻ sạch (vd: Slides, Words, PresentationFormat)
            tag_name = child.tag.replace(f"{{{ep_ns}}}", "")

            # Chỉ lấy các thẻ có chứa giá trị text đơn giản, bỏ qua các thẻ phức tạp như <HeadingPairs> (vì không cần thiết cho chấm điểm)
            if child.text and child.text.strip():
                props[tag_name] = child.text

    except Exception as e:
        print(f"[Cảnh báo] Lỗi khi parse app.xml: {e}")

    return props
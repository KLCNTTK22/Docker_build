import xml.etree.ElementTree as ET
from .xml_utils import NAMESPACES


def parse_presentation(xml_content, context):
    """
    Trích xuất thông tin cấu trúc cốt lõi từ file ppt/presentation.xml.
    Bao gồm: Kích thước slide, danh sách rId của Slide, danh sách rId của Slide Master.
    """
    data = {
        "slide_size": {},
        "slide_rIds": [],
        "slide_master_rIds": []
    }

    try:
        # Parse XML từ string
        root = ET.fromstring(xml_content.encode('utf-8'))

        # 1. Trích xuất Kích thước Slide (Slide Size)
        # Ví dụ: <p:sldSz cx="12192000" cy="6858000"/>
        sld_sz = root.find(f"{{{NAMESPACES['p']}}}sldSz")
        if sld_sz is not None:
            data["slide_size"] = {
                "cx": sld_sz.attrib.get("cx", ""),
                "cy": sld_sz.attrib.get("cy", "")
            }

        # 2. Trích xuất danh sách Slide
        # <p:sldIdLst><p:sldId id="256" r:id="rId2"/>...
        sld_id_lst = root.find(f"{{{NAMESPACES['p']}}}sldIdLst")
        if sld_id_lst is not None:
            for sld_id in sld_id_lst.findall(f"{{{NAMESPACES['p']}}}sldId"):
                # Lấy thuộc tính r:id để ánh xạ trong file .rels
                r_id = sld_id.attrib.get(f"{{{NAMESPACES['r']}}}id")
                if r_id:
                    data["slide_rIds"].append(r_id)

        # 3. Trích xuất danh sách Slide Master
        # <p:sldMasterIdLst><p:sldMasterId id="2147483648" r:id="rId1"/>...
        sld_master_id_lst = root.find(f"{{{NAMESPACES['p']}}}sldMasterIdLst")
        if sld_master_id_lst is not None:
            for master_id in sld_master_id_lst.findall(f"{{{NAMESPACES['p']}}}sldMasterId"):
                r_id = master_id.attrib.get(f"{{{NAMESPACES['r']}}}id")
                if r_id:
                    data["slide_master_rIds"].append(r_id)

    except Exception as e:
        print(f"[Cảnh báo] Lỗi khi parse presentation.xml: {e}")

    return data
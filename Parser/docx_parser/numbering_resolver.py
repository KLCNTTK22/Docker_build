def resolve_numbering(num_id, ilvl, numbering_data):
    """
    Trả về định dạng cụ thể của một dòng danh sách dựa trên numId và cấp độ.
    """
    if not num_id or ilvl is None or not numbering_data:
        return None

    # Đảm bảo num_id và ilvl là string để khớp với keys trong numbering_data
    num_entry = numbering_data.get(str(num_id))
    if not num_entry or "levels" not in num_entry:
        return None

    level_info = num_entry["levels"].get(str(ilvl))
    if not level_info:
        return None

    # Trả về bản sao thông tin định dạng
    return {
        "format": level_info.get("format"),
        "text": level_info.get("text"),
        "start": level_info.get("start")
    }
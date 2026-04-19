def clean_json(data):
    """
    Làm sạch dữ liệu JSON:
    - Loại bỏ key có giá trị null, list rỗng, dict rỗng
    """

    if isinstance(data, dict):
        cleaned_dict = {}

        for k, v in data.items():
            cleaned_v = clean_json(v)

            if cleaned_v is not None and cleaned_v != [] and cleaned_v != {}:
                cleaned_dict[k] = cleaned_v

        return cleaned_dict if cleaned_dict else None

    elif isinstance(data, list):
        cleaned_list = [clean_json(item) for item in data]
        return [item for item in cleaned_list if item is not None]

    else:
        return data
def resolve_style(style_id, styles):

    result = {}

    current = styles.get(style_id)

    while current:

        for k,v in current.items():
            if k not in result:
                result[k] = v

        parent = current.get("basedOn")

        if parent:
            current = styles.get(parent)
        else:
            break

    return result
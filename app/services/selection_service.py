def select_top_bundle_item(bundle_sorted, q, is_definition_query, is_punishment_query):
    top = bundle_sorted[0]

    if "theft" in q:
        if is_definition_query:
            for b in bundle_sorted:
                if str(b["section"]) == "378":
                    return b

        elif is_punishment_query:
            for b in bundle_sorted:
                if str(b["section"]) == "379":
                    return b

    return top
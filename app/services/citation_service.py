def build_citations(top, bundle_sorted):
    citations = []
    allowed_sections = {top["section"]}

    if top["act"] == "The Penal Code, 1860" and str(top["section"]) == "379":
        allowed_sections.add(378)

    heading_part = f" ({top['heading']})" if top.get("heading") else ""
    citations.append(
        f"{top['act']} — Section {top['section']}{heading_part}, pp. {top['pages'][0]}–{top['pages'][1]}"
    )

    seen_sections = {top["section"]}

    for b in bundle_sorted:
        if b["section"] in seen_sections:
            continue
        if b["section"] not in allowed_sections:
            continue

        heading_part = f" ({b['heading']})" if b.get("heading") else ""
        citations.append(
            f"{b['act']} — Section {b['section']}{heading_part}, pp. {b['pages'][0]}–{b['pages'][1]}"
        )
        seen_sections.add(b["section"])

    return citations
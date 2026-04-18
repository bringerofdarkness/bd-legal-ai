def log_query(query, query_type, law_hint, top_section, enabled=False):
    if not enabled:
        return

    print("\n[LOG]")
    print(f"Query: {query}")
    print(f"Type: {query_type}")
    print(f"Law hint: {law_hint}")
    print(f"Top section: {top_section}")
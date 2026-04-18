def order_evidence(top, bundle_sorted):
    return [top] + [b for b in bundle_sorted if b != top]
"""Gemeinsame Testhilfen."""

from stk_scenario import Instance


def manual_instance(events, n_stacks, max_height):
    """Handgebaute Instanz aus einer Ereignisfolge [("A", 0), ("A", 1), ("D", 0), ...]."""
    arrival = {c: t for t, (k, c) in enumerate(events) if k == "A"}
    departure = {c: t for t, (k, c) in enumerate(events) if k == "D"}
    dwell = sum(departure[c] - arrival[c] for c in departure) / len(departure)
    return Instance(n_stacks, max_height, 1.0, len(departure), 0, n_stacks * max_height, tuple(events),
                    arrival, departure, dwell)

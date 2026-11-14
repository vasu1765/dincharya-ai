"""Owner-approved publisher diagnostics over unchanged Cycle 1 evidence."""
import json
from math import isfinite
from pathlib import Path

PUBLISHER_TOLERANCE_SECONDS = 90
TIERS = {
    "drik_ekadashi": "primary",
    "drik2026": "primary",
    "pac2023": "secondary",
    "himalayan2025": "historical",
}
EVIDENCE = {
    "feasibility": "comparisons",
    "validation": "additional_transitions",
    "recurrence": "new_timing_diagnostics",
}


def publisher_comparison(source, delta_seconds):
    if not isfinite(delta_seconds):
        raise ValueError("Finite publisher residual required")
    return {
        "tier": TIERS.get(source, "context"),
        "within_display_diagnostic": abs(delta_seconds) <= PUBLISHER_TOLERANCE_SECONDS,
    }


def report(directory=Path(__file__).parent):
    rows = []
    for stem, key in EVIDENCE.items():
        evidence = json.loads((directory / f"{stem}-results.json").read_text(encoding="utf-8"))
        for record in evidence[key]:
            ref = record.get("reference", record)
            source = ref["source"]
            delta = record["delta_seconds"]
            rows.append(dict(source=source, published_at=ref.get("at", ref.get("published_at")),
                             delta_seconds=delta, **publisher_comparison(source, delta)))
    counts = {}
    for tier in ("primary", "secondary", "historical", "context"):
        comparisons = [row for row in rows if row["tier"] == tier]
        counts[tier] = dict(total=len(comparisons),
                            within=sum(row["within_display_diagnostic"] for row in comparisons))
    return dict(publisher_tolerance_seconds=PUBLISHER_TOLERANCE_SECONDS,
                counts=counts, comparisons=rows)


if __name__ == "__main__":
    print(json.dumps(report(), indent=2))

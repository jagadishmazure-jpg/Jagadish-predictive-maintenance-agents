"""Equipment-vendor advisory feed: fake (seeded) and live (explicit gap).

The live backend is a documented stub: it never hallucinates advisories,
it reports the gap instead.
"""

from __future__ import annotations

import random

_FAKE_ADVISORIES = [
    {"vendor": "Axis Bearing Co.", "advisory_id": "ADV-2026-014",
     "subject": "Bearing series 6205: extended L10 life with synthetic grease",
     "applies_to": "centrifugal pump", "severity": "info"},
    {"vendor": "Axis Bearing Co.", "advisory_id": "ADV-2026-021",
     "subject": "Seal kit 88: inspect for lip wear above 5000 h service",
     "applies_to": "air compressor", "severity": "watch"},
]


class FakeVendorFeed:
    """Deterministic seeded advisory feed."""

    def __init__(self, seed: int = 42):
        self._rng = random.Random(seed)

    def advisories(self, asset_type: str | None = None) -> list[dict]:
        items = list(_FAKE_ADVISORIES)
        self._rng.shuffle(items)
        if asset_type:
            items = [a for a in items if a["applies_to"] == asset_type]
        return items


class LiveVendorFeed:
    """Live backend stub: reports the integration gap, never invents data."""

    def advisories(self, asset_type: str | None = None) -> dict:
        return {
            "gap": True,
            "reason": "live vendor API not configured; "
                      "wire advisories() to the vendor feed here",
        }

# Threat model (STRIDE-lite)

## Assets
Sensor telemetry, work-order queue, audit chain, feedback text.

## Threats
- **Tampering:** audit entries modified to hide a missed failure -> hash
  chain detects (tested: `test_audit_tamper_detected`).
- **Elevation:** agent asked to write to the DB (e.g. close work orders) ->
  SELECT-only gateway rejects; write keywords scanned literal-aware.
- **Information disclosure:** technician PII in feedback text -> scrubbed
  to placeholders before storage (tested).
- **Denial of service:** runaway query -> 100-row LIMIT cap on every query.
- **Spoofing (vendor feed):** fake advisories presented as live -> live
  backend returns an explicit gap, never invented advisories.

## Out of scope
Physical sensor security, network segmentation, and historian access
control belong to the plant OT layer, not this repo.

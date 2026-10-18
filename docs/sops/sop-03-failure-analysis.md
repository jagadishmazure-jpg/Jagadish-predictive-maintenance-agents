# SOP-03: Failure Analysis

## After an unplanned stop
Record the downtime event with asset, line, duration, and cause within one
shift. Compare the actual failure against the last prediction: note the
predicted RUL and the feature that drove it.

## Feature review
When a prediction misses, check each breakdown term — vibration slope,
temperature slope, vibration level, age. A miss caused by a sensor fault
(mounting, calibration) is a data problem, not a model problem; fix the
sensor and re-baseline.

## Recurrence control
If the same asset fails twice for the same cause within 90 days, escalate
to engineering for a root-cause review instead of repeating the repair.

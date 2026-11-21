# Inspection event contract

The JSON Schema in `inspection-event.schema.json` defines the record exchanged by the edge application and operator interface.

Each defect finding contains a defect type, severity, location and confidence. Severity is kept independent from confidence. The allowed severity values are LOW, MEDIUM, HIGH and UNASSESSED; UNASSESSED is used when no board-specific impact policy has rated the finding.

The example event is illustrative and is not a detector measurement.

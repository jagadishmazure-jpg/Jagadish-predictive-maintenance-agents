"""Print the domain differentiator on the seeded data (README block, CI-checked)."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from predmaint import predict, prioritize, telemetry, views  # noqa: E402

conn = telemetry.build_db()
views.create_views(conn)
print("Failure-prediction scorer, top 3 by risk:")
for s in predict.predict_all(conn)[:3]:
    print(f"  {s['asset_id']}: risk {s['risk']}, RUL {s['rul_days']} days, contrib {s['breakdown']['contrib']}")
print("Work-order prioritizer (100 x crit/5 x P(fail) x impact/5; impact = criticality today):")
for r in prioritize.prioritize(conn):
    print(f"  {r['wo_id']} {r['asset_id']}: {r['score']} {r['band']}")
print()
probe = telemetry.build_db()
probe.execute("UPDATE sensor_readings SET vibration_mm_s = 5.2, temp_c = 88 WHERE asset_id = 'FAN-402'")
s = predict.score_asset(probe, "FAN-402")
print(f"FAN-402 held flat at 5.2 mm/s and 88 C: alerts {[a[0] for a in s['alerts']]}, "
      f"risk {s['risk']} (alert floor {s['breakdown']['alert_floor']}), RUL {s['rul_days']} days")
print()
try:
    views.run_query(conn, "SELECT * FROM v_asset_health, assets")
except views.GatewayError as exc:
    print(f"Gateway: {exc}")

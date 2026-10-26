#!/usr/bin/env bash
# Trigger the Airflow DAG for clean and defective loads, then read the API.
set -euo pipefail
API="http://localhost:${API_PORT:-8010}"
run() {
  docker compose exec -T airflow airflow dags trigger dq_validate_load \
    --conf "$1" >/dev/null
}
run '{"batch_index": 0}'
run '{"batch_index": 1}'
run '{"batch_index": 2, "defect": "nulls"}'
run '{"batch_index": 3, "defect": "schema_change"}'
run '{"batch_index": 4, "defect": "value_drift"}'
run '{"batch_index": 5, "defect": "row_loss"}'
echo "Waiting for 6 runs in the audit log..."
for _ in $(seq 1 90); do
  n=$(curl -s "$API/health" | python3 -c 'import json,sys; print(json.load(sys.stdin)["runs"])' 2>/dev/null || echo 0)
  [ "$n" -ge 6 ] && break
  sleep 5
done
echo "--- $API/health"
curl -s "$API/health" | python3 -m json.tool
echo "--- $API/alerts"
curl -s "$API/alerts" | python3 -m json.tool

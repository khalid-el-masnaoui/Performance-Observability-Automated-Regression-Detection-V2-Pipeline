import os
import json
import time
import requests
import redis
from flask import Flask, request, jsonify

app = Flask(__name__)

# config (use env vars in real setup)
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://prometheus:9090")
REPORT_URL = os.getenv("REPORT_URL", "http://report-service:5000")
SLACK_WEBHOOK = os.getenv("SLACK_WEBHOOK")

r = redis.Redis(host=REDIS_HOST, port=6379, decode_responses=True)

print ("App started", flush=True)

# -------------------------
# Prometheus query
# -------------------------

def query_prometheus_p95(route):
    query = f'''
    histogram_quantile(0.95,
      sum(rate(app_request_duration_seconds_bucket{{route="{route}"}}[2m])) by (le)
    )
    '''

    try:
        res = requests.get(f"{PROMETHEUS_URL}/api/v1/query", params={"query": query})
        data = res.json()

        results = data.get("data", {}).get("result", [])

        if not results: 
            return 0

        value = results[0]["value"][1]

        if value in ["NaN", "null", None]:
            return 0

        return round(float(value), 4)

    except Exception as e:
        print("Prometheus query error:", e, flush=True)
        return 0

def query_prometheus_metrics(route):
    # --------------------------------------------------
    # Helper
    # --------------------------------------------------

    def run_query(query):

        try:

            response = requests.get(f"{PROMETHEUS_URL}/api/v1/query", params={"query": query})

            data = response.json()

            results = data.get("data", {}).get("result", [])

            if not results:
                return 0

            value = results[0]["value"][1]

            if value in ["NaN", "null", None]:
                return 0

            return round(float(value), 4)

        except Exception as e:

            print(f"Prometheus query failed: {e}", flush=True)

            return 0

    # --------------------------------------------------
    # P95
    # --------------------------------------------------

    p95_query = f'''
    histogram_quantile(
      0.95,
      sum(
        rate(
          app_request_duration_seconds_bucket{{route="{route}"}}[2m]
        )
      ) by (le)
    )
    '''

    # --------------------------------------------------
    # P99
    # --------------------------------------------------

    p99_query = f'''
    histogram_quantile(
      0.99,
      sum(
        rate(
          app_request_duration_seconds_bucket{{route="{route}"}}[2m]
        )
      ) by (le)
    )
    '''

    # --------------------------------------------------
    # AVG
    # --------------------------------------------------

    avg_query = f'''
    rate(
      app_request_duration_seconds_sum{{route="{route}"}}[2m]
    )
    /
    rate(
      app_request_duration_seconds_count{{route="{route}"}}[2m]
    )
    '''

    # --------------------------------------------------
    # ERROR RATE
    # --------------------------------------------------

    error_query = f'''
    (
      sum(
        rate(
          app_requests_total{{route="{route}",status=~"5.."}}[2m]
        )
      )
      /
      sum(
        rate(
          app_requests_total{{route="{route}"}}[2m]
        )
      )
    )
    '''

    # --------------------------------------------------
    # MAX LATENCY
    # --------------------------------------------------

    max_query = f'''
    max_over_time(
      app_request_duration_seconds_sum{{route="{route}"}}[5m]
    )
    '''

    # --------------------------------------------------
    # THROUGHPUT
    # --------------------------------------------------

    throughput_query = f'''
    sum(
      rate(
        app_request_duration_seconds_count{{route="{route}"}}[1m]
      )
    )
    '''

    # --------------------------------------------------
    # Execute all queries
    # --------------------------------------------------

    metrics = {

        "p95": run_query(p95_query),

        "p99": run_query(p99_query),

        "avg": run_query(avg_query),

        "error_rate": run_query(error_query),

        "max_latency": run_query(max_query),

        "throughput": run_query(throughput_query)
    }

    return metrics

def query_prometheus_metrics_optimized():
    # ---------------------------------------------------
    # Helper
    # ---------------------------------------------------

    def run_query(query):

        try:

            response = requests.get(f"{PROMETHEUS_URL}/api/v1/query", params={"query": query})

            data = response.json()

            return data.get("data", {}).get("result", [])

        except Exception as e:

            print(f"Prometheus query failed: {e}", flush=True)

            return []

    # ---------------------------------------------------
    # Queries
    # ---------------------------------------------------

    queries = {

        "p95": '''
        histogram_quantile(
          0.95,
          sum(
            rate(app_request_duration_seconds_bucket[2m])
          ) by (le, route)
        )
        ''',

        "p99": '''
        histogram_quantile(
          0.99,
          sum(
            rate(app_request_duration_seconds_bucket[2m])
          ) by (le, route)
        )
        ''',

        "avg": '''
        sum(rate(app_request_duration_seconds_sum[2m])) by (route)
        /
        sum(rate(app_request_duration_seconds_count[2m])) by (route)
        ''',

        "error_rate": '''
        (
          sum(
            rate(app_requests_total{status=~"5.."}[2m])
          ) by (route)
          /
          sum(
            rate(app_requests_total[2m])
          ) by (route)
        )
        ''',

        "max_latency": '''
        max (
            max_over_time(
                app_request_duration_seconds_sum[5m]
            )
        ) by (route)
        ''',

        "throughput": '''
        sum(
          rate(app_request_duration_seconds_count[1m])
        ) by (route)
        '''
    }

    # ---------------------------------------------------
    # Final metrics object
    # ---------------------------------------------------

    final_metrics = {}

    # ---------------------------------------------------
    # Execute queries
    # ---------------------------------------------------

    for metric_name, query in queries.items():

        results = run_query(query)
        #print(f"Raw results for {metric_name}:", results, flush=True)

        for item in results:

            route = item["metric"].get("route")

            if not route:
                continue

            value = item["value"][1]

            try:
                value = round(float(value), 4)
            except:
                value = 0

            if route not in final_metrics:

                final_metrics[route] = {}

            final_metrics[route][metric_name] = value

    # ---------------------------------------------------
    # Fill missing metrics
    # ---------------------------------------------------

    required_metrics = [
        "p95",
        "p99",
        "avg",
        "error_rate",
        "max_latency",
        "throughput"
    ]

    #print("Raw metrics from Prometheus:", final_metrics, flush=True)

    for route in final_metrics:

        for metric in required_metrics:

            if metric not in final_metrics[route]:

                final_metrics[route][metric] = 0

    return final_metrics

# -------------------------
# SPX trigger
# -------------------------
def trigger_spx(route):
    # Enable profiling for next requests
    r.setex(f"spx:{route}", 60, 1)


# -------------------------
# Slack notification
# -------------------------
def send_slack(payload):
    try:
        requests.post(SLACK_WEBHOOK, json=payload)
    except Exception as e:
        print("Slack error:", e, flush=True)

def build_slack_payload(route, current, baseline, increase, regression):

    def fmt(value):
        try:
            return f"{float(value):.2f}"
        except:
            return "0.00"

    payload = {
        "attachments": [
            {
                "color": "#ff0000" if regression else "#36a64f",

                "title": f"🚨 Performance Alert: {route}",

                "fields": [

                    {
                        "title": "Current p95",
                        "value": f"{fmt(current)}s",
                        "short": True
                    },

                    {
                        "title": "Baseline p95",
                        "value": f"{fmt(baseline)}s",
                        "short": True
                    },

                    {
                        "title": "Increase",
                        "value": f"{fmt(increase * 100)}%",
                        "short": True
                    },

                    {
                        "title": "Regression",
                        "value": str(regression),
                        "short": True
                    }

                ],

                "footer": "Regression Service"
            }
        ]
    }

    return payload

# -------------------------
# baseline PDF report
# -------------------------
def generate_baseline_report(route, payload):

    try:

        requests.post(
            f"{REPORT_URL}/generate-baseline",
            json={
                "route": route,
                "p95": payload["p95"],
                "p99": payload["p99"],
                "avg": payload["avg"],
                "error_rate": payload["error_rate"],
                "max_latency": payload["max_latency"],
                "throughput": payload["throughput"]
            },
            timeout=5
        )

        print(f"📄 Baseline report generated for {route}")

    except Exception as e:

        print("Baseline report error:", e, flush=True)

# -------------------------
# Regression PDF report
# -------------------------
def generate_report(data):
    try:
        requests.post(f"{REPORT_URL}/generate", json=data)
    except Exception as e:
        print("Report error:", e, flush=True)


# -------------------------
# Store baseline per route
# -------------------------
@app.route("/baseline", methods=["POST"])
def baseline():
    data = request.json

    route = data["route"]

    payload = {
        "p95": data.get("p95", 0),
        "p99": data.get("p99", 0),
        "avg": data.get("avg", 0),
        "error_rate": data.get("error_rate", 0),
        "max_latency": data.get("max_latency", 0),
        "throughput": data.get("throughput", 0),
        "updated_at": int(time.time())
    }

    r.set(f"baseline:{route}", json.dumps(payload))

    generate_baseline_report(route, payload)

    return jsonify({"status": "stored", "route": route})


# -------------------------
# Alert handler (MAIN ENTRYPOINT)
# -------------------------
@app.route("/alert", methods=["POST"])
def alert():
    payload = request.json

    #print ("alert received", flush=True)
    #print (payload, flush=True)

    results = []

    for alert in payload.get("alerts", []):
        labels = alert.get("labels", {})
        route = labels.get("route")

        if not route:
            continue

        # load baseline
        baseline_raw = r.get(f"baseline:{route}")
        if not baseline_raw:
            print(f"No baseline for {route}", flush=True)
            continue

        baseline = json.loads(baseline_raw)

        if baseline["p95"] == 0:
            continue

        # current latency
        #current = query_prometheus_p95(route)

        # metrics
        #current = query_prometheus_metrics(route)
        current = query_prometheus_metrics_optimized().get(route, {})

        #print(f"Current metrics for {route}: {current}", flush=True)

        if not current:
            continue

       

        increase = (current["p95"] - baseline["p95"]) / baseline["p95"]

        is_regression = increase > 0.33

        #print(f"Route: {route}, Regression: {is_regression}", flush=True)

        if is_regression:
            result = {
                "route": route,
                "baseline": baseline["p95"],
                "current": current,
                "increase": increase,
                "regression": is_regression
            }

            results.append(result)

            # ALWAYS trigger SPX
            trigger_spx(route)

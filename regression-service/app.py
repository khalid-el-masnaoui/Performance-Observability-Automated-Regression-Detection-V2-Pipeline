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

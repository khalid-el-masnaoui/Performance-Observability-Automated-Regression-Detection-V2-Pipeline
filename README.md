# Performance Observability & Automated Regression Detection V2 Pipeline

A containerized end-to-end (almost :upside_down_face:) **performance observability and automated regression detection system** for PHP applications.

This project integrates:

- ⚡ Nginx + PHP-FPM application layer
- 📊 Prometheus metrics collection
- 📈 Grafana dashboards
- 🔥 SPX PHP profiler with flamegraphs
- 🚨 Alertmanager for alert routing
- 🤖 Custom Automated regression detection service (:snake: Python) 
- 🧪 k6 load testing for automated performance validation
- 📄 PDF report generation for baselines & regressions (:snake: Python)

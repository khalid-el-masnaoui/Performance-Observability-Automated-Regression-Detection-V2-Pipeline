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

This project is intended as a practical demo of how to wire **PHP request metrics**, **alerting**,  **dynamic profiler activation**,  **automatic regression detection** and **historical trend analysis & tracking** together into a reproducible Docker-based performance observability & automated regression detection pipeline.

## Table Of Contents

   - **[Overview](#overview)**
   - **[Architecture](#architecture)**
   - **[Project Structure](#project-structure)**
   - **[Prerequisites](#prerequisites)**
   - **[Quick Start](#quick-start)**
   - **[Endpoints & Routes](#endpoints-routes)**
      - **[Service Endpoints](#service-endpoints)**
      - **[Application routes](#application-routes)**
      - **[Metrics and profiling](#metrics-and-profiling)**
      - **[API Endpoints](#api-endpoints)**

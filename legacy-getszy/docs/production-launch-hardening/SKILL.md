---
name: production-launch-hardening
description: Comprehensive workflow for auditing GitHub repositories, assessing production readiness, executing security hardening, designing AI/load testing suites, and establishing Prometheus/Grafana monitoring strategies. Use for pre-launch reviews, code audits, infrastructure optimization, and operational observability setup.
---

# Production Launch Hardening & Audit Skill

This skill provides a structured, multi-phase methodology for taking an application from prototype to a production-ready, highly observable, and secure platform.

## Workflow Overview

1. **Repository & Architecture Audit**: Inspect project structure, modular routing, database indexing, and deployment scripts.
2. **Security Hardening**: Identify and fix hardcoded secrets, input injection vulnerabilities (e.g., MongoDB regex escaping), and authentication gaps.
3. **Performance & Load Validation**: Simulate realistic user journeys, test concurrent AI/LLM workloads, and analyze resource saturation.
4. **Operational Observability**: Deploy Prometheus, Grafana, and Node Exporter using standard templates to ensure 99.9% uptime visibility.

## References & Templates

- **Audit Framework**: See `references/audit_framework.md` for detailed evaluation criteria.
- **Prometheus Alerts Template**: See `templates/prometheus_alerts.yml` for production alerting rules.
- **Monitoring Compose Template**: See `templates/monitoring_compose.yml` for infrastructure telemetry setup.

# Signals Platform Devpost Agent — Architecture

## Security boundary

This repository is an isolated open-source competition application.

It must not contain:

- the production Signals Platform source code;
- production databases or evidence;
- customer, location, media, or observation data;
- VPS credentials or administrative endpoints;
- Grafana, Google Cloud, GitHub, or API secrets;
- private commercial modules.

## Runtime architecture

Signals Platform private backend
        |
        | Restricted read-only competition API
        v
Devpost investigation agent
        |
        +--> Gemini / Google Cloud
        |
        +--> Grafana MCP
                |
                +--> Signals Platform metrics
                +--> Signals Platform Loki logs
                +--> supporting VPS telemetry

## Initial workflow

1. Receive an operator incident question.
2. Query the restricted Signals Platform health API.
3. Query Grafana metrics and Loki logs.
4. Correlate application and infrastructure telemetry.
5. Generate a diagnosis and recommended action.
6. Return supporting dashboard and query references.

## Repository boundary

Only competition-specific integration code, synthetic demo data,
tests, deployment instructions, and documentation belong here.

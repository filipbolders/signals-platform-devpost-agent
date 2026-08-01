# Signals Platform Devpost Agent

An isolated agentic observability application for investigating
Signals Platform incidents using Gemini, Google Cloud, Grafana Cloud,
and Grafana MCP.

## Status

Phase 1: repository and security boundary.

## Core principles

- Production Signals Platform code remains private.
- Only restricted APIs are used.
- Secrets are loaded through environment variables.
- Demonstrations use synthetic or sanitised telemetry.
- No customer evidence or private operational data is committed.

## Planned workflow

The agent investigates Signals Platform incidents by combining:

- application health;
- Prometheus metrics;
- Loki logs;
- service and infrastructure telemetry;
- Gemini-based diagnosis and operator recommendations.

## Local setup

```bash
cp .env.example .env
python3 -m venv .venv
source .venv/bin/activate

Create the security policy:

```bash
cat > SECURITY.md <<'EOF'
# Security Policy

## Sensitive information

Never commit:

- API keys or access tokens;
- Google Cloud service-account credentials;
- Grafana credentials;
- production URLs containing secrets;
- customer, location, evidence, image, or video data;
- production databases;
- private Signals Platform source code.

## Reporting

Security issues should be reported privately to the repository owner
and must not be disclosed through public GitHub issues.

## Demo data

Only synthetic, anonymised, or explicitly approved demonstration data
may be included.

# Restricted API Security Boundary

## Permitted data

The Devpost API may expose only:

- service health states;
- module health states;
- aggregate request counts;
- aggregate error counts;
- aggregate latency;
- aggregate event counts;
- sanitised incident summaries;
- synthetic demonstration incidents;
- non-secret Grafana labels and dashboard paths.

## Prohibited data

The API must never expose:

- API keys, tokens, cookies, passwords, or credentials;
- customer names, emails, account IDs, or tenant identifiers;
- precise coordinates, addresses, routes, or device locations;
- evidence files, images, videos, audio, or document contents;
- original uploaded filenames;
- database rows or raw event payloads;
- internal administrative endpoints;
- filesystem paths;
- stack traces containing secrets or production paths;
- private Signals Platform source code;
- unrestricted log access;
- shell or command-execution functionality.

## Authentication

- HTTPS only outside localhost.
- Bearer token authentication.
- Separate restricted token used only by the Devpost agent.
- Token stored in an environment variable.
- No token in Git, URLs, query parameters, logs, or screenshots.
- Token rotation must be possible without restarting the production platform.

## Authorisation

The restricted token grants access only to:

- GET /api/devpost/v1/health
- GET /api/devpost/v1/modules
- GET /api/devpost/v1/incidents
- GET /api/devpost/v1/incidents/{incident_id}
- GET /api/devpost/v1/telemetry-summary
- POST /api/devpost/v1/demo/incidents when DEMO_MODE=true

It grants no access to production create, update, delete, upload,
administration, evidence, media, authentication, or user-management routes.

## Rate limits

Recommended initial limits:

- 30 requests per minute per token;
- 5 synthetic incidents per minute;
- maximum incident-list limit of 50;
- telemetry windows restricted to 5, 15, 30, or 60 minutes.

## Data retention

Synthetic Devpost incidents should be stored separately from production
incidents and may be deleted automatically after 24 hours.

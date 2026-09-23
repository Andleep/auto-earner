# Company Intelligence API for AI Agents

Machine-payable company research and due diligence over **x402 + USDC on Base**.

## What it sells

An AI agent can inspect a public company website and receive structured JSON for:

- company metadata and canonical URL
- public contact emails
- social profiles
- technology fingerprints
- DNS, MX, SPF and DMARC
- TLS and security headers
- robots.txt, sitemap.xml and llms.txt accessibility
- consolidated public-signal risk controls
- agent-ready decision reports

## Products

| Endpoint | Price | Purpose |
|---|---:|---|
| `POST /v1/company` | $0.01 | Fast company/website intelligence |
| `POST /v1/company/batch` | $0.03 | Up to 5 company URLs |
| `POST /v1/domain-intelligence` | $0.03 | DNS + TLS + security posture |
| `POST /v1/full-intelligence` | $0.05 | Full company/domain due diligence |
| `POST /v1/decision-report` | $0.10 | Consolidated agent-ready decision report |

## Agent discovery

- Base URL: https://auto-earner.onrender.com
- OpenAPI: https://auto-earner.onrender.com/openapi.json
- x402 discovery: https://auto-earner.onrender.com/.well-known/x402
- Agent card: https://auto-earner.onrender.com/.well-known/agent.json
- LLM instructions: https://auto-earner.onrender.com/llms.txt
- x402 catalog: https://auto-earner.onrender.com/.well-known/x402-catalog.json

## Payment

- x402 v2
- Base mainnet: `eip155:8453`
- USDC
- Exact pay-per-request settlement
- Pay-to wallet supplied by `PAY_TO`
- Facilitator: OpenX402

## Run locally

```bash
export PAY_TO=0x...
export PRICE_USDC=0.01
python3.13 company_api.py
```

## Render

Build: `pip install -r requirements.txt`

Start: `gunicorn --bind 0.0.0.0:$PORT company_api:app`

Health: `/health`

Required environment variable: `PAY_TO`

## Safety

The service analyzes public web signals only. Decision reports are automated screening outputs, not legal, financial, identity or security guarantees.

Unpaid requests to paid routes must return HTTP 402 with machine-readable Base USDC x402 requirements.

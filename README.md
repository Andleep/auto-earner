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

Render auto-deploy is configured for the `main` branch after GitHub CI checks pass. A successful CI run should trigger deployment automatically; confirm the resulting deployment in the Render service events.

## Safety

The service analyzes public web signals only. Decision reports are automated screening outputs, not legal, financial, identity or security guarantees.

Unpaid requests to paid routes must return HTTP 402 with machine-readable Base USDC x402 requirements.

## Best-fit buyers and workflows

Auto-Earner is intended for software agents and developers that need a compact first-pass view of a public company website or domain. It is not a substitute for authoritative company registries, a paid security audit, or professional due diligence.

- **Lead enrichment:** collect website metadata, public contact emails and social links before manual verification.
- **Vendor triage:** combine website, DNS, TLS and security-header signals to decide which vendors need deeper review.
- **Agent research pipelines:** request JSON results without an account or long-term subscription, using x402 on Base.
- **Batch screening:** submit up to five URLs in one request and inspect per-URL successes and errors.

## Buyer integration checklist

1. Read the live OpenAPI document and x402 catalogue before selecting a route.
2. Send a request without payment only to inspect the current payment challenge; an HTTP 402 is not a completed purchase.
3. Use an x402-compatible client and review the exact recipient, network, token and amount before authorizing a payment.
4. After payment, require HTTP 200 and validate the returned JSON. Keep the payment receipt/transaction evidence separately from application logs.
5. Verify important fields from primary sources. Extracted emails, technology hints and risk signals can be incomplete or misleading.

## Commercial proof and reporting

Keep these states separate in dashboards and public claims:

- **Listed:** a marketplace record exists.
- **Payable challenge:** an unpaid request returns a well-formed x402 challenge.
- **Paid fulfillment:** an authorized paid request returns the advertised product.
- **Settled revenue:** a confirmed payment reaches the configured recipient.

Do not report directory listings, unpaid probes, test transactions, or HTTP 402 challenges as customers or revenue. Marketplace verification should use a marketplace/operator-funded canary where available; never spend an owner wallet without explicit approval.

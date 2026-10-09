# Auto-Earner — Agent Buyer Quickstart

Auto-Earner provides small, structured company and domain intelligence responses for AI agents. It uses x402 micropayments in USDC on Base; no API key or subscription is required.

## Discover the service

- API home: https://auto-earner.onrender.com
- OpenAPI 3.1: https://auto-earner.onrender.com/openapi.json
- x402 resources: https://auto-earner.onrender.com/.well-known/x402
- Machine-readable pricing catalogue: https://auto-earner.onrender.com/.well-known/x402-catalog.json
- Agent card: https://auto-earner.onrender.com/.well-known/agent.json
- LLM instructions: https://auto-earner.onrender.com/llms.txt
- Health: https://auto-earner.onrender.com/health

## Choose an endpoint

| Endpoint | Price per request | Intended use |
|---|---:|---|
| `POST /v1/company` | $0.01 | Quick public company/site signals |
| `POST /v1/company/batch` | $0.03 | Check up to five URLs in one request |
| `POST /v1/domain-intelligence` | $0.03 | DNS, TLS, security and domain signals |
| `POST /v1/full-intelligence` | $0.05 | Broader company/domain screening |
| `POST /v1/decision-report` | $0.10 | Consolidated agent-oriented decision report |

Prices and payment requirements returned by the live endpoint take precedence over this document.

## Inspect the payment requirement without paying

This request intentionally does not include payment credentials. It should return HTTP `402 Payment Required` with an x402 payment challenge; it does not buy a report:

```bash
curl -i -X POST https://auto-earner.onrender.com/v1/company \
  -H 'Content-Type: application/json' \
  -d '{"url":"https://example.com"}'
```

To obtain a report, use an x402-compatible client configured for Base mainnet USDC. Review the live `PAYMENT-REQUIRED` challenge and price before authorizing a transaction. Never send a private key to this API.

## Typical agent workflow

1. Read `openapi.json` and `/.well-known/x402-catalog.json` to select a suitable endpoint and current price.
2. Use public website/domain signals to enrich a lead, prioritize manual research, or triage a vendor.
3. Treat results as preliminary signals. Verify important facts against primary sources before acting.
4. Do not treat automated risk signals as legal, financial, identity, or compliance guarantees.

## Payment

- Protocol: x402 exact
- Network: Base mainnet (`eip155:8453`)
- Asset: USDC
- Payments settle to the recipient disclosed in the live payment challenge.

## Contact / issues

For API issues, open a GitHub issue: https://github.com/Andleep/auto-earner/issues

Automated screening only. No legal, financial, identity, or compliance guarantee is provided.
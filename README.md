# Company Intelligence x402 API

Paid API for AI agents. Returns website metadata, public emails, social links, technology hints, JSON-LD count and external-link count.

## Payment
- USDC on Base mainnet
- x402 v2
- Price: $0.01 per request
- Pay-to wallet is supplied by `PAY_TO`
- Facilitator: OpenX402

## Run
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

## Paid route
`POST /v1/company`
Body: `{"url":"https://example.com"}`

An unpaid request must return HTTP 402 with Base USDC x402 requirements.

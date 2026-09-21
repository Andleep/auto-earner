from flask import Flask, request, jsonify
import urllib.request, urllib.parse, re, time, socket, ipaddress, os, threading, ssl
import dns.resolver
from html import unescape
from x402.http import HTTPFacilitatorClientSync, PaymentOption
from x402.http.middleware.flask import payment_middleware
from x402.http.types import RouteConfig
from x402.mechanisms.evm.exact import ExactEvmServerScheme
from x402.server import x402ResourceServerSync
from x402.extensions.bazaar import declare_discovery_extension, OutputConfig, bazaar_resource_server_extension

app = Flask(__name__)
MAX_BYTES = int(os.getenv("MAX_BYTES", "500000"))
TIMEOUT = int(os.getenv("FETCH_TIMEOUT", "10"))
PRICE = os.getenv("PRICE_USDC", "0.01")
BATCH_PRICE = os.getenv("BATCH_PRICE_USDC", "0.03")
DOMAIN_PRICE = os.getenv("DOMAIN_PRICE_USDC", "0.03")
FULL_PRICE = os.getenv("FULL_PRICE_USDC", "0.05")
_cache = {}
_lock = threading.Lock()

def clean(s):
    return re.sub(r"\s+", " ", unescape(s or "")).strip()

def safe_url(url):
    p = urllib.parse.urlparse(url)
    if p.scheme not in ("http", "https") or not p.hostname:
        raise ValueError("only_http_https")
    host = p.hostname.strip("[]").lower()
    if host == "localhost" or host.endswith(".local"):
        raise ValueError("private_host_blocked")
    try:
        for info in socket.getaddrinfo(host, None):
            if not ipaddress.ip_address(info[4][0]).is_global:
                raise ValueError("private_host_blocked")
    except socket.gaierror:
        raise ValueError("dns_failed")
    return url

def fetch(url):
    safe_url(url)
    req = urllib.request.Request(url, headers={"User-Agent":"Auto-Earner-Company-Intelligence/2.1"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        data = r.read(MAX_BYTES + 1)
        if len(data) > MAX_BYTES:
            raise ValueError("response_too_large")
        return data.decode("utf-8", "ignore"), r.geturl()

def extract(url):
    now = time.time()
    with _lock:
        if url in _cache and now - _cache[url][0] < 300:
            return _cache[url][1]
    html, final_url = fetch(url)
    title = re.search(r"<title[^>]*>(.*?)</title>", html, re.I | re.S)
    desc = re.search(r'<meta[^>]+(?:name|property)=["\'](?:description|og:description)["\'][^>]+content=["\'](.*?)["\']', html, re.I | re.S)
    canon = re.search(r'<link[^>]+rel=["\'][^"\']*canonical[^"\']*["\'][^>]+href=["\'](.*?)["\']', html, re.I | re.S)
    emails = sorted(set(re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", html)))[:20]
    socials = {}
    pats = {
      "linkedin": r"https?://(?:www\.)?linkedin\.com/[^\s\"'<>]+",
      "twitter": r"https?://(?:www\.)?(?:twitter\.com|x\.com)/[^\s\"'<>]+",
      "facebook": r"https?://(?:www\.)?facebook\.com/[^\s\"'<>]+",
      "instagram": r"https?://(?:www\.)?instagram\.com/[^\s\"'<>]+",
      "youtube": r"https?://(?:www\.)?(?:youtube\.com|youtu\.be)/[^\s\"'<>]+"
    }
    for k, p in pats.items():
        v = sorted(set(re.findall(p, html, re.I)))[:5]
        if v:
            socials[k] = v
    low = html.lower()
    checks = {
      "WordPress": "wp-content" in low or "wordpress" in low,
      "Shopify": "cdn.shopify.com" in low or "shopify" in low,
      "Google Analytics": "google-analytics.com" in low or "googletagmanager.com" in low,
      "Cloudflare": "cloudflare" in low,
      "Next.js": "_next/static" in low,
      "React": "react" in low,
      "Vue": "vue" in low
    }
    result = {
      "url": url,
      "final_url": final_url,
      "title": clean(title.group(1)) if title else "",
      "description": clean(desc.group(1)) if desc else "",
      "canonical": clean(canon.group(1)) if canon else "",
      "emails": emails,
      "social_links": socials,
      "technologies_hints": [k for k,v in checks.items() if v],
      "jsonld_blocks": len(re.findall(r'<script[^>]+type=["\']application/ld\+json["\']', html, re.I)),
      "external_links_count": len(set(re.findall(r'href=["\'](https?://[^"\'<>]+)', html, re.I)))
    }
    with _lock:
        _cache[url] = (now, result)
        if len(_cache) > 500:
            _cache.pop(next(iter(_cache)))
    return result

def bazaar_ext(kind):
    schemas = {
        "company": ({"url": "https://example.com"}, {"properties": {"url": {"type": "string", "format": "uri", "description": "Public company website URL to analyze"}}, "required": ["url"]}),
        "batch": ({"urls": ["https://example.com", "https://example.org"]}, {"type": "object", "properties": {"urls": {"type": "array", "maxItems": 5, "items": {"type": "string", "format": "uri"}}}, "required": ["urls"]}),
    }
    sample, schema = schemas["batch" if kind == "batch" else "company"]
    return declare_discovery_extension(input=sample, input_schema=schema, body_type="json", output=OutputConfig(example={"ok": True, "result": {}}))

def dns_intelligence(host):
    out = {"A": [], "AAAA": [], "NS": [], "MX": [], "TXT": [], "CNAME": [], "SPF": [], "DMARC": [], "errors": []}
    resolver = dns.resolver.Resolver()
    resolver.timeout = 3
    resolver.lifetime = 4
    for record in ("A", "AAAA", "NS", "MX", "TXT", "CNAME"):
        try:
            answers = resolver.resolve(host, record)
            vals = []
            for a in answers:
                vals.append(str(a).strip().rstrip("."))
            out[record] = sorted(set(vals))[:30]
        except Exception as e:
            out["errors"].append(record + ":" + type(e).__name__)
    out["SPF"] = [x for x in out["TXT"] if x.lower().startswith("v=spf1")]
    try:
        answers = resolver.resolve("_dmarc." + host, "TXT")
        out["DMARC"] = sorted(set(str(a).strip() for a in answers))[:10]
    except Exception as e:
        out["errors"].append("DMARC:" + type(e).__name__)
    return out

@app.get("/")
def home():
    return """<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Company Intelligence API for AI Agents</title><meta name="description" content="Pay-per-request company research, lead enrichment and domain due diligence for AI agents. x402 USDC on Base."><style>body{font-family:system-ui,-apple-system,sans-serif;max-width:920px;margin:auto;padding:28px;line-height:1.55;color:#17202a}h1{font-size:42px;line-height:1.05}h2{margin-top:34px}.hero{padding:24px 0}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:12px}.card{border:1px solid #ddd;border-radius:12px;padding:16px}.price{font-size:24px;font-weight:700}code,pre{background:#f4f4f4;padding:3px 6px;border-radius:5px}a{color:#0759c9}</style></head><body><section class="hero"><p>⚡ x402 • Base • USDC</p><h1>Company intelligence built for AI agents.</h1><p>Give your agent structured company and domain intelligence on demand. No subscription, no API key, pay only when an agent calls.</p></section><h2>Use cases</h2><div class="grid"><div class="card"><b>Lead enrichment</b><br>Find public contacts, social profiles and technology signals.</div><div class="card"><b>Vendor screening</b><br>Inspect company websites and domain configuration.</div><div class="card"><b>Due diligence</b><br>Combine company, DNS, TLS and security signals.</div><div class="card"><b>Agent research</b><br>Machine-readable JSON with x402 payment terms.</div></div><h2>Pay-per-call endpoints</h2><div class="grid"><div class="card"><code>POST /v1/company</code><div class="price">$0.01</div>Quick company intelligence</div><div class="card"><code>POST /v1/company/batch</code><div class="price">$0.03</div>Up to 5 companies</div><div class="card"><code>POST /v1/domain-intelligence</code><div class="price">$0.03</div>DNS + TLS + security</div><div class="card"><code>POST /v1/full-intelligence</code><div class="price">$0.05</div>Full due diligence</div></div><h2>Agent discovery</h2><p><a href="/openapi.json">OpenAPI</a> · <a href="/.well-known/x402">x402 resources</a> · <a href="/.well-known/agent.json">Agent card</a> · <a href="/llms.txt">llms.txt</a> · <a href="/.well-known/x402-catalog.json">x402 catalog</a></p><h2>Example request</h2><pre>POST /v1/company
Content-Type: application/json

{"url":"https://example.com"}</pre><p>The API responds with HTTP 402 and machine-readable x402 payment terms. After payment, the agent receives the JSON intelligence report.</p><h2>Why x402?</h2><p>Agents can discover, pay and use the service in one automated flow. This is designed for machine customers rather than a traditional human checkout.</p></body></html>""", 200, {"Content-Type":"text/html; charset=utf-8"}

@app.get("/health")
def health():
    return jsonify(ok=True, service="company-intelligence", version="4.0")

@app.post("/v1/company")
def company():
    data = request.get_json(silent=True) or {}
    url = str(data.get("url", "")).strip()
    if not url:
        return jsonify(error="url_required"), 400
    try:
        return jsonify(ok=True, result=extract(url), generated_at=int(time.time()))
    except Exception as e:
        return jsonify(ok=False, error=str(e)[:120]), 400

@app.post("/v1/company/batch")
def company_batch():
    data = request.get_json(silent=True) or {}
    urls = data.get("urls")
    if not isinstance(urls, list) or not urls:
        return jsonify(error="urls_required"), 400
    urls = [str(u).strip() for u in urls[:5] if str(u).strip()]
    if not urls:
        return jsonify(error="urls_required"), 400
    results, errors = [], []
    for url in urls:
        try:
            results.append(extract(url))
        except Exception as e:
            errors.append({"url": url, "error": str(e)[:120]})
    return jsonify(ok=True, results=results, errors=errors,
                    requested=len(urls), completed=len(results),
                    generated_at=int(time.time()))

@app.post("/v1/full-intelligence")
def full_intelligence():
    data = request.get_json(silent=True) or {}
    url = str(data.get("url", "")).strip()
    if not url:
        return jsonify(error="url_required"), 400
    try:
        parsed = urllib.parse.urlparse(safe_url(url))
        host = parsed.hostname
        base = domain_intelligence_endpoint().get_json()
        result = base.get("result", {}) if isinstance(base, dict) else {}
        result["dns"] = dns_intelligence(host)
        result["report_type"] = "full_company_domain_due_diligence"
        result["risk_signals"] = {
            "missing_https": parsed.scheme != "https",
            "missing_dmarc": not bool(result["dns"].get("DMARC")),
            "missing_spf": not bool(result["dns"].get("SPF")),
            "missing_security_headers": [k for k in ("strict-transport-security","content-security-policy","x-content-type-options","x-frame-options") if k not in result.get("domain",{}).get("security_headers",{})]
        }
        return jsonify(ok=True,result=result,generated_at=int(time.time()))
    except Exception as e:
        return jsonify(ok=False,error=str(e)[:120]),400

@app.get("/openapi.json")
def openapi():
    def paid(price, summary, schema):
        return {"post":{"summary":summary,"operationId":summary.lower().replace(" ","_"),"security":[{"x402":[]}],"x-payment-info":{"pricingMode":"fixed","price":{"mode":"fixed","currency":"USD","amount":price},"protocols":["x402"]},"requestBody":{"required":True,"content":{"application/json":{"schema":schema}}},"responses":{"402":{"description":"Payment Required","content":{"application/json":{"schema":{"type":"object"}}}},"200":{"description":"Paid JSON result","content":{"application/json":{"schema":{"type":"object"}}}}}}}
    url_schema={"type":"object","required":["url"],"properties":{"url":{"type":"string","format":"uri","description":"Public company or domain URL"}}}
    batch_schema={"type":"object","required":["urls"],"properties":{"urls":{"type":"array","maxItems":5,"items":{"type":"string","format":"uri"}}}}
    return jsonify({"openapi":"3.1.0","info":{"title":"Auto-Earner Agent Intelligence API","version":"4.0","description":"Machine-payable company, domain and due-diligence intelligence for AI agents. Returns structured JSON over x402 USDC on Base. Built for vendor screening, lead enrichment, website audits and agent workflows."},"servers":[{"url":"https://auto-earner.onrender.com"}],"paths":{
        "/v1/company":paid("0.01","Company Intelligence",url_schema),
        "/v1/company/batch":paid("0.03","Batch Company Intelligence",batch_schema),
        "/v1/domain-intelligence":paid("0.03","Domain Intelligence",url_schema),
        "/v1/full-intelligence":paid("0.05","Full Company Domain Due Diligence",url_schema)
    },"components":{"schemas":{"PaymentRequired":{"type":"object"}},"securitySchemes":{"x402":{"type":"apiKey","in":"header","name":"PAYMENT-SIGNATURE"}}},"x-discovery":{"ownershipProofs":[PAY_TO]}})

@app.get("/.well-known/402index-verify.txt")
def _402index_verify():
    return "b1624c9a5124e20ac24622b3b18c618876e7524cbf4363d8b0aade04778b7b7a\n", 200, {"Content-Type":"text/plain; charset=utf-8"}

@app.get("/.well-known/x402")
def well_known_x402():
    return jsonify({"x402Version":2,"resources":[
        {"resource":"https://auto-earner.onrender.com/v1/company","method":"POST","price":"$0.01","network":"eip155:8453","asset":"USDC","description":"Quick company website intelligence"},
        {"resource":"https://auto-earner.onrender.com/v1/company/batch","method":"POST","price":"$0.03","network":"eip155:8453","asset":"USDC","description":"Batch intelligence for up to five company URLs"},
        {"resource":"https://auto-earner.onrender.com/v1/domain-intelligence","method":"POST","price":"$0.03","network":"eip155:8453","asset":"USDC","description":"DNS, TLS, security and agent-accessibility intelligence"},
        {"resource":"https://auto-earner.onrender.com/v1/full-intelligence","method":"POST","price":"$0.05","network":"eip155:8453","asset":"USDC","description":"Full company and domain due-diligence report with risk signals"}
    ]}), 200

@app.get("/.well-known/agent.json")
def agent_card():
    return jsonify({"name":"Auto-Earner Agent Intelligence","description":"Pay-per-call company and domain intelligence for AI agents: metadata, contacts, social, technology, DNS, TLS, security headers and risk signals.","url":"https://auto-earner.onrender.com","capabilities":["company_intelligence","lead_enrichment","domain_intelligence","due_diligence","dns","security","agent_discovery"],"payment":{"protocol":"x402","network":"eip155:8453","asset":"USDC","payTo":PAY_TO},"endpoints":["/v1/company","/v1/company/batch","/v1/domain-intelligence","/v1/full-intelligence"]})

@app.get("/llms.txt")
def llms():
    return "# Auto-Earner Agent Intelligence\n\nMachine-payable company and domain due diligence for AI agents.\n\n- POST /v1/company — $0.01 quick company intelligence\n- POST /v1/company/batch — up to 5 URLs, $0.03\n- POST /v1/domain-intelligence — DNS, TLS, security and agent-accessibility report, $0.03\n- POST /v1/full-intelligence — full company/domain due diligence with risk signals, $0.05\n- GET /openapi.json — machine-readable API description\n- GET /.well-known/x402-catalog.json — x402 resource catalogue\n\nPayment: x402 exact, Base mainnet, USDC.\n", 200, {"Content-Type":"text/plain; charset=utf-8"}

@app.post("/v1/domain-intelligence")
def domain_intelligence_endpoint():
    data = request.get_json(silent=True) or {}
    url = str(data.get("url", "")).strip()
    if not url:
        return jsonify(error="url_required"), 400
    try:
        parsed = urllib.parse.urlparse(safe_url(url))
        host = parsed.hostname
        addresses = sorted(set(i[4][0] for i in socket.getaddrinfo(host, None)))
        headers = {}
        req = urllib.request.Request(url, headers={"User-Agent":"Auto-Earner-Domain-Intelligence/4.0"})
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            headers = {k.lower(): v for k,v in resp.headers.items() if k.lower() in {"server","strict-transport-security","content-security-policy","x-content-type-options","x-frame-options","referrer-policy","permissions-policy"}}
            status = resp.status
        tls = {}
        try:
            ctx = ssl.create_default_context()
            with socket.create_connection((host,443),timeout=5) as sock:
                with ctx.wrap_socket(sock,server_hostname=host) as ss:
                    tls = {"version":ss.version(),"cipher":ss.cipher()[0] if ss.cipher() else None}
        except Exception as e:
            tls = {"error":type(e).__name__}
        files = {}
        for path in ("/robots.txt","/sitemap.xml","/llms.txt"):
            try:
                with urllib.request.urlopen(urllib.request.Request(f"https://{host}{path}",headers={"User-Agent":"Auto-Earner/3.0"}),timeout=5) as resp:
                    files[path] = resp.status == 200
            except Exception:
                files[path] = False
        return jsonify(ok=True,result={"company":extract(url),"domain":{"host":host,"addresses":addresses[:20],"dns":dns_intelligence(host),"http_status":status,"security_headers":headers,"tls":tls,"public_files":files}},generated_at=int(time.time()))
    except Exception as e:
        return jsonify(ok=False,error=str(e)[:120]),400

@app.get("/.well-known/x402-catalog.json")
def x402_catalog():
    return jsonify(resources=[{"resource":"https://auto-earner.onrender.com/v1/company","method":"POST","price":PRICE,"network":"eip155:8453","currency":"USDC"},{"resource":"https://auto-earner.onrender.com/v1/company/batch","method":"POST","price":BATCH_PRICE,"network":"eip155:8453","currency":"USDC"},{"resource":"https://auto-earner.onrender.com/v1/domain-intelligence","method":"POST","price":DOMAIN_PRICE,"network":"eip155:8453","currency":"USDC"},{"resource":"https://auto-earner.onrender.com/v1/full-intelligence","method":"POST","price":FULL_PRICE,"network":"eip155:8453","currency":"USDC"}])

PAY_TO = os.getenv("PAY_TO", "")
NETWORK = "eip155:8453"
if not PAY_TO:
    raise RuntimeError("PAY_TO environment variable is required")
print("X402_BOOT_1", flush=True)
_facilitator = HTTPFacilitatorClientSync({"url": "https://facilitator.openx402.ai"})
print("X402_BOOT_2", flush=True)
_server = x402ResourceServerSync(_facilitator)
print("X402_BOOT_3", flush=True)
_server.register(NETWORK, ExactEvmServerScheme())
_server.register_extension(bazaar_resource_server_extension)
print("X402_BOOT_4", flush=True)
_routes = {
    "POST /v1/company": RouteConfig(
        accepts=[PaymentOption(scheme="exact", pay_to=PAY_TO, price="$" + PRICE, network=NETWORK)],
        description="Company website intelligence: metadata, contacts, social links and technology hints",
        extensions=bazaar_ext("company"),
        mime_type="application/json",
        service_name="Company Intelligence",
        tags=["company","lead-enrichment","due-diligence","domain"],
        resource=os.getenv("PUBLIC_URL", "https://auto-earner.onrender.com/v1/company"),
    ),
    "POST /v1/domain-intelligence": RouteConfig(
        accepts=[PaymentOption(scheme="exact", pay_to=PAY_TO, price="$" + DOMAIN_PRICE, network=NETWORK)],
        description="Full company and domain due-diligence intelligence including DNS, TLS, security headers and agent accessibility",
        extensions=bazaar_ext("company"),
        mime_type="application/json",
        service_name="Company Intelligence",
        tags=["company","lead-enrichment","due-diligence","domain"],
        resource=os.getenv("PUBLIC_URL_DOMAIN", "https://auto-earner.onrender.com/v1/domain-intelligence"),
    ),
    "POST /v1/company/batch": RouteConfig(
        accepts=[PaymentOption(scheme="exact", pay_to=PAY_TO, price="$" + BATCH_PRICE, network=NETWORK)],
        description="Batch company website intelligence for up to 5 URLs",
        extensions=bazaar_ext("batch"),
        mime_type="application/json",
        service_name="Company Intelligence",
        tags=["company","lead-enrichment","due-diligence","domain"],
        resource=os.getenv("PUBLIC_URL_BATCH", "https://auto-earner.onrender.com/v1/company/batch"),
    ),
    "POST /v1/full-intelligence": RouteConfig(
        accepts=[PaymentOption(scheme="exact", pay_to=PAY_TO, price="$" + FULL_PRICE, network=NETWORK)],
        description="Full company and domain due-diligence report with DNS, TLS, security headers and risk signals",
        extensions=bazaar_ext("company"),
        mime_type="application/json",
        service_name="Company Intelligence",
        tags=["company","lead-enrichment","due-diligence","domain"],
        resource=os.getenv("PUBLIC_URL_FULL", "https://auto-earner.onrender.com/v1/full-intelligence"),
    )
}
payment_middleware(app, routes=_routes, server=_server)

if __name__ == "__main__":
    app.run(host=os.getenv("HOST", "0.0.0.0"), port=int(os.getenv("PORT", "8765")))

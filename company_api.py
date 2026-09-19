from flask import Flask, request, jsonify
import urllib.request, urllib.parse, re, time, socket, ipaddress, os, threading
from html import unescape
from x402.http import HTTPFacilitatorClientSync, PaymentOption
from x402.http.middleware.flask import payment_middleware
from x402.http.types import RouteConfig
from x402.mechanisms.evm.exact import ExactEvmServerScheme
from x402.server import x402ResourceServerSync

app = Flask(__name__)
MAX_BYTES = int(os.getenv("MAX_BYTES", "500000"))
TIMEOUT = int(os.getenv("FETCH_TIMEOUT", "10"))
PRICE = os.getenv("PRICE_USDC", "0.01")
_cache = {}
_lock = threading.Lock()

def clean(s): return re.sub(r"\s+", " ", unescape(s or "")).strip()

def safe_url(url):
    p = urllib.parse.urlparse(url)
    if p.scheme not in ("http", "https") or not p.hostname: raise ValueError("only_http_https")
    host = p.hostname.strip("[]").lower()
    if host == "localhost" or host.endswith(".local"): raise ValueError("private_host_blocked")
    try:
        for info in socket.getaddrinfo(host, None):
            if not ipaddress.ip_address(info[4][0]).is_global: raise ValueError("private_host_blocked")
    except socket.gaierror: raise ValueError("dns_failed")
    return url

def fetch(url):
    safe_url(url)
    req = urllib.request.Request(url, headers={"User-Agent":"Auto-Earner-Company-Intelligence/2.0"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        data = r.read(MAX_BYTES + 1)
        if len(data) > MAX_BYTES: raise ValueError("response_too_large")
        return data.decode("utf-8","ignore"), r.geturl()

def extract(url):
    now=time.time()
    with _lock:
        if url in _cache and now-_cache[url][0] < 300: return _cache[url][1]
    html, final_url = fetch(url)
    title=re.search(r"<title[^>]*>(.*?)</title>",html,re.I|re.S)
    desc=re.search(r'<meta[^>]+(?:name|property)=["\'](?:description|og:description)["\'][^>]+content=["\'](.*?)["\']',html,re.I|re.S)
    canon=re.search(r'<link[^>]+rel=["\'][^"\']*canonical[^"\']*["\'][^>]+href=["\'](.*?)["\']',html,re.I|re.S)
    emails=sorted(set(re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",html)))[:20]
    socials={}
    pats={
      "linkedin":r"https?://(?:www\.)?linkedin\.com/[^\\s\"'<>]+",
      "twitter":r"https?://(?:www\.)?(?:twitter\.com|x\.com)/[^\\s\"'<>]+",
      "facebook":r"https?://(?:www\.)?facebook\.com/[^\\s\"'<>]+",
      "instagram":r"https?://(?:www\.)?instagram\.com/[^\\s\"'<>]+",
      "youtube":r"https?://(?:www\.)?(?:youtube\.com|youtu\.be)/[^\\s\"'<>]+"
    }
    for k,p in pats.items():
        v=sorted(set(re.findall(p,html,re.I)))[:5]
        if v: socials[k]=v
    low=html.lower()
    checks={"WordPress":"wp-content" in low or "wordpress" in low,"Shopify":"cdn.shopify.com" in low or "shopify" in low,"Google Analytics":"google-analytics.com" in low or "googletagmanager.com" in low,"Cloudflare":"cloudflare" in low,"Next.js":"_next/static" in low,"React":"react" in low,"Vue":"vue" in low}
    result={"url":url,"final_url":final_url,"title":clean(title.group(1)) if title else "","description":clean(desc.group(1)) if desc else "","canonical":clean(canon.group(1)) if canon else "","emails":emails,"social_links":socials,"technologies_hints":[k for k,v in checks.items() if v],"jsonld_blocks":len(re.findall(r'<script[^>]+type=["\']application/ld\\+json["\']',html,re.I)),"external_links_count":len(set(re.findall(r'href=["\'](https?://[^"\'<>]+)',html,re.I)))}
    with _lock:
        _cache[url]=(now,result)
        if len(_cache)>500: _cache.pop(next(iter(_cache)))
    return result

@app.get("/")
def home(): return jsonify(service="Auto-Earner Company Intelligence",version="2.0",status="live",price_usdc=PRICE,paid_endpoints=["/v1/company"],currency="USDC",network="Base")

@app.get("/health")
def health(): return jsonify(ok=True,service="company-intelligence")

@app.post("/v1/company")
def company():
    data=request.get_json(silent=True) or {}
    url=str(data.get("url","")).strip()
    if not url: return jsonify(error="url_required"),400
    try: return jsonify(ok=True,result=extract(url),generated_at=int(time.time()))
    except Exception as e: return jsonify(ok=False,error=str(e)[:120]),400

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
print("X402_BOOT_4", flush=True)
_routes = {
    "POST /v1/company": RouteConfig(
        accepts=[PaymentOption(scheme="exact", pay_to=PAY_TO, price="$" + PRICE, network=NETWORK)],
        description="Company website intelligence: metadata, contacts, social links and technology hints",
        mime_type="application/json",
        resource="/v1/company",
    )
}
payment_middleware(app, routes=_routes, server=_server)

if __name__=="__main__": app.run(host=os.getenv("HOST","0.0.0.0"),port=int(os.getenv("PORT","8765")))

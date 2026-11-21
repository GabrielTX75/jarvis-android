import re
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ACTIVITY = (ROOT / "app/src/main/java/com/gabriel/jarvis/MainActivity.kt").read_text(encoding="utf-8")
HTML = (ROOT / "app/src/main/assets/index.html").read_text(encoding="utf-8")
MANIFEST = (ROOT / "app/src/main/AndroidManifest.xml").read_text(encoding="utf-8")
NETWORK = (ROOT / "app/src/main/res/xml/network_security_config.xml").read_text(encoding="utf-8")
APP_JS = (ROOT / "app/src/main/assets/app.js").read_text(encoding="utf-8")


class Audit(HTMLParser):
    def __init__(self):
        super().__init__()
        self.scripts = []
        self.frames = []
        self.inline_handlers = []
        self.csp = ""

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "script":
            self.scripts.append(attrs)
        if tag in {"iframe", "frame", "object", "embed"}:
            self.frames.append(tag)
        if tag == "meta" and attrs.get("http-equiv", "").lower() == "content-security-policy":
            self.csp = attrs.get("content", "")
        self.inline_handlers.extend(
            (tag, key) for key in attrs if key.lower().startswith("on")
        )


audit = Audit()
audit.feed(HTML)

csp = audit.csp
assert csp, "CSP meta tag ausente"
assert "script-src 'self'" in csp
assert "frame-src 'none'" in csp
assert "object-src 'none'" in csp
assert "base-uri 'none'" in csp
assert "http://localhost:*" in csp and "http://127.0.0.1:*" in csp
script_policy = next(part for part in csp.split(";") if part.strip().startswith("script-src"))
assert "'unsafe-inline'" not in script_policy, "Scripts inline não devem ser autorizados"
assert "'unsafe-eval'" not in script_policy

assert len(audit.scripts) == 1 and audit.scripts[0].get("src") == "app.js", "A página deve carregar somente o JavaScript local empacotado"
assert APP_JS.strip(), "app.js não pode estar vazio"
assert not re.search(r"\beval\s*\(|\bnew\s+Function\s*\(|document\.write\s*\(", APP_JS), "JavaScript dinâmico perigoso detectado"
assert not audit.frames, "A página não deve criar frames ou objetos incorporados"
assert not audit.inline_handlers, "Atributos de evento inline não são permitidos"

assert "private fun isTrustedAssetOrigin(uri: Uri)" in ACTIVITY
assert 'uri.path == "/assets/index.html"' in ACTIVITY
assert "assetLoader.shouldInterceptRequest(uri) ?: notFoundResponse()" in ACTIVITY
assert "private fun notFoundResponse()" in ACTIVITY
assert 'if (uri.scheme == "https")' in ACTIVITY
assert 'uri.scheme == "https" || uri.scheme == "http"' not in ACTIVITY
assert "safeBrowsingEnabled = true" in ACTIVITY
assert "allowFileAccessFromFileURLs = false" in ACTIVITY
assert "allowUniversalAccessFromFileURLs = false" in ACTIVITY
assert "setAcceptThirdPartyCookies(webView, false)" in ACTIVITY

assert 'android:usesCleartextTraffic="false"' in MANIFEST
assert 'cleartextTrafficPermitted="false"' in NETWORK
assert '<domain includeSubdomains="false">localhost</domain>' in NETWORK
assert '<domain includeSubdomains="false">127.0.0.1</domain>' in NETWORK

print("WebView security static audit: OK")

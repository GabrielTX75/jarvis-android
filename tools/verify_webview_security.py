import re
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ACTIVITY = (ROOT / "app/src/main/java/com/gabriel/jarvis/MainActivity.kt").read_text(encoding="utf-8")
AI_POLICY = (ROOT / "app/src/main/java/com/gabriel/jarvis/AiEndpointPolicy.kt").read_text(encoding="utf-8")
AI_POLICY_TEST = (ROOT / "app/src/test/java/com/gabriel/jarvis/AiEndpointPolicyTest.kt").read_text(encoding="utf-8")
HTML = (ROOT / "app/src/main/assets/index.html").read_text(encoding="utf-8")
MANIFEST = (ROOT / "app/src/main/AndroidManifest.xml").read_text(encoding="utf-8")
NETWORK = (ROOT / "app/src/main/res/xml/network_security_config.xml").read_text(encoding="utf-8")
APP_JS = (ROOT / "app/src/main/assets/app.js").read_text(encoding="utf-8")
SERVICE = (ROOT / "app/src/main/java/com/gabriel/jarvis/JarvisOuvidoService.kt").read_text(encoding="utf-8")
NUCLEO = (ROOT / "app/src/main/java/com/gabriel/jarvis/NucleoJarvis.kt").read_text(encoding="utf-8")
AUDIO_POLICY = (ROOT / "app/src/main/java/com/gabriel/jarvis/AudioReadPolicy.kt").read_text(encoding="utf-8")
AUDIO_POLICY_TEST = (ROOT / "app/src/test/java/com/gabriel/jarvis/AudioReadPolicyTest.kt").read_text(encoding="utf-8")


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
assert 'private val JS_READABLE_SECRET_NAMES = setOf("busca_url", "pin_hash")' in ACTIVITY
assert "name !in JS_READABLE_SECRET_NAMES" in ACTIVITY, "Tokens e chaves de API não podem ser retornados ao JavaScript"
assert "@JavascriptInterface fun requestAI(messagesJson: String, requestId: String)" in ACTIVITY
assert "@JavascriptInterface fun searchConfigured(query: String, requestId: String)" in ACTIVITY
assert "@JavascriptInterface fun cancelSearch(requestId: String)" in ACTIVITY
assert 'setRequestProperty("X-Jarvis-Token", token)' in ACTIVITY
assert "AiEndpointPolicy.validate(baseUrl)" in ACTIVITY
assert "if (Manifest.permission.RECORD_AUDIO in faltando)" in ACTIVITY
assert "pendingBackgroundListen = true" in ACTIVITY
assert "REQ_BACKGROUND_LISTEN" in ACTIVITY
assert "@JavascriptInterface fun cancelAI(requestId: String)" in ACTIVITY
assert "connection.instanceFollowRedirects = false" in ACTIVITY
assert "ai_approved_endpoint" in ACTIVITY, "O endpoint completo precisa de aprovação nativa"
assert 'getString("ai_approved_origin"' not in ACTIVITY, "A aprovação antiga apenas por origem não pode continuar autorizando chamadas"
assert "parsed.rawQuery != null" in AI_POLICY, "Query strings devem ser recusadas para impedir credenciais na URL"
assert "parsed.rawFragment != null" in AI_POLICY, "Fragmentos devem ser recusados na URL do endpoint"
assert "parsed.rawUserInfo != null" in AI_POLICY, "Credenciais embutidas na URL devem ser recusadas"
assert "AiEndpointPolicy.validate(candidate)" in ACTIVITY
assert "AiEndpointPolicy.validate(endpoint)" in ACTIVITY
assert "normalizesHttpsHostAndDefaultPort" in AI_POLICY_TEST
assert "allowsHttpOnlyForLoopbackNames" in AI_POLICY_TEST
assert "rejectsCredentialsQueryAndFragment" in AI_POLICY_TEST
assert "approved != validatedEndpoint.normalized" in ACTIVITY, "A chamada deve conferir a URL completa aprovada"
assert "endpoint completo" in ACTIVITY, "O diálogo deve deixar claro que a aprovação cobre a URL completa"
assert "cancelAllAiRequests(\"Consulta interrompida" in ACTIVITY
assert "callbacksEnabled" in ACTIVITY
assert 'lerSegredo("ai_key")' not in APP_JS, "A chave da IA não deve ser lida pelo JavaScript"
assert 'lerSegredo("busca_token")' not in APP_JS, "O token de busca não deve ser lido pelo JavaScript"
assert 'fetch(url+"/busca?' not in APP_JS, "A busca autenticada deve passar pelo Kotlin"
assert "requestNativeSearch" in APP_JS, "A busca Android deve usar o transporte nativo"
assert "requestNativeAI(messages" in APP_JS, "Android deve usar o transporte nativo"
assert "await syncWpp()" in APP_JS, "A chamada de IA deve aguardar a aprovação do endpoint"
assert "nativeAiConfigPending=promise" in APP_JS, "A promessa de configuração deve existir antes da chamada nativa"
assert "AudioReadPolicy.decide(n)" in SERVICE
assert "AudioReadPolicy.decide(n)" in NUCLEO
assert "AudioReadDecision.RECOVER" in SERVICE and "AudioReadDecision.RECOVER" in NUCLEO
assert "Notification.VISIBILITY_PRIVATE" in SERVICE
assert 'atualizarStatus("Ouvi:' not in SERVICE, "A notificação não deve expor transcrições de voz"
assert "fun decide(readResult: Int)" in AUDIO_POLICY
assert "negativeReadResultsRequestRecorderRecovery" in AUDIO_POLICY_TEST

assert 'android:usesCleartextTraffic="false"' in MANIFEST
assert 'cleartextTrafficPermitted="false"' in NETWORK
assert '<domain includeSubdomains="false">localhost</domain>' in NETWORK
assert '<domain includeSubdomains="false">127.0.0.1</domain>' in NETWORK

print("WebView security static audit: OK")

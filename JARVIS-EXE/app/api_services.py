"""Small, dependency-free clients for the JARVIS optional APIs.

Secrets are supplied by the caller (Windows Credential Manager via keyring).
This module never persists credentials or logs request headers.
"""
import json
import urllib.error
import urllib.parse
import urllib.request


class ApiServiceError(RuntimeError):
    pass


def _request(url, *, method="GET", headers=None, payload=None, timeout=18):
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            raw = response.read(1_500_000)
            return json.loads(raw.decode("utf-8"))
    except urllib.error.HTTPError as exc:
        # Never include the URL, headers, or request body: they may contain a key.
        raise ApiServiceError("O serviço respondeu HTTP " + str(exc.code) + ". Confira a chave, a cota e tente novamente.") from None
    except urllib.error.URLError:
        raise ApiServiceError("Não foi possível conectar ao serviço. Verifique a internet.") from None
    except (TimeoutError, json.JSONDecodeError):
        raise ApiServiceError("O serviço demorou ou retornou dados inválidos.") from None


def tavily_search(api_key, query, max_results=5):
    query = str(query or "").strip()
    if not api_key:
        raise ApiServiceError("Tavily não configurada. Adicione a chave em Configurações.")
    if not query or len(query) > 400:
        raise ApiServiceError("A pesquisa precisa ter entre 1 e 400 caracteres.")
    data = _request(
        "https://api.tavily.com/search", method="POST",
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        payload={"api_key": api_key, "query": query, "max_results": max(1, min(int(max_results), 8)),
                 "search_depth": "basic", "include_answer": True},
    )
    results = []
    for item in data.get("results", []):
        if not isinstance(item, dict):
            continue
        url = str(item.get("url", ""))
        if not url.startswith(("https://", "http://")):
            continue
        results.append({
            "title": str(item.get("title", "Resultado"))[:180],
            "url": url[:1000],
            "content": str(item.get("content", ""))[:900],
            "score": item.get("score"),
        })
    return {"answer": str(data.get("answer", ""))[:1500], "results": results}


def brapi_quote(api_key, ticker):
    ticker = str(ticker or "").strip().upper()
    if not api_key:
        raise ApiServiceError("brapi não configurada. Adicione o token em Configurações.")
    if not ticker or len(ticker) > 12 or not ticker.replace(".", "").isalnum():
        raise ApiServiceError("Código de ativo inválido.")
    url = "https://brapi.dev/api/quote/" + urllib.parse.quote(ticker, safe="") + "?token=" + urllib.parse.quote(api_key, safe="")
    data = _request(url, headers={"Accept": "application/json"})
    quotes = data.get("results") or []
    if not quotes:
        raise ApiServiceError("A brapi não retornou cotação para esse código.")
    q = quotes[0]
    return {
        "symbol": str(q.get("symbol", ticker)),
        "name": str(q.get("longName") or q.get("shortName") or ticker),
        "price": q.get("regularMarketPrice"),
        "change": q.get("regularMarketChangePercent"),
        "currency": str(q.get("currency") or "BRL"),
        "updated": str(q.get("regularMarketTime") or q.get("regularMarketTimeFormatted") or ""),
        "source": "brapi",
    }


def groq_chat(api_key, model, messages, endpoint="https://api.groq.com/openai/v1/chat/completions"):
    if not api_key:
        raise ApiServiceError("Chave Groq não configurada.")
    if not endpoint.startswith("https://"):
        raise ApiServiceError("O endpoint da IA precisa usar HTTPS.")
    data = _request(endpoint, method="POST",
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + api_key},
        payload={"model": model, "messages": messages[-24:], "max_completion_tokens": 4096, "stream": False},
        timeout=90)
    answer = data["choices"][0]["message"]["content"]
    if isinstance(answer, list):
        answer = "\n".join(x.get("text", "") for x in answer if isinstance(x, dict))
    if not isinstance(answer, str) or not answer.strip():
        raise ApiServiceError("A IA retornou uma resposta vazia.")
    return answer


def gemini_chat(api_key, messages, model="gemini-2.0-flash"):
    if not api_key:
        raise ApiServiceError("Chave Gemini não configurada.")
    contents = []
    system_text = ""
    for item in messages[-24:]:
        role = item.get("role")
        if role == "system":
            system_text = str(item.get("content", ""))[:6000]
            continue
        if role not in ("user", "assistant"):
            continue
        contents.append({"role": "model" if role == "assistant" else "user",
                         "parts": [{"text": str(item.get("content", ""))[:12000]}]})
    if not contents or contents[-1]["role"] != "user":
        raise ApiServiceError("A conversa não contém uma mensagem do usuário para enviar.")
    url = "https://generativelanguage.googleapis.com/v1beta/models/" + model + ":generateContent?key=" + urllib.parse.quote(api_key, safe="")
    data = _request(url, method="POST", headers={"Content-Type": "application/json"},
                    payload={"systemInstruction": {"parts": [{"text": system_text}]} if system_text else None,
                    "contents": contents, "generationConfig": {"maxOutputTokens": 4096}}, timeout=90)
    parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
    answer = "\n".join(str(part.get("text", "")) for part in parts if isinstance(part, dict))
    if not answer.strip():
        raise ApiServiceError("O Gemini retornou uma resposta vazia.")
    return answer

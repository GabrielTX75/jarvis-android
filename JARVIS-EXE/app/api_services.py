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
        # Show the provider's useful error message without exposing URLs, headers,
        # request bodies, or credentials (Gemini keys may be in the query string).
        detail = ""
        try:
            body = json.loads(exc.read(8192).decode("utf-8", errors="replace"))
            error = body.get("error", {}) if isinstance(body, dict) else {}
            detail = str(error.get("message", "")) if isinstance(error, dict) else ""
        except Exception:
            detail = ""
        detail = " ".join(detail.split())[:240]
        code = int(exc.code)
        if code == 401:
            hint = "Chave ausente, inválida ou não autorizada."
        elif code == 403:
            hint = "Acesso negado: confira permissões do projeto, da chave e do modelo."
        elif code == 404:
            hint = "Endpoint ou modelo não encontrado; confira o identificador do modelo."
        elif code == 429:
            hint = "Limite de uso ou cota atingido; confira os limites do provedor."
        elif code >= 500:
            hint = "Falha temporária no serviço do provedor."
        else:
            hint = "O provedor recusou a solicitação."
        if detail:
            # Do not echo the credential if a provider ever includes it in an error.
            detail = detail.replace(str(headers.get("Authorization", "")).replace("Bearer ", ""), "[oculto]") if headers else detail
            raise ApiServiceError("HTTP " + str(code) + " — " + hint + " Detalhe: " + detail) from None
        raise ApiServiceError("HTTP " + str(code) + " — " + hint) from None
    except urllib.error.URLError:
        raise ApiServiceError("Não foi possível conectar ao serviço. Verifique a internet.") from None
    except (TimeoutError, json.JSONDecodeError):
        raise ApiServiceError("O serviço demorou ou retornou dados inválidos.") from None


def ollama_chat(messages, model="llama3.2:3b", endpoint="http://127.0.0.1:11434"):
    """Run a chat locally through Ollama; prompts stay on this computer."""
    endpoint = str(endpoint or "").rstrip("/")
    if not endpoint.startswith(("http://127.0.0.1", "http://localhost")):
        raise ApiServiceError("A IA local só pode usar localhost por segurança.")
    if not model or len(model) > 100:
        raise ApiServiceError("Informe um modelo Ollama válido.")
    payload_messages = []
    for item in messages[-24:]:
        role = item.get("role")
        if role in ("system", "user", "assistant"):
            payload_messages.append({"role": role, "content": str(item.get("content", ""))[:12000]})
    data = _request(endpoint + "/api/chat", method="POST",
        headers={"Content-Type": "application/json"},
        payload={"model": model, "messages": payload_messages, "stream": False},
        timeout=180)
    answer = data.get("message", {}).get("content", "")
    if not isinstance(answer, str) or not answer.strip():
        raise ApiServiceError("O Ollama respondeu sem conteúdo. Confira se o modelo foi baixado.")
    return answer


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


def gemini_chat(api_key, messages, model="gemini-3.8-flash"):
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


def chat_with_fallback(messages, *, prefer_local=False, local_model="llama3.2:3b",
                       groq_key="", groq_model="openai/gpt-oss-120b",
                       groq_endpoint="https://api.groq.com/openai/v1/chat/completions",
                       gemini_key=""):
    """Choose a provider; prefer_local is strict and never sends prompts to cloud."""
    if prefer_local:
        try:
            return ollama_chat(messages, model=local_model), "IA local (Ollama)"
        except Exception:
            raise ApiServiceError(
                "Modo somente local: o Ollama está indisponível ou o modelo não foi encontrado. "
                "Nenhuma mensagem foi enviada a provedores online. Verifique se o Ollama está "
                "em execução e se o modelo foi baixado."
            ) from None

    errors = []
    if groq_key:
        try:
            return groq_chat(groq_key, groq_model, messages, endpoint=groq_endpoint), "Groq"
        except Exception as exc:
            errors.append("Groq: " + str(exc))
    if gemini_key:
        try:
            return gemini_chat(gemini_key, messages), "Gemini (reserva)"
        except Exception as exc:
            errors.append("Gemini: " + str(exc))
    try:
        return ollama_chat(messages, model=local_model), "IA local (Ollama)"
    except Exception as exc:
        errors.append("Local: " + str(exc))
    raise ApiServiceError("Nenhuma IA respondeu. " + " ".join(errors or [
        "Configure Groq/Gemini ou instale o Ollama com um modelo local."
    ]))

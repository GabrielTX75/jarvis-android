import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))
import api_services


class FakeResponse:
    status = 200
    def __init__(self, payload):
        self.payload = json.dumps(payload).encode("utf-8")
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False
    def read(self, _limit):
        return self.payload


class ApiServiceTests(unittest.TestCase):
    @patch("api_services.urllib.request.urlopen")
    def test_tavily_search_returns_only_valid_http_results(self, mocked):
        mocked.return_value = FakeResponse({
            "answer": "Resumo de teste",
            "results": [
                {"title": "Fonte", "url": "https://example.com", "content": "Trecho"},
                {"title": "Inválido", "url": "javascript:alert(1)", "content": "x"}
            ]
        })
        result = api_services.tavily_search("private-key", "clima Recife")
        self.assertEqual(result["answer"], "Resumo de teste")
        self.assertEqual(len(result["results"]), 1)
        request = mocked.call_args.args[0]
        self.assertNotIn("private-key", request.full_url)

    @patch("api_services.urllib.request.urlopen")
    def test_brapi_quote_normalizes_quote(self, mocked):
        mocked.return_value = FakeResponse({"results": [{
            "symbol": "PETR4", "longName": "Petrobras", "regularMarketPrice": 38.5,
            "regularMarketChangePercent": 1.2, "currency": "BRL"
        }]})
        result = api_services.brapi_quote("private-token", "PETR4")
        self.assertEqual(result["symbol"], "PETR4")
        self.assertEqual(result["price"], 38.5)
        self.assertEqual(result["source"], "brapi")

    @patch("api_services.urllib.request.urlopen")
    def test_http_error_exposes_provider_message_without_credentials(self, mocked):
        import urllib.error
        error_body = json.dumps({"error": {"message": "The model is not enabled for this project"}}).encode()
        mocked.side_effect = urllib.error.HTTPError(
            "https://example.test/api?key=secret-key", 403, "Forbidden",
            {}, __import__("io").BytesIO(error_body)
        )
        with self.assertRaises(api_services.ApiServiceError) as caught:
            api_services._request(
                "https://example.test/api?key=secret-key",
                headers={"Authorization": "Bearer secret-key"}
            )
        message = str(caught.exception)
        self.assertIn("HTTP 403", message)
        self.assertIn("model is not enabled", message)
        self.assertNotIn("secret-key", message)

    @patch("api_services.urllib.request.urlopen")
    def test_groq_chat_sends_real_chat_completion_request(self, mocked):
        mocked.return_value = FakeResponse({"choices": [{
            "message": {"content": "OK"}
        }]})
        answer = api_services.groq_chat(
            "secret", "openai/gpt-oss-120b",
            [{"role": "user", "content": "Responda apenas: OK"}]
        )
        self.assertEqual(answer, "OK")
        request = mocked.call_args.args[0]
        self.assertEqual(request.full_url, "https://api.groq.com/openai/v1/chat/completions")
        self.assertEqual(request.get_header("Authorization"), "Bearer secret")

    @patch("api_services.urllib.request.urlopen")
    def test_gemini_chat_sends_real_generation_request(self, mocked):
        mocked.return_value = FakeResponse({"candidates": [{
            "content": {"parts": [{"text": "OK"}]}
        }]})
        answer = api_services.gemini_chat("secret", [
            {"role": "user", "content": "Responda apenas: OK"}
        ])
        self.assertEqual(answer, "OK")
        request = mocked.call_args.args[0]
        self.assertIn(":generateContent", request.full_url)
        self.assertEqual(request.get_method(), "POST")

    @patch("api_services.urllib.request.urlopen")
    def test_ollama_chat_uses_localhost_and_returns_response(self, mocked):
        mocked.return_value = FakeResponse({"message": {"content": "Olá local"}})
        answer = api_services.ollama_chat(
            [{"role": "user", "content": "Oi"}], model="llama3.2:3b"
        )
        self.assertEqual(answer, "Olá local")
        request = mocked.call_args.args[0]
        self.assertEqual(request.full_url, "http://127.0.0.1:11434/api/chat")
        payload = json.loads(request.data.decode("utf-8"))
        self.assertFalse(payload["stream"])
        self.assertEqual(payload["model"], "llama3.2:3b")

    def test_ollama_rejects_non_local_endpoint(self):
        with self.assertRaises(api_services.ApiServiceError):
            api_services.ollama_chat([], endpoint="https://example.com")

    def test_tavily_rejects_missing_key_and_empty_query(self):
        with self.assertRaises(api_services.ApiServiceError):
            api_services.tavily_search("", "test")
        with self.assertRaises(api_services.ApiServiceError):
            api_services.tavily_search("key", " ")

    def test_brapi_rejects_invalid_ticker(self):
        with self.assertRaises(api_services.ApiServiceError):
            api_services.brapi_quote("token", "../secrets")

    @patch("api_services.urllib.request.urlopen")
    def test_gemini_translates_chat_roles_and_system_prompt(self, mocked):
        mocked.return_value = FakeResponse({"candidates": [{
            "content": {"parts": [{"text": "Olá"}]}
        }]})
        answer = api_services.gemini_chat("secret", [
            {"role": "system", "content": "Seja útil"},
            {"role": "user", "content": "Oi"}
        ])
        self.assertEqual(answer, "Olá")
        payload = json.loads(mocked.call_args.args[0].data.decode("utf-8"))
        self.assertEqual(payload["systemInstruction"]["parts"][0]["text"], "Seja útil")
        self.assertEqual(payload["contents"][0]["role"], "user")


    def test_local_only_mode_never_falls_back_to_cloud(self):
        with patch("api_services.ollama_chat", side_effect=api_services.ApiServiceError("offline")) as local, \
             patch("api_services.groq_chat") as groq, \
             patch("api_services.gemini_chat") as gemini:
            with self.assertRaises(api_services.ApiServiceError) as caught:
                api_services.chat_with_fallback(
                    [{"role": "user", "content": "mensagem privada"}],
                    prefer_local=True,
                    groq_key="configured-but-must-not-be-used",
                    gemini_key="configured-but-must-not-be-used",
                )
        self.assertIn("somente local", str(caught.exception))
        self.assertIn("Nenhuma mensagem foi enviada", str(caught.exception))
        local.assert_called_once()
        groq.assert_not_called()
        gemini.assert_not_called()

    def test_local_only_mode_uses_ollama_without_cloud_fallback(self):
        with patch("api_services.ollama_chat", return_value="Resposta local") as local, \
             patch("api_services.groq_chat") as groq, \
             patch("api_services.gemini_chat") as gemini:
            answer, provider = api_services.chat_with_fallback(
                [{"role": "user", "content": "Oi"}], prefer_local=True
            )
        self.assertEqual((answer, provider), ("Resposta local", "IA local (Ollama)"))
        local.assert_called_once()
        groq.assert_not_called()
        gemini.assert_not_called()

    def test_cloud_mode_keeps_groq_then_gemini_then_local_fallback_order(self):
        with patch("api_services.groq_chat", side_effect=api_services.ApiServiceError("quota")), \
             patch("api_services.gemini_chat", return_value="Resposta Gemini") as gemini, \
             patch("api_services.ollama_chat") as local:
            answer, provider = api_services.chat_with_fallback(
                [{"role": "user", "content": "Oi"}],
                groq_key="configured",
                gemini_key="configured",
            )
        self.assertEqual((answer, provider), ("Resposta Gemini", "Gemini (reserva)"))
        gemini.assert_called_once()
        local.assert_not_called()



if __name__ == "__main__":
    unittest.main()

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


if __name__ == "__main__":
    unittest.main()

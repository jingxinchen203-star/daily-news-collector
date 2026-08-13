import unittest

from news_common import parse_json_response, render_report_sections, safe_url


class NewsCommonTests(unittest.TestCase):
    def test_parse_plain_json(self):
        self.assertEqual(parse_json_response('{"alert": true, "infections": 42}')["infections"], 42)

    def test_parse_fenced_json(self):
        value = parse_json_response('```json\n{"alert": false}\n```')
        self.assertFalse(value["alert"])

    def test_escape_report_html(self):
        rendered = render_report_sections('【疫情概况】<script>alert(1)</script>')
        self.assertNotIn('<script>', rendered)
        self.assertIn('&lt;script&gt;', rendered)

    def test_reject_unsafe_urls(self):
        self.assertEqual(safe_url('javascript:alert(1)'), '#')
        self.assertEqual(safe_url('https://example.com/news'), 'https://example.com/news')


if __name__ == '__main__':
    unittest.main()


class LlmFallbackTests(unittest.TestCase):
    def test_provider_fallback(self):
        import os
        from unittest.mock import patch
        from news_common import Settings, call_llm

        settings = Settings("", "deepseek-key", "openai-key", "", "mail-pass", "a@example.com", "b@example.com")
        calls = []

        def fake_completion(url, key, model, prompt, *, max_tokens, temperature):
            calls.append(key)
            if key == "deepseek-key":
                raise RuntimeError("quota exhausted")
            return "fallback response"

        with patch.dict(os.environ, {"AI_FALLBACK_PROVIDERS": "deepseek,openai"}, clear=False), patch("news_common._chat_completion", side_effect=fake_completion):
            self.assertEqual(call_llm(settings, "hello"), "fallback response")
        self.assertEqual(calls, ["deepseek-key", "openai-key"])

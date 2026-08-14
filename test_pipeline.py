import os
import unittest
from unittest.mock import patch

from news_sources import fetch_articles


class NewsPipelineTests(unittest.TestCase):
    def test_fetch_articles_deduplicates_by_url_and_applies_limit(self):
        articles = [
            {"title": "same", "url": "https://example.com/same"},
            {"title": "replacement", "url": "https://example.com/same"},
            {"title": "other", "url": "https://example.com/other"},
        ]
        with patch("news_sources.fetch_rss_feed", return_value=articles):
            with patch.dict(os.environ, {"NEWS_RSS_URLS": "https://example.com/feed"}, clear=False):
                result = fetch_articles(page_size=1)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["title"], "replacement")

    def test_fetch_articles_keeps_healthy_sources_when_one_rss_feed_fails(self):
        def fake_feed(url, *, since):
            if url.endswith("bad"):
                raise ValueError("invalid feed")
            return [{"title": "healthy", "url": "https://example.com/healthy"}]

        with patch("news_sources.fetch_rss_feed", side_effect=fake_feed):
            with patch.dict(
                os.environ,
                {"NEWS_RSS_URLS": "https://example.com/bad,https://example.com/good"},
                clear=False,
            ):
                result = fetch_articles(page_size=20)
        self.assertEqual([item["title"] for item in result], ["healthy"])

    def test_fetch_articles_raises_when_all_sources_fail(self):
        with patch("news_sources.fetch_rss_feed", side_effect=ValueError("invalid feed")):
            with patch.dict(os.environ, {"NEWS_RSS_URLS": "https://example.com/bad"}, clear=False):
                with self.assertRaisesRegex(RuntimeError, "所有新闻源均失败"):
                    fetch_articles(page_size=20)


if __name__ == "__main__":
    unittest.main()

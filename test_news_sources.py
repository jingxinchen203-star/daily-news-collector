import unittest

from news_sources import parse_feed


class NewsSourceTests(unittest.TestCase):
    def test_parse_rss_feed(self):
        xml = b'''<rss version="2.0"><channel><item><title>Outbreak update</title><description>Ten cases.</description><link>https://example.org/news/1</link><pubDate>Wed, 13 Aug 2026 08:00:00 GMT</pubDate></item></channel></rss>'''
        articles = parse_feed(xml, "https://example.org/feed.xml")
        self.assertEqual(len(articles), 1)
        self.assertEqual(articles[0]["title"], "Outbreak update")
        self.assertEqual(articles[0]["source"]["name"], "example.org")

    def test_parse_atom_feed(self):
        xml = b'''<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Atom update</title><link href="https://example.org/news/2"/><summary>Summary</summary></entry></feed>'''
        articles = parse_feed(xml, "https://example.org/atom.xml")
        self.assertEqual(len(articles), 1)
        self.assertEqual(articles[0]["url"], "https://example.org/news/2")


if __name__ == "__main__":
    unittest.main()

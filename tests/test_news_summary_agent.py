import pytest

from news_summary_agent import SummaryError, extract_article, summarize_extractive, validate_url


HTML = """
<!doctype html>
<html>
  <head><title>Fallback title</title><meta property="og:title" content="Market update"/></head>
  <body>
    <article>
      <h1>Ignored after og title</h1>
      <p>The central bank announced a new policy package today after weeks of market volatility.</p>
      <p>Officials said the measure is designed to support liquidity while inflation remains above target.</p>
      <p>Analysts expect the decision to influence borrowing costs and investor sentiment this quarter.</p>
    </article>
  </body>
</html>
"""


def test_validate_url_accepts_http_url():
    assert validate_url("https://example.com/news") == "https://example.com/news"


def test_validate_url_rejects_non_http_url():
    with pytest.raises(SummaryError):
        validate_url("file:///etc/passwd")


def test_extract_article_prefers_metadata_title():
    article = extract_article("https://example.com/news", HTML)

    assert article.title == "Market update"
    assert "central bank announced" in article.text
    assert "Analysts expect" in article.text


def test_extractive_summary_includes_source_and_bullets():
    article = extract_article("https://example.com/news", HTML)
    summary = summarize_extractive(article, max_words=80)

    assert "Tieu de: Market update" in summary
    assert "Nguon: https://example.com/news" in summary
    assert "- The central bank announced" in summary

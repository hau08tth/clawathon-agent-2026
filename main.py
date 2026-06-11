from datetime import datetime, timezone

from dotenv import load_dotenv
from greennode_agentbase import GreenNodeAgentBaseApp, PingStatus, RequestContext

from news_summary_agent import SummaryError, fetch_article, summarize_article


load_dotenv()

app = GreenNodeAgentBaseApp()


@app.entrypoint
def handler(payload: dict, context: RequestContext) -> dict:
    """Summarize a news page from a URL.

    Expected payload:
      {"url": "https://example.com/news.html", "language": "vi", "max_words": 500}
    """
    url = payload.get("url") or payload.get("message")
    language = payload.get("language", "vi")
    max_words = int(payload.get("max_words", 500))

    try:
        article = fetch_article(url)
        summary = summarize_article(article, language=language, max_words=max_words)
    except (SummaryError, TypeError, ValueError) as exc:
        return {
            "status": "error",
            "error": str(exc),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "request_id": context.request_id,
        }

    return {
        "status": "success",
        "title": article.title,
        "url": article.url,
        "summary": summary,
        "summary_mode": "llm" if _uses_llm() else "extractive",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "session_id": context.session_id,
        "request_id": context.request_id,
    }


@app.ping
def health_check() -> PingStatus:
    return PingStatus.HEALTHY


def _uses_llm() -> bool:
    import os

    return all(os.environ.get(name) for name in ("LLM_BASE_URL", "LLM_API_KEY", "LLM_MODEL"))


if __name__ == "__main__":
    app.run(port=8080, host="0.0.0.0")

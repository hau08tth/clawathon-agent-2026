import os
import re
from dataclasses import dataclass
from typing import Iterable
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup


USER_AGENT = (
    "Mozilla/5.0 (compatible; ClawathonNewsSummaryAgent/1.0; "
    "+https://github.com/hau08tth/clawathon-agent-2026)"
)


@dataclass
class Article:
    url: str
    title: str
    text: str


class SummaryError(ValueError):
    """Raised when a URL cannot be fetched or summarized."""


def validate_url(url: str) -> str:
    parsed = urlparse((url or "").strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise SummaryError("Payload must include a valid http(s) URL.")
    return parsed.geturl()


def fetch_article(url: str, timeout_seconds: float = 15.0) -> Article:
    url = validate_url(url)
    try:
        response = httpx.get(
            url,
            timeout=timeout_seconds,
            follow_redirects=True,
            headers={"User-Agent": USER_AGENT},
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise SummaryError(f"Cannot fetch URL: {exc}") from exc

    content_type = response.headers.get("content-type", "")
    if "text/html" not in content_type and "application/xhtml" not in content_type:
        raise SummaryError(f"URL did not return an HTML page: {content_type or 'unknown'}")

    return extract_article(url=str(response.url), html=response.text)


def extract_article(url: str, html: str) -> Article:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg", "iframe", "form"]):
        tag.decompose()

    title = _first_text(
        [
            _meta_content(soup, "property", "og:title"),
            _meta_content(soup, "name", "twitter:title"),
            soup.title.string if soup.title and soup.title.string else "",
            _selector_text(soup, "h1"),
        ]
    )

    content_root = (
        soup.find("article")
        or soup.find("main")
        or soup.find(attrs={"role": "main"})
        or soup.body
        or soup
    )
    paragraphs = [
        normalize_whitespace(node.get_text(" ", strip=True))
        for node in content_root.find_all(["p", "h2", "h3", "li"])
    ]
    text = "\n".join(part for part in paragraphs if len(part) >= 35)
    if not text:
        text = normalize_whitespace(content_root.get_text(" ", strip=True))

    if len(text) < 120:
        raise SummaryError("Could not extract enough article text from the page.")

    return Article(url=url, title=title or "Untitled article", text=text)


def summarize_article(article: Article, language: str = "vi", max_words: int = 500) -> str:
    if _llm_is_configured():
        return summarize_with_llm(article, language=language, max_words=max_words)
    return summarize_extractive(article, max_words=max_words)


def summarize_with_llm(article: Article, language: str = "vi", max_words: int = 500) -> str:
    base_url = os.environ["LLM_BASE_URL"].rstrip("/")
    api_key = os.environ["LLM_API_KEY"]
    model = os.environ["LLM_MODEL"]
    prompt_language = "Vietnamese" if language.lower().startswith("vi") else language
    source = article.text[:12000]

    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You summarize news articles accurately. Keep names, dates, "
                    "numbers, and caveats. Do not invent facts."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Summarize this news article in {prompt_language} in one page "
                    f"(maximum {max_words} words). Include: headline, key points, "
                    "context, and why it matters.\n\n"
                    f"URL: {article.url}\nTitle: {article.title}\n\n{source}"
                ),
            },
        ],
        "temperature": 0.2,
    }
    try:
        response = httpx.post(
            f"{base_url}/chat/completions",
            timeout=45,
            headers={"Authorization": f"Bearer {api_key}"},
            json=payload,
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()
    except (httpx.HTTPError, KeyError, IndexError) as exc:
        raise SummaryError(f"LLM summarization failed: {exc}") from exc


def summarize_extractive(article: Article, max_words: int = 500) -> str:
    sentences = split_sentences(article.text)
    picked = []
    word_count = 0
    for sentence in sentences:
        words = sentence.split()
        if len(words) < 8:
            continue
        if word_count + len(words) > max_words:
            break
        picked.append(sentence)
        word_count += len(words)
        if len(picked) >= 10:
            break

    if not picked:
        picked = [article.text[: max_words * 6].strip()]

    return "\n".join(
        [
            f"Tieu de: {article.title}",
            f"Nguon: {article.url}",
            "",
            "Tom tat:",
            *[f"- {sentence}" for sentence in picked],
        ]
    )


def split_sentences(text: str) -> list[str]:
    clean = normalize_whitespace(text)
    return [part.strip() for part in re.split(r"(?<=[.!?。！？])\s+", clean) if part.strip()]


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _llm_is_configured() -> bool:
    return all(os.environ.get(name) for name in ("LLM_BASE_URL", "LLM_API_KEY", "LLM_MODEL"))


def _meta_content(soup: BeautifulSoup, attr: str, value: str) -> str:
    tag = soup.find("meta", attrs={attr: value})
    content = tag.get("content") if tag else ""
    return normalize_whitespace(content)


def _selector_text(soup: BeautifulSoup, selector: str) -> str:
    tag = soup.select_one(selector)
    return normalize_whitespace(tag.get_text(" ", strip=True)) if tag else ""


def _first_text(values: Iterable[str]) -> str:
    for value in values:
        cleaned = normalize_whitespace(value)
        if cleaned:
            return cleaned
    return ""

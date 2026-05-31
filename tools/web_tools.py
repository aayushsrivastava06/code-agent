"""
Web tools — search the web, fetch pages, download files.
Uses only free/open services: DuckDuckGo for search, requests for fetch.
"""

import re
import json
import urllib.request
import urllib.parse
import urllib.error
import ssl
from pathlib import Path
from typing import Optional

from .registry import registry, ToolDefinition


def _get(url: str, headers: dict = None, timeout: int = 15) -> tuple[str, int]:
    """Simple HTTP GET, no external deps required."""
    req_headers = {
        "User-Agent": "Mozilla/5.0 (compatible; CodeAgent/1.0)",
        "Accept": "text/html,application/json,*/*",
    }
    if headers:
        req_headers.update(headers)
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(url, headers=req_headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            data = resp.read()
            charset = "utf-8"
            ct = resp.headers.get_content_charset()
            if ct:
                charset = ct
            return data.decode(charset, errors="replace"), resp.status
    except urllib.error.HTTPError as e:
        return f"HTTP Error {e.code}: {e.reason}", e.code
    except urllib.error.URLError as e:
        return f"URL Error: {e.reason}", 0
    except Exception as e:
        return f"Error: {e}", 0


def _strip_html(html: str) -> str:
    text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.S | re.I)
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.S | re.I)
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"&amp;", "&", text)
    text = re.sub(r"&lt;", "<", text)
    text = re.sub(r"&gt;", ">", text)
    text = re.sub(r"&quot;", '"', text)
    text = re.sub(r"&#39;", "'", text)
    text = re.sub(r"&\w+;", "", text)
    text = re.sub(r"\s{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def web_search(query: str, max_results: int = 10) -> str:
    try:
        encoded = urllib.parse.quote(query)
        url = f"https://html.duckduckgo.com/html/?q={encoded}"
        html, status = _get(url)
        if status == 0 or "Error" in html[:100]:
            url2 = f"https://duckduckgo.com/?q={encoded}&ia=web"
            html, status = _get(url2)

        results = []
        pattern = re.compile(
            r'<a[^>]+class="[^"]*result__a[^"]*"[^>]*href="([^"]*)"[^>]*>(.*?)</a>',
            re.S | re.I
        )
        snippet_pattern = re.compile(
            r'<a[^>]+class="[^"]*result__snippet[^"]*"[^>]*>(.*?)</a>',
            re.S | re.I
        )

        links = pattern.findall(html)
        snippets = [_strip_html(s) for s in snippet_pattern.findall(html)]

        seen = set()
        for i, (href, title) in enumerate(links):
            if href.startswith("//duckduckgo") or href.startswith("/?"):
                continue
            if href in seen:
                continue
            seen.add(href)
            clean_title = _strip_html(title).strip()
            snippet = snippets[i] if i < len(snippets) else ""
            results.append(f"{len(results)+1}. {clean_title}\n   {href}\n   {snippet[:200]}")
            if len(results) >= max_results:
                break

        if not results:
            results.append("(No structured results found — try fetch_url with the search URL directly)")
            results.append(f"URL tried: {url}")

        return f"Web search: '{query}'\n\n" + "\n\n".join(results)
    except Exception as e:
        return f"Error searching: {e}"


def fetch_url(url: str, extract_text: bool = True, max_chars: int = 8000) -> str:
    try:
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        content, status = _get(url)
        if status not in (200, 0) and status > 0:
            return f"Error: HTTP {status}\n{content[:500]}"

        content_type_guess = "html" if "<html" in content[:1000].lower() else "text"

        if extract_text and content_type_guess == "html":
            text = _strip_html(content)
        elif content.strip().startswith("{") or content.strip().startswith("["):
            try:
                parsed = json.loads(content)
                text = json.dumps(parsed, indent=2)
            except Exception:
                text = content
        else:
            text = content

        if len(text) > max_chars:
            text = text[:max_chars] + f"\n\n[Truncated — {len(text)} total chars. Increase max_chars or use more specific fetch.]"

        return f"URL: {url}\nStatus: {status if status else 'OK'}\n\n{text}"
    except Exception as e:
        return f"Error fetching {url}: {e}"


def download_file(url: str, destination: str, workspace: str = ".") -> str:
    try:
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        dest_path = Path(workspace) / destination if not Path(destination).is_absolute() else Path(destination)
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        urllib.request.urlretrieve(url, dest_path)
        size = dest_path.stat().st_size
        return f"Downloaded {url} → {destination} ({size/1024:.1f}KB)"
    except Exception as e:
        return f"Error downloading {url}: {e}"


def check_url(url: str) -> str:
    try:
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        _, status = _get(url, timeout=10)
        if status in range(200, 400):
            return f"✓ URL accessible: {url} (HTTP {status})"
        elif status == 0:
            return f"✗ URL unreachable: {url}"
        else:
            return f"⚠ URL returned HTTP {status}: {url}"
    except Exception as e:
        return f"Error checking URL: {e}"


def register_web_tools(workspace_getter):
    def ws():
        return workspace_getter()

    tools = [
        ToolDefinition(
            name="web_search",
            description=(
                "Search the web using DuckDuckGo (free, no API key needed). "
                "Returns titles, URLs, and snippets for top results."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "max_results": {"type": "integer", "description": "Max results to return", "default": 10},
                },
                "required": ["query"],
            },
            handler=lambda query, max_results=10: web_search(query, max_results),
            category="web",
        ),
        ToolDefinition(
            name="fetch_url",
            description=(
                "Fetch and read the contents of a webpage or API endpoint. "
                "Automatically strips HTML tags to return clean text. "
                "Works for documentation, GitHub, Stack Overflow, etc."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL to fetch"},
                    "extract_text": {"type": "boolean", "description": "Strip HTML and return clean text", "default": True},
                    "max_chars": {"type": "integer", "description": "Max characters to return", "default": 8000},
                },
                "required": ["url"],
            },
            handler=lambda url, extract_text=True, max_chars=8000: fetch_url(url, extract_text, max_chars),
            category="web",
        ),
        ToolDefinition(
            name="download_file",
            description="Download a file from a URL and save it to disk.",
            input_schema={
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL to download from"},
                    "destination": {"type": "string", "description": "Local file path to save to"},
                },
                "required": ["url", "destination"],
            },
            handler=lambda url, destination: download_file(url, destination, ws()),
            category="web",
        ),
        ToolDefinition(
            name="check_url",
            description="Check if a URL is accessible and get its HTTP status code.",
            input_schema={
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL to check"},
                },
                "required": ["url"],
            },
            handler=lambda url: check_url(url),
            category="web",
        ),
    ]
    for tool in tools:
        registry.register(tool)

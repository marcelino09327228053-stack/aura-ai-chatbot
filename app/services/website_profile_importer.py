"""Safely extract readable company information from a public webpage."""

from __future__ import annotations

import ipaddress
import socket
import time
from html.parser import HTMLParser
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlsplit, urlunsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


MAX_RESPONSE_BYTES = 2_000_000
MAX_REDIRECTS = 4
MAX_IMPORT_PAGES = 15
ALLOWED_PORTS = {None, 80, 443}
REQUEST_TIMEOUT_SECONDS = 25
RETRY_DELAYS_SECONDS = (0, 1.0, 2.5)
IMPORTANT_LINK_TERMS = {
    "about": 100,
    "about-us": 100,
    "company": 95,
    "products": 90,
    "product": 85,
    "services": 90,
    "service": 85,
    "projects": 80,
    "project": 75,
    "contact": 70,
    "contact-us": 70,
    "pricing": 65,
    "price": 60,
    "faq": 55,
    "support": 50,
    "hours": 68,
    "opening-hours": 68,
    "locations": 68,
    "location": 65,
    "branches": 65,
    "mission": 64,
    "vision": 64,
    "values": 62,
    "policies": 61,
    "policy": 60,
    "warranty": 61,
    "returns": 61,
    "refund": 61,
    "leadership": 59,
    "management": 58,
    "team": 55,
    "board": 54,
    "investor-relations": 58,
    "investors": 57,
    "certifications": 54,
    "accreditations": 54,
    "awards": 52,
    "partners": 51,
    "clients": 51,
    "careers": 48,
    "jobs": 47,
}

PROFILE_INFORMATION_CATEGORIES = {
    "company overview": ("about us", "our company", "company overview", "who we are"),
    "products or services": ("products", "services", "what we offer", "solutions"),
    "contact details": ("contact us", "email", "phone", "telephone", "mailto:"),
    "address or locations": ("address", "location", "branches", "head office", "office at"),
    "business hours": ("business hours", "opening hours", "office hours", "monday", "mon-fri"),
    "pricing": ("pricing", "price list", "rates", "packages", "₱", "$"),
    "mission, vision or values": ("mission", "vision", "core values", "our values"),
    "policies or support": ("policy", "warranty", "returns", "refund", "customer support"),
    "leadership or team": ("leadership", "management team", "board of directors", "our team"),
    "investor relations": ("investor relations", "shareholders", "annual report"),
    "certifications or awards": ("certification", "accreditation", "awards", "recognized by"),
    "partners or clients": ("partners", "our clients", "customers", "collaborators"),
    "careers": ("careers", "job openings", "join our team", "vacancies"),
    "social or messaging channels": ("facebook.com", "instagram.com", "linkedin.com", "youtube.com", "tiktok.com", "wa.me"),
}
CORE_INFORMATION_CATEGORIES = {
    "company overview",
    "products or services",
    "contact details",
    "address or locations",
}


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        return None


class _ReadableHTMLParser(HTMLParser):
    useful_tags = {"title", "h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "address", "td"}
    ignored_tags = {"script", "style", "nav", "footer", "header", "form", "svg", "noscript", "template"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._ignored_depth = 0
        self._capture_depth = 0
        self._buffer: list[str] = []
        self.lines: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:  # noqa: ANN001
        tag = tag.lower()
        if tag in self.ignored_tags:
            self._ignored_depth += 1
        elif not self._ignored_depth and tag in self.useful_tags:
            self._capture_depth += 1

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in self.ignored_tags and self._ignored_depth:
            self._ignored_depth -= 1
            return
        if not self._ignored_depth and tag in self.useful_tags and self._capture_depth:
            self._capture_depth -= 1
            if not self._capture_depth:
                text = " ".join("".join(self._buffer).split())
                self._buffer.clear()
                if len(text) >= 2:
                    self.lines.append(text)

    def handle_data(self, data: str) -> None:
        if not self._ignored_depth and self._capture_depth:
            self._buffer.append(data)


class _ImportantLinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._href = ""
        self._text: list[str] = []
        self.links: list[tuple[str, str]] = []

    def handle_starttag(self, tag: str, attrs) -> None:  # noqa: ANN001
        if tag.lower() != "a":
            return
        self._href = next((value for name, value in attrs if name.lower() == "href" and value), "")
        self._text = []

    def handle_data(self, data: str) -> None:
        if self._href:
            self._text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a" and self._href:
            self.links.append((self._href, " ".join("".join(self._text).split())))
            self._href = ""
            self._text = []


class _PublicContactLinkParser(HTMLParser):
    social_hosts = {
        "facebook.com", "www.facebook.com", "instagram.com", "www.instagram.com",
        "linkedin.com", "www.linkedin.com", "youtube.com", "www.youtube.com",
        "tiktok.com", "www.tiktok.com", "x.com", "twitter.com", "wa.me",
    }

    def __init__(self, base_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.channels: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:  # noqa: ANN001
        if tag.lower() != "a":
            return
        href = next((value for name, value in attrs if name.lower() == "href" and value), "").strip()
        lower = href.casefold()
        if lower.startswith(("mailto:", "tel:")):
            self.channels.append(href)
            return
        absolute = urljoin(self.base_url, href)
        if (urlsplit(absolute).hostname or "").casefold() in self.social_hosts:
            self.channels.append(absolute)


def _validated_public_url(value: str) -> str:
    raw = value.strip()
    if not raw:
        raise ValueError("Paste a public website link first.")
    if "://" not in raw:
        raw = "https://" + raw
    parsed = urlsplit(raw)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("Only public HTTP or HTTPS website links are supported.")
    if parsed.username or parsed.password:
        raise ValueError("Website links containing usernames or passwords are not allowed.")
    try:
        port = parsed.port
    except ValueError as exc:
        raise ValueError("The website link has an invalid port.") from exc
    if port not in ALLOWED_PORTS:
        raise ValueError("Only standard public website ports are allowed.")
    try:
        addresses = socket.getaddrinfo(parsed.hostname, port or (443 if parsed.scheme == "https" else 80))
    except socket.gaierror as exc:
        raise ValueError("The website address could not be found.") from exc
    for address in addresses:
        ip = ipaddress.ip_address(address[4][0])
        if not ip.is_global:
            raise ValueError("Private, local, or restricted network links are not allowed.")
    return parsed.geturl()


def _candidate_urls(url: str) -> list[str]:
    """Return safe connection fallbacks without changing the requested path."""
    validated = _validated_public_url(url)
    parsed = urlsplit(validated)
    hostname = parsed.hostname or ""
    hosts = [hostname]
    if hostname.startswith("www."):
        hosts.append(hostname[4:])
    else:
        hosts.append("www." + hostname)

    candidates: list[str] = []
    for scheme, host in (
        (parsed.scheme, hosts[0]),
        (parsed.scheme, hosts[1]),
        ("http", hosts[0]),
        ("http", hosts[1]),
    ):
        port = parsed.port
        if port in {80, 443}:
            port = None
        netloc = host if port is None else f"{host}:{port}"
        candidate = urlunsplit((scheme, netloc, parsed.path or "/", parsed.query, ""))
        if candidate not in candidates:
            candidates.append(candidate)
    return candidates


def _download_once(url: str) -> tuple[str, str]:
    opener = build_opener(_NoRedirect())
    current = _validated_public_url(url)
    for _ in range(MAX_REDIRECTS + 1):
        request = Request(
            current,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/140.0 Safari/537.36"
                ),
                "Accept": "text/html,text/plain;q=0.9",
                "Accept-Language": "en-US,en;q=0.9",
                "Connection": "close",
            },
        )
        try:
            response = opener.open(request, timeout=REQUEST_TIMEOUT_SECONDS)
        except HTTPError as exc:
            if exc.code in {301, 302, 303, 307, 308} and exc.headers.get("Location"):
                current = _validated_public_url(urljoin(current, exc.headers["Location"]))
                continue
            raise RuntimeError(f"The website returned HTTP {exc.code}.") from exc
        except URLError as exc:
            raise RuntimeError("The public website could not be reached.") from exc
        content_type = response.headers.get_content_type()
        if content_type not in {"text/html", "text/plain"}:
            raise ValueError("The link does not point to a readable webpage.")
        declared_length = response.headers.get("Content-Length")
        if declared_length and int(declared_length) > MAX_RESPONSE_BYTES:
            raise ValueError("The webpage is too large to import.")
        chunks: list[bytes] = []
        payload_size = 0
        try:
            while payload_size <= MAX_RESPONSE_BYTES:
                chunk = response.read(min(8192, MAX_RESPONSE_BYTES + 1 - payload_size))
                if not chunk:
                    break
                chunks.append(chunk)
                payload_size += len(chunk)
        except (TimeoutError, socket.timeout):
            # Some older public sites stream a complete page very slowly and never
            # close the connection promptly. Keep enough already-received HTML.
            if payload_size < 1024:
                raise RuntimeError("The website timed out before sending readable content.")
        payload = b"".join(chunks)
        if len(payload) > MAX_RESPONSE_BYTES:
            raise ValueError("The webpage is too large to import.")
        charset = response.headers.get_content_charset() or "utf-8"
        return payload.decode(charset, errors="replace"), current
    raise RuntimeError("The website redirected too many times.")


def _download_public_html(url: str) -> tuple[str, str]:
    """Download a slow/intermittent public site using browser-like retries."""
    candidates = _candidate_urls(url)
    failures: list[str] = []
    for candidate_index, candidate in enumerate(candidates):
        # Retry the exact address most often. Fallback variants get one attempt
        # so a broken site cannot hold the request open indefinitely.
        delays = RETRY_DELAYS_SECONDS if candidate_index == 0 else (0,)
        for delay in delays:
            if delay:
                time.sleep(delay)
            try:
                return _download_once(candidate)
            except (RuntimeError, ValueError) as exc:
                failures.append(f"{candidate}: {exc}")

    last_error = failures[-1].split(": ", 1)[-1] if failures else "Connection failed."
    raise RuntimeError(
        "The website could not be imported after several connection attempts. "
        f"Last result: {last_error}"
    )


def _extract_profile_text(html: str, base_url: str = "https://public.example/") -> str:
    parser = _ReadableHTMLParser()
    parser.feed(html)
    unique: list[str] = []
    seen: set[str] = set()
    for line in parser.lines:
        key = " ".join(line.casefold().split())
        if key in seen:
            continue
        seen.add(key)
        unique.append(line)
    contact_parser = _PublicContactLinkParser(base_url)
    contact_parser.feed(html)
    for channel in contact_parser.channels:
        key = channel.casefold().rstrip("/")
        if key not in seen:
            seen.add(key)
            unique.append(f"PUBLIC CONTACT CHANNEL: {channel}")
    text = "\n\n".join(unique).strip()
    if len(text) < 80:
        raise ValueError("Not enough public company information was found on this page.")
    return text[:50_000]


def _normalized_host(url: str) -> str:
    host = (urlsplit(url).hostname or "").casefold()
    return host[4:] if host.startswith("www.") else host


def _discover_important_links(html: str, base_url: str) -> list[str]:
    parser = _ImportantLinkParser()
    parser.feed(html)
    base_host = _normalized_host(base_url)
    ranked: dict[str, int] = {}
    for href, label in parser.links:
        absolute = urljoin(base_url, href)
        parsed = urlsplit(absolute)
        if parsed.scheme not in {"http", "https"} or _normalized_host(absolute) != base_host:
            continue
        if parsed.path.casefold().endswith((".pdf", ".jpg", ".jpeg", ".png", ".gif", ".zip", ".doc", ".docx")):
            continue
        searchable = f"{parsed.path} {label}".casefold().replace("_", "-").replace(" ", "-")
        score = max((weight for term, weight in IMPORTANT_LINK_TERMS.items() if term in searchable), default=0)
        if not score:
            continue
        # Prefer main menu pages over deep category/detail pages. The primary
        # Products page usually summarizes its subcategories, leaving crawl
        # capacity for Projects, Contact, Pricing, and FAQ.
        path_depth = len([part for part in parsed.path.split("/") if part])
        score -= max(0, path_depth - 1) * 25
        clean = urlunsplit((parsed.scheme, parsed.netloc, parsed.path or "/", parsed.query, ""))
        if clean.rstrip("/") == base_url.rstrip("/"):
            continue
        ranked[clean] = max(score, ranked.get(clean, 0))
    return [url for url, _ in sorted(ranked.items(), key=lambda item: (-item[1], item[0]))]


def _combine_profile_pages(pages: list[tuple[str, str]]) -> str:
    combined: list[str] = []
    seen: set[str] = set()
    for page_url, html in pages:
        try:
            page_text = _extract_profile_text(html, page_url)
        except ValueError:
            continue
        page_name = urlsplit(page_url).path.strip("/").replace("-", " ").replace("_", " ") or "Home"
        page_lines: list[str] = []
        for line in page_text.split("\n\n"):
            key = " ".join(line.casefold().split())
            if not key or key in seen:
                continue
            seen.add(key)
            page_lines.append(line)
        if page_lines:
            combined.append(f"SOURCE PAGE: {page_name.title()}\n" + "\n\n".join(page_lines))
    result = "\n\n".join(combined).strip()
    if len(result) < 80:
        raise ValueError("Not enough public company information was found on this website.")
    return result[:100_000]


def _profile_completeness(text: str) -> dict[str, bool]:
    normalized = " ".join(text.casefold().split())
    return {
        category: any(marker.casefold() in normalized for marker in markers)
        for category, markers in PROFILE_INFORMATION_CATEGORIES.items()
    }


def import_public_website_profile(url: str) -> dict:
    home_html, final_url = _download_public_html(url)
    pages: list[tuple[str, str]] = [(final_url, home_html)]
    imported_urls = {final_url.rstrip("/")}
    candidate_links = _discover_important_links(home_html, final_url)
    for page_url in candidate_links:
        if len(pages) >= MAX_IMPORT_PAGES:
            break
        try:
            page_html, resolved_url = _download_public_html(page_url)
        except (RuntimeError, ValueError):
            # One slow or broken menu page should not discard the pages that
            # were already imported successfully.
            continue
        key = resolved_url.rstrip("/")
        if key in imported_urls:
            continue
        imported_urls.add(key)
        pages.append((resolved_url, page_html))
        current_profile = _combine_profile_pages(pages)
        completeness = _profile_completeness(current_profile)
        found_count = sum(completeness.values())
        core_complete = all(completeness[name] for name in CORE_INFORMATION_CATEGORIES)
        # Do not keep requesting pages for facts a company may not publish.
        # Once core details plus several optional categories are present, the
        # remaining missing items are reported to the user instead.
        if len(pages) >= 5 and core_complete and found_count >= 8:
            break
    extracted_profile = _combine_profile_pages(pages)
    completeness = _profile_completeness(extracted_profile)
    return {
        "url": final_url,
        "extracted_profile": extracted_profile,
        "pages_imported": [page_url for page_url, _ in pages],
        "information_found": [name for name, found in completeness.items() if found],
        "information_missing": [name for name, found in completeness.items() if not found],
    }

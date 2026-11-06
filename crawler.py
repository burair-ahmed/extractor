"""
High-Speed Asynchronous Domain Crawler
Traverses internal pages of target websites prioritizing contact, about, and team pages
to extract all reachable email addresses while respecting domain boundaries.
"""

import asyncio
import re
import urllib.parse
from bs4 import BeautifulSoup
import httpx
from typing import Set, Dict, List, Optional, Callable, Any, Tuple
from extractor import extract_emails_from_html, select_primary_email

CONTACT_PATH_KEYWORDS = [
    "contact", "contact-us", "contactus", "about", "about-us", "team",
    "our-team", "staff", "reach", "reach-us", "touch", "get-in-touch",
    "support", "help", "imprint", "impressum", "legal", "privacy",
    "location", "locations", "office", "offices", "connect", "info", "people"
]

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)


def normalize_root_url(raw_url: str) -> str:
    """Ensures URL starts with http/https scheme and has valid structure."""
    raw_url = raw_url.strip()
    if not raw_url:
        return ""
    if not re.match(r"^https?://", raw_url, re.IGNORECASE):
        raw_url = "https://" + raw_url
    return raw_url


def get_domain_root(url: str) -> str:
    """Extracts base network location (e.g., example.com)."""
    parsed = urllib.parse.urlparse(url)
    netloc = parsed.netloc.lower()
    if ":" in netloc:
        netloc = netloc.split(":")[0]
    return netloc


def is_same_domain(url: str, base_domain: str) -> bool:
    """Checks if a URL belongs to the base domain (or www variant)."""
    domain = get_domain_root(url)
    clean_base = base_domain.replace("www.", "")
    clean_domain = domain.replace("www.", "")
    return clean_domain == clean_base or clean_domain.endswith("." + clean_base)


def score_link_priority(url: str, anchor_text: str = "") -> int:
    """
    Scores an internal link based on likelihood of containing contact information.
    Higher score = crawled earlier.
    """
    score = 0
    lower_url = url.lower()
    lower_text = anchor_text.lower()

    for kw in CONTACT_PATH_KEYWORDS:
        if kw in lower_url:
            score += 15
        if kw in lower_text:
            score += 10

    # Slight penalty for very long URLs or query-heavy URLs
    if len(lower_url) > 80:
        score -= 2
    if "?" in lower_url:
        score -= 2

    return score


class WebsiteResult:
    def __init__(self, target_url: str):
        self.target_url = target_url
        self.primary_email: str = ""
        self.all_emails: List[str] = []
        self.email_sources: Dict[str, str] = {}  # email -> page_url where found
        self.pages_scanned: int = 0
        self.status: str = "Pending"
        self.visited_pages: List[str] = []
        self.error_message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "target_url": self.target_url,
            "primary_email": self.primary_email,
            "all_emails": ", ".join(self.all_emails) if self.all_emails else "None",
            "all_emails_list": self.all_emails,
            "email_sources": self.email_sources,
            "pages_scanned": self.pages_scanned,
            "status": self.status,
            "visited_pages": self.visited_pages,
            "error_message": self.error_message,
        }


class DomainCrawler:
    def __init__(
        self,
        target_url: str,
        max_pages: int = 25,
        timeout: float = 12.0,
        progress_callback: Optional[Callable[[Dict[str, Any]], Any]] = None,
    ):
        self.raw_target = target_url
        self.target_url = normalize_root_url(target_url)
        self.base_domain = get_domain_root(self.target_url)
        self.max_pages = max(1, max_pages)
        self.timeout = timeout
        self.progress_callback = progress_callback
        self.visited: Set[str] = set()
        self.result = WebsiteResult(self.target_url)
        self.cancelled = False

    def cancel(self):
        self.cancelled = True

    async def _notify(self, event_type: str, details: Dict[str, Any]):
        if self.progress_callback:
            try:
                payload = {
                    "event": event_type,
                    "target_url": self.target_url,
                    "base_domain": self.base_domain,
                    **details
                }
                if asyncio.iscoroutinefunction(self.progress_callback):
                    await self.progress_callback(payload)
                else:
                    self.progress_callback(payload)
            except Exception:
                pass

    async def crawl(self, client: Optional[httpx.AsyncClient] = None) -> WebsiteResult:
        if not self.target_url or not self.base_domain:
            self.result.status = "Invalid URL"
            self.result.error_message = "URL could not be parsed."
            return self.result

        should_close_client = False
        if client is None:
            headers = {"User-Agent": DEFAULT_USER_AGENT, "Accept-Language": "en-US,en;q=0.9"}
            client = httpx.AsyncClient(
                headers=headers,
                timeout=httpx.Timeout(self.timeout),
                follow_redirects=True,
                verify=False  # Avoid failure on corporate/self-signed certs
            )
            should_close_client = True

        queue: List[Tuple[int, str]] = [(100, self.target_url)]
        enqueued: Set[str] = {self.target_url}

        discovered_emails: Set[str] = set()

        try:
            while queue and len(self.visited) < self.max_pages and not self.cancelled:
                # Sort queue so highest priority URLs are popped first
                queue.sort(key=lambda x: x[0], reverse=True)
                score, current_url = queue.pop(0)

                # Canonicalize page URL
                clean_url = current_url.split("#")[0].rstrip("/")
                if clean_url in self.visited:
                    continue

                self.visited.add(clean_url)
                self.result.pages_scanned += 1
                self.result.visited_pages.append(current_url)

                await self._notify("page_start", {
                    "current_page": current_url,
                    "pages_scanned": self.result.pages_scanned,
                    "emails_found_count": len(discovered_emails),
                })

                # Fetch HTML
                html_text = ""
                try:
                    resp = await client.get(current_url)
                    if resp.status_code == 200:
                        content_type = resp.headers.get("content-type", "").lower()
                        # Only parse HTML pages
                        if "text/html" in content_type or not content_type:
                            html_text = resp.text
                except Exception as exc:
                    # Ignore individual page failures
                    pass

                if not html_text:
                    continue

                # Extract emails from this page
                new_emails = extract_emails_from_html(html_text, current_url)
                for email in new_emails:
                    if email not in discovered_emails:
                        discovered_emails.add(email)
                        self.result.email_sources[email] = current_url
                        await self._notify("email_found", {
                            "email": email,
                            "source_page": current_url,
                            "emails_count": len(discovered_emails),
                        })

                # Discover new internal links
                if len(self.visited) < self.max_pages:
                    soup = BeautifulSoup(html_text, "lxml")
                    for a_tag in soup.find_all("a", href=True):
                        raw_href = a_tag.get("href", "").strip()
                        if not raw_href or raw_href.startswith(("#", "javascript:", "tel:", "sms:", "mailto:")):
                            continue

                        # Resolve relative links
                        full_link = urllib.parse.urljoin(current_url, raw_href)
                        clean_link = full_link.split("#")[0].rstrip("/")

                        if clean_link not in self.visited and clean_link not in enqueued:
                            if is_same_domain(clean_link, self.base_domain):
                                anchor_text = a_tag.get_text(strip=True)
                                link_score = score_link_priority(clean_link, anchor_text)
                                queue.append((link_score, clean_link))
                                enqueued.add(clean_link)

            # Finalize Result
            self.result.all_emails = sorted(list(discovered_emails))
            if self.result.all_emails:
                self.result.primary_email = select_primary_email(self.result.all_emails, self.base_domain)
                self.result.status = "Success"
            else:
                self.result.status = "No Email Found"

        except Exception as e:
            self.result.status = "Failed"
            self.result.error_message = str(e)
        finally:
            if should_close_client:
                await client.aclose()

        await self._notify("site_completed", {
            "primary_email": self.result.primary_email,
            "all_emails": self.result.all_emails,
            "status": self.result.status,
            "pages_scanned": self.result.pages_scanned,
        })

        return self.result


async def crawl_batch_websites(
    urls: List[str],
    max_pages_per_site: int = 25,
    max_concurrent_sites: int = 4,
    timeout: float = 12.0,
    progress_callback: Optional[Callable[[Dict[str, Any]], Any]] = None,
) -> List[WebsiteResult]:
    """Crawls a batch of websites concurrently with semaphore rate limiting."""
    semaphore = asyncio.Semaphore(max_concurrent_sites)
    results: List[WebsiteResult] = []

    headers = {"User-Agent": DEFAULT_USER_AGENT, "Accept-Language": "en-US,en;q=0.9"}
    async with httpx.AsyncClient(
        headers=headers,
        timeout=httpx.Timeout(timeout),
        follow_redirects=True,
        verify=False
    ) as shared_client:
        async def crawl_single(target_url: str):
            async with semaphore:
                crawler = DomainCrawler(
                    target_url=target_url,
                    max_pages=max_pages_per_site,
                    timeout=timeout,
                    progress_callback=progress_callback
                )
                res = await crawler.crawl(client=shared_client)
                results.append(res)
                return res

        tasks = [crawl_single(u) for u in urls if u.strip()]
        await asyncio.gather(*tasks, return_exceptions=True)

    return results

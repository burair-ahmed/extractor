"""
Google My Business (GMB) / Google Maps Extractor Module
High-performance scraper using Playwright to extract complete local business profiles
including Business Name, Category, Phone, Website, Address, Rating, Reviews, Maps URL,
and operating hours, with sub-area grid expansion for exhaustive crawling.
"""

import asyncio
import re
import sys
import threading
import urllib.parse
from typing import Dict, List, Optional, Callable, Any, Set
from dataclasses import dataclass, field, asdict
from playwright.async_api import async_playwright, Browser, BrowserContext, Page


@dataclass
class GMBBusinessProfile:
    place_id: str = ""
    business_name: str = ""
    category: str = ""
    phone: str = ""
    website: str = ""
    primary_email: str = ""
    all_emails: List[str] = field(default_factory=list)
    address: str = ""
    rating: str = ""
    reviews_count: str = ""
    operating_status: str = ""
    maps_url: str = ""
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    social_links: List[str] = field(default_factory=list)
    scraped_at: str = ""
    source_query: str = ""

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        if isinstance(d.get("all_emails"), list):
            d["all_emails_str"] = ", ".join(d["all_emails"])
        return d


class GMBExtractor:
    """
    Asynchronous Google Maps scraper leveraging Playwright to extract
    business listings from search queries.
    """

    def __init__(
        self,
        niche: str,
        location: str,
        max_results: int = 200,
        exhaustive_mode: bool = False,
        enrich_emails: bool = True,
        on_log: Optional[Callable[[str, str], Any]] = None,
        on_profile_found: Optional[Callable[[Dict[str, Any]], Any]] = None,
        cancel_token: Optional[asyncio.Event] = None,
    ):
        self.niche = niche.strip()
        self.location = location.strip()
        self.max_results = max(1, max_results)
        self.exhaustive_mode = exhaustive_mode
        self.enrich_emails = enrich_emails
        self.on_log = on_log or (lambda msg, lvl="info": None)
        self.on_profile_found = on_profile_found or (lambda p: None)
        self.cancel_token = cancel_token or asyncio.Event()

        self.scraped_profiles: Dict[str, GMBBusinessProfile] = {}
        self.visited_urls: Set[str] = set()

    def _log(self, message: str, level: str = "info"):
        try:
            self.on_log(message, level)
        except Exception:
            pass

    def _generate_queries(self) -> List[str]:
        """
        Generates search query variants. In exhaustive mode, expands location
        into directional quadrants or sub-areas to bypass Google's 120-item cap.
        """
        base_query = f"{self.niche} in {self.location}"
        if not self.exhaustive_mode:
            return [base_query]

        # Multi-zone directional sub-queries to uncover all profiles in the targeted area
        sub_zones = [
            f"{self.niche} in {self.location}",
            f"{self.niche} in Downtown {self.location}",
            f"{self.niche} in North {self.location}",
            f"{self.niche} in South {self.location}",
            f"{self.niche} in East {self.location}",
            f"{self.niche} in West {self.location}",
            f"{self.niche} in Central {self.location}",
            f"best {self.niche} in {self.location}",
        ]
        return sub_zones

    async def _handle_consent(self, page: Page):
        """Dismiss Google cookies/privacy consent dialogs if present."""
        try:
            consent_btn = page.locator(
                'button:has-text("Accept all"), button:has-text("I agree"), form[action*="consent"] button'
            )
            if await consent_btn.count() > 0:
                await consent_btn.first.click(timeout=3000)
                self._log("Dismissed Google consent overlay.", "info")
                await page.wait_for_timeout(1000)
        except Exception:
            pass

    async def _extract_card_info(self, card_element) -> Optional[GMBBusinessProfile]:
        """
        Parses a single Google Maps result card in the feed.
        """
        try:
            # 1. Main anchor / maps URL / Name
            link_el = card_element.locator('a.hfpxzc, a[href*="/maps/place/"]')
            if await link_el.count() == 0:
                return None

            maps_url = await link_el.first.get_attribute("href") or ""
            business_name = await link_el.first.get_attribute("aria-label") or ""

            if not business_name:
                name_el = card_element.locator('div.qBF1Pd, div.fontHeadlineSmall')
                if await name_el.count() > 0:
                    business_name = (await name_el.first.inner_text()).strip()

            if not business_name:
                return None

            # Deduplication key using place ID or normalized name
            place_id_match = re.search(r"!1s([^!]+)", maps_url)
            place_id = place_id_match.group(1) if place_id_match else f"{business_name}_{maps_url[:60]}"

            # 2. Rating & Reviews
            rating = ""
            reviews_count = ""
            rating_el = card_element.locator('span.MW4etd')
            if await rating_el.count() > 0:
                rating = (await rating_el.first.inner_text()).strip()

            reviews_el = card_element.locator('span.UY7F9')
            if await reviews_el.count() > 0:
                reviews_text = (await reviews_el.first.inner_text()).strip()
                reviews_count = reviews_text.replace("(", "").replace(")", "").replace(",", "").strip()

            # 3. Text lines container (category, address, status, phone)
            full_card_text = (await card_element.inner_text()) or ""
            lines = [l.strip() for l in full_card_text.split("\n") if l.strip()]

            category = ""
            phone = ""
            address = ""
            operating_status = ""

            # Extract phone using regex
            phone_match = re.search(
                r'(\+?\d{1,3}[-.\s]?)?(\(?\d{2,4}\)?[-.\s]?)?\d{3,4}[-.\s]?\d{3,4}',
                full_card_text
            )
            if phone_match:
                possible_phone = phone_match.group(0).strip()
                # Ensure it's not just a year or 4-digit number
                digits_only = re.sub(r'\D', '', possible_phone)
                if len(digits_only) >= 7:
                    phone = possible_phone

            # Extract website link from card action buttons
            website = ""
            web_el = card_element.locator('a[data-value="Website"], a[aria-label*="website" i], a.lcr4fd')
            if await web_el.count() > 0:
                raw_href = await web_el.first.get_attribute("href") or ""
                if raw_href:
                    # Resolve google redirect URL if needed: /url?q=https://...
                    if "/url?q=" in raw_href:
                        parsed = urllib.parse.parse_qs(urllib.parse.urlparse(raw_href).query)
                        website = parsed.get("q", [raw_href])[0]
                    else:
                        website = raw_href

            # Parse lines for category and address
            # Typically line 0 is Name, line 1 is Rating/Reviews, line 2 is Category · Address
            for line in lines[1:]:
                if "·" in line:
                    parts = [p.strip() for p in line.split("·") if p.strip()]
                    if parts and not category:
                        category = parts[0]
                    if len(parts) > 1 and not address:
                        # Find address segment
                        for p in parts[1:]:
                            if any(c.isdigit() for c in p) or any(
                                word in p.lower() for word in ["st", "ave", "rd", "blvd", "dr", "suite", "hwy"]
                            ):
                                address = p
                                break
                if any(kw in line.lower() for kw in ["open", "closed", "hours", "closes"]):
                    if not operating_status:
                        operating_status = line

            # Coordinates from maps_url: @32.7767,-96.7970,14z
            lat, lng = None, None
            coords_match = re.search(r'@(-?\d+\.\d+),(-?\d+\.\d+)', maps_url)
            if coords_match:
                lat = float(coords_match.group(1))
                lng = float(coords_match.group(2))

            profile = GMBBusinessProfile(
                place_id=place_id,
                business_name=business_name,
                category=category or self.niche,
                phone=phone,
                website=website,
                address=address or self.location,
                rating=rating,
                reviews_count=reviews_count,
                operating_status=operating_status,
                maps_url=maps_url,
                latitude=lat,
                longitude=lng,
                source_query=f"{self.niche} in {self.location}",
            )
            return profile

        except Exception as e:
            return None

    async def _scrape_single_query(self, page: Page, query: str):
        """
        Executes Google Maps search for a single query string, continuously
        scrolling the results feed until max_results or end of list.
        """
        search_url = f"https://www.google.com/maps/search/{urllib.parse.quote_plus(query)}?hl=en"
        self._log(f"Navigating to Google Maps: '{query}'", "info")

        try:
            await page.goto(search_url, wait_until="domcontentloaded", timeout=45000)
            await self._handle_consent(page)
        except Exception as e:
            self._log(f"Navigation warning: {e}", "warning")

        # Wait for feed or single business profile
        feed_selector = 'div[role="feed"]'
        try:
            await page.wait_for_selector(feed_selector, timeout=12000)
        except Exception:
            # Check if Google routed directly to a single business profile view
            if "/maps/place/" in page.url:
                self._log("Google Maps matched single specific place directly.", "info")
                try:
                    title_el = page.locator('h1.DUwDvf, h1.fontHeadlineLarge')
                    name = (await title_el.first.inner_text()).strip() if await title_el.count() > 0 else ""
                    if name:
                        profile = GMBBusinessProfile(
                            place_id=page.url[:60],
                            business_name=name,
                            category=self.niche,
                            maps_url=page.url,
                            address=self.location,
                        )
                        if profile.place_id not in self.scraped_profiles:
                            self.scraped_profiles[profile.place_id] = profile
                            self.on_profile_found(profile.to_dict())
                except Exception:
                    pass
                return

            self._log(f"No result feed found for query '{query}'. Moving to next.", "warning")
            return

        feed = page.locator(feed_selector)
        prev_card_count = 0
        no_growth_cycles = 0
        scroll_attempts = 0

        self._log(f"Found active Google Maps feed. Starting automated infinite scroll...", "info")

        while len(self.scraped_profiles) < self.max_results and not self.cancel_token.is_set():
            # Query all cards currently in DOM
            cards = page.locator('div[role="feed"] > div:has(a[href*="/maps/place/"])')
            current_card_count = await cards.count()

            # Process newly loaded cards
            for i in range(current_card_count):
                if self.cancel_token.is_set() or len(self.scraped_profiles) >= self.max_results:
                    break

                try:
                    card = cards.nth(i)
                    profile = await self._extract_card_info(card)
                    if profile and profile.place_id not in self.scraped_profiles:
                        # Avoid duplicates
                        norm_key = f"{profile.business_name.lower().strip()}_{profile.phone}"
                        if norm_key not in self.visited_urls:
                            self.visited_urls.add(norm_key)
                            self.scraped_profiles[profile.place_id] = profile
                            self.on_profile_found(profile.to_dict())
                            self._log(
                                f"Discovered #{len(self.scraped_profiles)}: {profile.business_name} ({profile.category}) - Phone: {profile.phone or 'N/A'}",
                                "success"
                            )
                except Exception:
                    continue

            if len(self.scraped_profiles) >= self.max_results:
                self._log(f"Target count of {self.max_results} profiles reached.", "success")
                break

            # Check if feed reached end
            end_markers = page.locator(
                'span:has-text("You\'ve reached the end of the list"), p:has-text("You\'ve reached the end")'
            )
            if await end_markers.count() > 0:
                self._log("Google Maps end-of-list sentinel reached.", "info")
                break

            # Scroll feed down
            try:
                await feed.evaluate("node => node.scrollBy(0, 1800)")
            except Exception:
                await page.evaluate("window.scrollBy(0, 1800)")

            scroll_attempts += 1
            await asyncio.sleep(1.2)

            # Check for stall/end of feed
            new_card_count = await cards.count()
            if new_card_count == prev_card_count:
                no_growth_cycles += 1
                if no_growth_cycles >= 4:
                    self._log(f"Feed reached bottom or exhausted after {scroll_attempts} scroll batches.", "info")
                    break
            else:
                no_growth_cycles = 0
                prev_card_count = new_card_count

    async def run(self) -> List[Dict[str, Any]]:
        """
        Main runner: Launches headless browser, executes queries, harvests profiles,
        and optionally enriches with contact emails from websites.
        """
        queries = self._generate_queries()
        self._log(f"Initiating GMB extraction for '{self.niche}' in '{self.location}' ({len(queries)} query zones)...", "info")

        async with async_playwright() as p:
            browser: Browser = await p.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                ]
            )

            context: BrowserContext = await browser.new_context(
                viewport={"width": 1366, "height": 768},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
                locale="en-US",
                timezone_id="America/New_York",
            )

            page: Page = await context.new_page()

            for idx, q in enumerate(queries, start=1):
                if self.cancel_token.is_set() or len(self.scraped_profiles) >= self.max_results:
                    break
                self._log(f"[Zone {idx}/{len(queries)}] Searching query: '{q}'", "info")
                try:
                    await self._scrape_single_query(page, q)
                except Exception as e:
                    self._log(f"Error during query '{q}': {e}", "warning")

            await context.close()
            await browser.close()

        results_list = [p.to_dict() for p in self.scraped_profiles.values()]
        self._log(f"Google Maps phase completed. Total profiles harvested: {len(results_list)}", "success")

        # Step 2: Website Email Deep Extraction Enrichment
        if self.enrich_emails and results_list and not self.cancel_token.is_set():
            await self._enrich_emails_from_websites(results_list)

        return results_list

    async def _enrich_emails_from_websites(self, results_list: List[Dict[str, Any]]):
        """
        Iterates over discovered businesses with a website and uses DomainCrawler
        to extract owner/contact emails and social profiles directly.
        """
        websites_to_crawl = [
            (idx, r) for idx, r in enumerate(results_list)
            if r.get("website") and str(r["website"]).startswith("http")
        ]

        if not websites_to_crawl:
            self._log("No valid websites found to crawl for emails.", "info")
            return

        self._log(f"Starting Email Enrichment for {len(websites_to_crawl)} business websites...", "info")

        from crawler import DomainCrawler

        semaphore = asyncio.Semaphore(4)

        async def enrich_single(idx: int, profile: Dict[str, Any]):
            if self.cancel_token.is_set():
                return
            async with semaphore:
                url = profile["website"]
                try:
                    self._log(f"Scanning website for emails: {profile['business_name']} ({url})", "info")
                    crawler = DomainCrawler(
                        target_url=url,
                        max_pages=8,
                        timeout=10.0
                    )
                    res = await crawler.crawl()
                    if res.all_emails:
                        profile["primary_email"] = res.primary_email
                        profile["all_emails"] = res.all_emails
                        profile["all_emails_str"] = ", ".join(res.all_emails)
                        self._log(
                            f"Discovered email for '{profile['business_name']}': {res.primary_email}",
                            "success"
                        )
                        self.on_profile_found(profile)
                except Exception as e:
                    pass

        tasks = [enrich_single(idx, r) for idx, r in websites_to_crawl]
        await asyncio.gather(*tasks, return_exceptions=True)
        self._log("Email enrichment completed for all business websites.", "success")


def run_gmb_in_thread(
    niche: str,
    location: str,
    max_results: int,
    exhaustive_mode: bool,
    enrich_emails: bool,
    main_loop: asyncio.AbstractEventLoop,
    emit_event_fn: Callable[[Dict[str, Any]], Any],
    cancel_event: threading.Event,
) -> List[Dict[str, Any]]:
    """
    Runs GMBExtractor inside an isolated thread with its own ProactorEventLoop on Windows.
    This guarantees that Playwright's subprocess launch works cleanly even when Uvicorn
    runs with --reload (which forces SelectorEventLoop on Windows).
    """
    if sys.platform == "win32":
        thread_loop = asyncio.ProactorEventLoop()
    else:
        thread_loop = asyncio.new_event_loop()

    asyncio.set_event_loop(thread_loop)

    profiles_registry: Dict[str, Dict[str, Any]] = {}

    def handle_log(msg: str, level: str = "info"):
        try:
            main_loop.call_soon_threadsafe(
                emit_event_fn,
                {"type": "log", "message": msg, "level": level}
            )
        except Exception:
            pass

    def handle_profile(profile_dict: Dict[str, Any]):
        try:
            place_id = profile_dict.get("place_id") or profile_dict.get("business_name")
            profiles_registry[place_id] = profile_dict
            total_p = len(profiles_registry)
            total_e = sum(1 for p in profiles_registry.values() if p.get("primary_email"))

            main_loop.call_soon_threadsafe(
                emit_event_fn,
                {
                    "type": "gmb_profile_found",
                    "profile": profile_dict,
                    "total_profiles": total_p,
                    "total_emails": total_e
                }
            )
        except Exception:
            pass

    extractor = GMBExtractor(
        niche=niche,
        location=location,
        max_results=max_results,
        exhaustive_mode=exhaustive_mode,
        enrich_emails=enrich_emails,
        on_log=handle_log,
        on_profile_found=handle_profile,
        cancel_token=cancel_event
    )

    try:
        results = thread_loop.run_until_complete(extractor.run())
        return results
    finally:
        try:
            thread_loop.close()
        except Exception:
            pass



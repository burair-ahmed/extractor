"""
High-Precision Email Extractor Module
Extracts emails from HTML content, raw text, mailto links, Cloudflare obfuscation,
HTML entities, contact form attributes, and script tags.
"""

import re
import html
import base64
import urllib.parse
from bs4 import BeautifulSoup
from typing import Set, Dict, List, Optional, Tuple, Any

# Common false positives, asset extensions, and placeholder domains
IGNORED_EXTENSIONS = {
    "png", "jpg", "jpeg", "gif", "svg", "webp", "ico", "bmp", "tiff",
    "css", "js", "woff", "woff2", "ttf", "eot", "mp4", "mp3", "pdf", "zip"
}

DUMMY_EMAIL_PATTERNS = [
    r"^example@",
    r"^user@",
    r"^yourname@",
    r"^name@",
    r"^test@",
    r"^someone@",
    r"^email@",
    r"^sample@",
    r"^demo@",
    r"^username@",
    r"^myname@",
    r"^first\.last@",
    r".*@example\.com$",
    r".*@example\.org$",
    r".*@domain\.com$",
    r".*@email\.com$",
    r".*@yourdomain\.com$",
    r".*@sentry\.io$",
    r".*@wixpress\.com$",
    r".*@schema\.org$",
    r".*@w3\.org$",
    r".*@github\.com$",
    r".*@cloudflare\.com$",
]

# Standard RFC 5322 compliant email regex (case insensitive)
EMAIL_REGEX = re.compile(
    r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+",
    re.IGNORECASE
)

# Obfuscated patterns like "contact [at] domain [dot] com" or "info(at)domain(dot)com"
OBFUSCATED_PATTERNS = [
    re.compile(r"([a-zA-Z0-9_.+-]+)\s*\[at\]\s*([a-zA-Z0-9-]+)\s*\[dot\]\s*([a-zA-Z0-9-.]+)", re.IGNORECASE),
    re.compile(r"([a-zA-Z0-9_.+-]+)\s*\(at\)\s*([a-zA-Z0-9-]+)\s*\(dot\)\s*([a-zA-Z0-9-.]+)", re.IGNORECASE),
    re.compile(r"([a-zA-Z0-9_.+-]+)\s*\[@\]\s*([a-zA-Z0-9-]+)\s*\[\.\]\s*([a-zA-Z0-9-.]+)", re.IGNORECASE),
    re.compile(r"([a-zA-Z0-9_.+-]+)\s+AT\s+([a-zA-Z0-9-]+)\s+DOT\s+([a-zA-Z0-9-.]+)", re.IGNORECASE),
]

# Phone number extraction patterns
PHONE_REGEX = re.compile(
    r"(?:(?:\+|00)\d{1,3}[\s.-]?)?(?:\(?\d{2,5}\)?[\s.-]?)?\d{3,5}[\s.-]?\d{3,5}(?:[\s.-]?\d{1,5})?",
    re.VERBOSE
)

DUMMY_PHONES = {
    "1234567890", "0123456789", "0000000000", "1111111111", "9999999999",
    "5555555555", "12345678", "1234567"
}

SOCIAL_DOMAINS = {
    "linkedin": re.compile(r"https?://(?:www\.)?linkedin\.com/(?:company|in|school)/([a-zA-Z0-9_-]+)", re.IGNORECASE),
    "twitter": re.compile(r"https?://(?:www\.)?(?:twitter\.com|x\.com)/(?!share|intent|search|home|explore|privacy|tos)([a-zA-Z0-9_]{1,30})", re.IGNORECASE),
    "facebook": re.compile(r"https?://(?:www\.)?facebook\.com/(?!sharer|share\.php|dialog|plugins|help|policies|pages)([a-zA-Z0-9._-]+)", re.IGNORECASE),
    "instagram": re.compile(r"https?://(?:www\.)?instagram\.com/(?!p/|stories/|explore/|about/|developer/)([a-zA-Z0-9._]+)", re.IGNORECASE),
    "github": re.compile(r"https?://(?:www\.)?github\.com/(?!features|pricing|about|security|login|signup|topics)([a-zA-Z0-9_-]+)", re.IGNORECASE),
    "youtube": re.compile(r"https?://(?:www\.)?youtube\.com/(?:@|channel/|c/|user/)([a-zA-Z0-9_-]+)", re.IGNORECASE),
}


def decode_cloudflare_email(cf_hex: str) -> Optional[str]:
    """
    Decodes emails protected by Cloudflare's email protection (data-cfemail attribute).
    Cloudflare uses a 1-byte XOR key followed by XOR'ed hex character pairs.
    """
    try:
        if not cf_hex or len(cf_hex) < 4:
            return None
        r = int(cf_hex[:2], 16)
        email_chars = []
        for n in range(2, len(cf_hex), 2):
            email_chars.append(chr(int(cf_hex[n:n+2], 16) ^ r))
        decoded = "".join(email_chars).strip()
        return decoded if "@" in decoded else None
    except Exception:
        return None


def clean_and_validate_email(email: str) -> Optional[str]:
    """
    Cleans raw email string and validates its structure, discarding noise,
    media asset names, and placeholder templates.
    """
    if not email:
        return None

    email = email.strip().strip("'\"<>(),;:/\\").lower()

    # Unescape any percent-encoding (e.g. mailto:user%40site.com)
    try:
        email = urllib.parse.unquote(email)
    except Exception:
        pass

    # Must contain exactly one '@'
    if email.count("@") != 1:
        return None

    user, domain = email.split("@")
    if not user or not domain:
        return None

    # Check for valid domain structure (must have dot, valid TLD)
    if "." not in domain:
        return None

    tld = domain.split(".")[-1].lower()
    if len(tld) < 2 or len(tld) > 24 or not tld.isalpha():
        return None

    # Check if this is an image or document filename mistakenly matched
    if tld in IGNORED_EXTENSIONS:
        return None

    # Check against known dummy/placeholder email patterns
    for pattern in DUMMY_EMAIL_PATTERNS:
        if re.search(pattern, email, re.IGNORECASE):
            return None

    # Ensure no invalid characters
    if any(c in email for c in [" ", "\t", "\n", "\r", "\\", "/", ":", ";", "<", ">", "[", "]", "{", "}"]):
        return None

    return email


def extract_emails_from_html(html_content: str, page_url: str = "") -> Set[str]:
    """
    Extracts all email addresses found within the given HTML page,
    inspecting:
      1. Cloudflare protected elements (<a data-cfemail="...">)
      2. mailto: links in <a> tags
      3. Contact form actions, hidden inputs, and data-* attributes
      4. Decoded HTML text & unescaped entities
      5. Obfuscated strings like [at] and (dot)
      6. Inline script definitions & JSON-LD
    """
    if not html_content:
        return set()

    found_emails: Set[str] = set()

    # 1. Unescape HTML entities first (e.g., &#64; -> @)
    decoded_html = html.unescape(html_content)

    # 2. Parse DOM with BeautifulSoup
    soup = BeautifulSoup(decoded_html, "lxml")

    # A. Check Cloudflare email obfuscation
    for elem in soup.find_all(attrs={"data-cfemail": True}):
        cf_hex = elem.get("data-cfemail")
        decoded = decode_cloudflare_email(cf_hex)
        if decoded:
            cleaned = clean_and_validate_email(decoded)
            if cleaned:
                found_emails.add(cleaned)

    # B. Inspect all mailto: links
    for link in soup.find_all("a", href=True):
        href = link.get("href", "").strip()
        if href.lower().startswith("mailto:"):
            # Strip mailto: prefix and query params (?subject=...)
            raw_email = href[7:].split("?")[0].strip()
            # In case multiple emails separated by comma or semicolon
            for part in re.split(r"[,;]", raw_email):
                cleaned = clean_and_validate_email(part)
                if cleaned:
                    found_emails.add(cleaned)

    # C. Inspect contact forms, input fields, and data attributes
    for form in soup.find_all("form"):
        # Form action might point to mailto: or have email in query string
        action = form.get("action", "")
        if "mailto:" in action.lower():
            raw = action.split("mailto:")[1].split("?")[0]
            cleaned = clean_and_validate_email(raw)
            if cleaned:
                found_emails.add(cleaned)

        # Look inside form inputs for email attributes
        for inp in form.find_all(["input", "textarea"]):
            for attr in ["value", "placeholder", "data-email", "data-contact", "data-to"]:
                val = inp.get(attr, "")
                if val and "@" in val:
                    for match in EMAIL_REGEX.findall(val):
                        cleaned = clean_and_validate_email(match)
                        if cleaned:
                            found_emails.add(cleaned)

    # D. Inspect any tag with data-email or data-address attributes
    for tag in soup.find_all(True):
        tag_attrs = getattr(tag, "attrs", {})
        if isinstance(tag_attrs, dict):
            for k, v in tag_attrs.items():
                if k.startswith("data-") and ("email" in k or "mail" in k):
                    if isinstance(v, str) and "@" in v:
                        for match in EMAIL_REGEX.findall(v):
                            cleaned = clean_and_validate_email(match)
                            if cleaned:
                                found_emails.add(cleaned)

    # E. De-obfuscate text patterns (e.g. contact [at] domain [dot] com)
    body_text = soup.get_text(separator=" ", strip=True)
    for pattern in OBFUSCATED_PATTERNS:
        for match in pattern.finditer(body_text):
            reconstructed = f"{match.group(1)}@{match.group(2)}.{match.group(3)}"
            cleaned = clean_and_validate_email(reconstructed)
            if cleaned:
                found_emails.add(cleaned)

    # F. Standard regex across visible text
    for match in EMAIL_REGEX.findall(body_text):
        cleaned = clean_and_validate_email(match)
        if cleaned:
            found_emails.add(cleaned)

    # G. Inspect scripts (like JSON-LD schema or contact widgets)
    for script in soup.find_all("script"):
        script_text = script.string or script.text or ""
        if script_text and "@" in script_text:
            for match in EMAIL_REGEX.findall(script_text):
                cleaned = clean_and_validate_email(match)
                if cleaned:
                    found_emails.add(cleaned)

    return found_emails


def select_primary_email(emails: List[str], target_domain: str = "") -> str:
    """
    Selects the most suitable primary contact email from a list of discovered emails.
    Favors general contact prefixes (info@, contact@, support@, hello@, sales@)
    and emails matching the target domain.
    """
    if not emails:
        return ""

    if len(emails) == 1:
        return emails[0]

    # Clean target domain for comparison
    clean_domain = target_domain.lower().replace("www.", "").strip()

    priority_prefixes = ["info@", "contact@", "support@", "hello@", "sales@", "inquiries@", "help@", "admin@", "team@"]

    # Score each email
    scored: List[Tuple[int, str]] = []
    for email in emails:
        score = 0
        user, domain = email.split("@")

        # Bonus for matching target domain
        if clean_domain and (clean_domain in domain or domain in clean_domain):
            score += 20

        # Bonus for common corporate prefixes
        for idx, prefix in enumerate(priority_prefixes):
            if email.startswith(prefix):
                score += (30 - idx * 2)
                break

        scored.append((score, email))

    # Return highest scoring email
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[0][1]

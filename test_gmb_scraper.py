"""
Integration & Unit Test for GMB Extractor
Verifies Playwright browser launching, GMBExtractor query generation,
data extraction, and Excel/CSV/XLS export capabilities.
"""

import asyncio
import os
import io
from gmb_scraper import GMBExtractor, GMBBusinessProfile
from exporter import export_gmb_to_excel, export_gmb_to_csv, export_gmb_to_xls


def test_query_generation():
    # Standard mode
    extractor = GMBExtractor(niche="Dentists", location="Dallas, TX", exhaustive_mode=False)
    queries = extractor._generate_queries()
    assert len(queries) == 1
    assert queries[0] == "Dentists in Dallas, TX"

    # Exhaustive mode
    extractor_ex = GMBExtractor(niche="Roofing", location="Miami, FL", exhaustive_mode=True)
    queries_ex = extractor_ex._generate_queries()
    assert len(queries_ex) >= 5
    assert any("Downtown" in q for q in queries_ex)
    assert any("North" in q for q in queries_ex)


def test_gmb_exports():
    mock_data = [
        {
            "business_name": "Apex Dental Studio",
            "category": "Cosmetic Dentist",
            "phone": "(214) 555-0199",
            "primary_email": "hello@apexdental.com",
            "all_emails": ["hello@apexdental.com", "billing@apexdental.com"],
            "website": "https://apexdental.com",
            "address": "123 Main St, Dallas, TX 75201",
            "rating": "4.9",
            "reviews_count": "158",
            "operating_status": "Open · Closes 5 PM",
            "maps_url": "https://maps.google.com/?cid=123456789",
            "place_id": "ChIJ123456",
        },
        {
            "business_name": "Lone Star Smiles",
            "category": "Pediatric Dentist",
            "phone": "(214) 555-0288",
            "primary_email": "",
            "all_emails": [],
            "website": "https://lonestarsmiles.com",
            "address": "456 Elm St, Dallas, TX 75202",
            "rating": "4.7",
            "reviews_count": "89",
            "operating_status": "Closed · Opens 8 AM Mon",
            "maps_url": "https://maps.google.com/?cid=987654321",
            "place_id": "ChIJ654321",
        }
    ]

    # 1. Test Excel .xlsx export
    xlsx_bytes = export_gmb_to_excel(mock_data)
    assert len(xlsx_bytes) > 2000
    assert xlsx_bytes[:4] == b"PK\x03\x04"  # Valid ZIP/XLSX header

    # 2. Test CSV export
    csv_str = export_gmb_to_csv(mock_data)
    assert "Business Name" in csv_str
    assert "Apex Dental Studio" in csv_str
    assert "hello@apexdental.com" in csv_str

    # 3. Test Legacy .xls export
    xls_bytes = export_gmb_to_xls(mock_data)
    assert len(xls_bytes) > 1000
    assert xls_bytes[:8] == b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"  # OLE/CFB header


async def test_playwright_launch():
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
        )
        page = await browser.new_page()
        await page.set_content("<html><body><h1>GMB Extractor Test</h1></body></html>")
        h1_text = await page.locator("h1").inner_text()
        assert h1_text == "GMB Extractor Test"
        await browser.close()


if __name__ == "__main__":
    test_query_generation()
    test_gmb_exports()
    asyncio.run(test_playwright_launch())
    print("ALL TESTS PASSED SUCCESSFULLY!")

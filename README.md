# Lead & Email Harvester Pro 🚀

A high-performance Python web application designed for comprehensive local business lead generation from **Google My Business (GMB / Google Maps)** and deep multi-page email extraction across target websites with automatic styled Excel (`.xlsx`), legacy (`.xls`), and CSV export.

---

## Key Features

### 1. 📍 Google Maps / GMB Profile Extractor (New!)
- **Dual-Input Lead Generator**:
  - **Niche / Business Category** (e.g. *Dentists*, *Roofers*, *Plumbers*, *Real Estate*, *Restaurants*)
  - **City, Targeted Area, or State** (e.g. *Dallas, TX*, *Miami, FL*, *California*)
- **Infinite-Scroll Harvester**:
  - Leverages **Playwright (Async Headless Chromium)** to automate Google Maps feed scrolling (`div[role='feed']`).
  - Extracts **Business Name, Category/Niche, Phone Number, Website, Full Address, Rating ⭐, Review Count, Operating Status, and Google Maps CID/URL**.
- **Exhaustive "Get ALL" Multi-Zone Sweep**:
  - Decomposes target cities/states into directional sub-queries (*Downtown, North, South, East, West, Central*) to bypass Google's artificial ~120-listing limit and extract all available profiles.
  - Automatic deduplication by Place ID and phone number.
- **Deep Website Email Enrichment Bridge**:
  - Discovered business websites are automatically fed into the built-in crawler to extract owner and contact emails (`owner@`, `info@`, `contact@`), saving everything to a single unified spreadsheet!

### 2. 🌐 Direct Website Email Extractor
- Traverses internal pages (`/contact`, `/about`, `/team`, `/staff`, `/support`, `/help`, `/imprint`, footer links) within target domains.
- Unmasks obfuscated emails, decodes Cloudflare email protection (`data-cfemail`), and scans contact form actions.
- Smart column auto-detection and column picker modal for `.xlsx`, `.xls`, and `.csv` file uploads.

### 3. 📊 Real-Time Web Dashboard & Exports
- **Dual Mode UI Tabs**: Switch seamlessly between Google Maps Leads and Direct Website Crawling.
- Dark-mode glassmorphic dashboard with live counters, progress bar, and Active Spider Console with SSE streaming.
- **Multi-Format Styled Exports**:
  - **Excel (`.xlsx`)**: Styled header rows, clickable website/maps hyperlinks, auto-fitted column widths, and rating highlights.
  - **Legacy Excel (`.xls`)**: Maximum backward compatibility.
  - **CSV**: Standard flat file export.
- **Session History**: Automatically saves and indexes every extraction with one-click reload and download.

---

## Quick Start

### 1. Launch with Single Click
Double-click `run.bat` or run in terminal:
```bash
.\run.bat
```
This automatically activates the virtual environment, launches the server, and opens your default browser at `http://127.0.0.1:8000`.

### 2. Manual Command Line
```bash
.venv\Scripts\python -m uvicorn app:app --host 127.0.0.1 --port 8000 --reload
```

---

## Project Structure

```
d:/extractor/
├── app.py              # FastAPI server, background task manager & SSE stream
├── gmb_scraper.py      # Playwright Google Maps extractor & exhaustive grid expander
├── crawler.py          # Async domain crawler with link priority scoring
├── extractor.py        # Email extraction, de-obfuscation & Cloudflare decoder
├── exporter.py         # OpenPyXL & xlwt styled Excel (.xlsx/.xls) and CSV exporter
├── requirements.txt    # Frozen Python dependencies
├── run.bat             # 1-click launcher script
├── templates/
│   └── index.html      # Dual-mode modern dashboard HTML
└── static/
    ├── style.css       # Dark glassmorphic design system
    └── app.js          # Client-side controller, mode switcher & table renderer
```

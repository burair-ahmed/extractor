# Email Extractor Pro 🚀

A high-performance Python web application designed for deep multi-page email extraction across target websites and automatic styled Excel (`.xlsx`) export.

---

## Key Features

- **Email-Centric Deep Crawler**:
  - Traverses internal pages (`/contact`, `/about`, `/team`, `/staff`, `/support`, `/help`, `/imprint`, footer links) within the same domain.
  - Extracts direct `mailto:` links with parameters removed.
  - De-obfuscates masked patterns (e.g., `info [at] domain [dot] com`, `contact(at)site.org`).
  - Decodes **Cloudflare email protection** (`data-cfemail` hex string decoding).
  - Inspects contact form actions, hidden form values, and `data-*` attributes.
  - Filters dummy/placeholder addresses (`user@example.com`, `name@domain.com`) and asset extensions (`logo@2x.png`).
- **Real-Time Web Dashboard**:
  - Dark-mode glassmorphic interface with live progress bar and live counters.
  - Active Spider Console with streaming Server-Sent Events (SSE).
  - Searchable/filterable results directory with one-click copy buttons.
- **Export Formats**:
  - **Excel (`.xlsx`)**: Custom-styled workbook with frozen headers, auto-adjusted column widths, status color coding, and individual email source URLs.
  - **CSV**: Standard flat file export.
- **Batch Inputs**:
  - Multi-line textarea paste.
  - File upload supporting `.txt`, `.csv`, and `.xlsx` files.

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
├── crawler.py          # Async domain crawler with link priority scoring
├── extractor.py        # Email extraction, de-obfuscation & Cloudflare decoder
├── exporter.py         # OpenPyXL styled Excel & CSV exporter
├── requirements.txt    # Frozen Python dependencies
├── run.bat             # 1-click launcher script
├── templates/
│   └── index.html      # Modern dashboard HTML
└── static/
    ├── style.css       # Dark glassmorphic design system
    └── app.js          # Client-side SSE controller & table renderer
```

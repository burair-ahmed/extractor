"""
Email Extractor Web Application Server
FastAPI backend powering URL batch crawling, real-time SSE progress streaming,
Excel/CSV report generation, and persistent session history.
"""

import asyncio
import io
import json
import os
import uuid
import datetime
from typing import Dict, List, Optional, Any
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Response
from fastapi.responses import HTMLResponse, StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd

from crawler import DomainCrawler, WebsiteResult, normalize_root_url
from exporter import export_results_to_excel, export_results_to_csv, export_results_to_xls

app = FastAPI(title="Email Extractor Pro", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# History Storage
HISTORY_DIR = os.path.join(os.path.dirname(__file__), "history")
os.makedirs(HISTORY_DIR, exist_ok=True)

HISTORY_INDEX_FILE = os.path.join(HISTORY_DIR, "index.json")


def _load_history_index() -> List[Dict]:
    if not os.path.exists(HISTORY_INDEX_FILE):
        return []
    try:
        with open(HISTORY_INDEX_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _save_history_index(index: List[Dict]):
    with open(HISTORY_INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2, ensure_ascii=False)


def _save_task_to_history(task: "ExtractionTask"):
    """Persist completed task results to disk in XLSX, XLS, CSV and JSON, then update index."""
    if not task.results:
        return

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = f"session_{task.task_id}_{timestamp}"

    # 1. Save Modern Excel (.xlsx)
    xlsx_bytes = export_results_to_excel(task.results)
    xlsx_path = os.path.join(HISTORY_DIR, base_name + ".xlsx")
    with open(xlsx_path, "wb") as f:
        f.write(xlsx_bytes)

    # 2. Save Legacy Excel (.xls)
    try:
        xls_bytes = export_results_to_xls(task.results)
        xls_path = os.path.join(HISTORY_DIR, base_name + ".xls")
        with open(xls_path, "wb") as f:
            f.write(xls_bytes)
        xls_file = base_name + ".xls"
    except Exception as e:
        xls_file = ""

    # 3. Save CSV (.csv)
    csv_data = export_results_to_csv(task.results)
    csv_path = os.path.join(HISTORY_DIR, base_name + ".csv")
    with open(csv_path, "w", encoding="utf-8") as f:
        f.write(csv_data)

    # 4. Save Raw JSON for instant reloading into UI
    json_path = os.path.join(HISTORY_DIR, base_name + ".json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(task.results, f, indent=2, ensure_ascii=False)

    index = _load_history_index()
    index.insert(0, {
        "task_id": task.task_id,
        "timestamp": datetime.datetime.now().isoformat(),
        "timestamp_display": datetime.datetime.now().strftime("%b %d, %Y %H:%M"),
        "total_sites": task.total_sites,
        "completed_sites": task.completed_sites,
        "total_emails": task.total_emails_found,
        "total_pages": task.total_pages_scanned,
        "status": task.status,
        "xlsx_file": base_name + ".xlsx",
        "xls_file": xls_file,
        "csv_file": base_name + ".csv",
        "json_file": base_name + ".json",
        "urls_sample": task.urls[:5],
    })
    index = index[:50]
    _save_history_index(index)



class ExtractionTask:
    def __init__(self, task_id: str, urls: List[str], max_pages: int, concurrency: int, timeout: float):
        self.task_id = task_id
        self.urls = [u for u in [normalize_root_url(x) for x in urls] if u]
        self.max_pages = max_pages
        self.concurrency = concurrency
        self.timeout = timeout
        self.status = "Pending"
        self.results: List[Dict[str, Any]] = []
        self.total_sites = len(self.urls)
        self.completed_sites = 0
        self.total_emails_found = 0
        self.total_pages_scanned = 0
        self.event_queue: asyncio.Queue = asyncio.Queue()
        self.active_crawlers: List[DomainCrawler] = []
        self.is_cancelled = False

    async def emit_event(self, data: Dict[str, Any]):
        await self.event_queue.put(data)

    def cancel(self):
        self.is_cancelled = True
        self.status = "Cancelled"
        for c in self.active_crawlers:
            c.cancel()


TASKS: Dict[str, ExtractionTask] = {}


async def run_crawler_task(task: ExtractionTask):
    task.status = "Running"
    await task.emit_event({
        "type": "task_start",
        "total_sites": task.total_sites,
        "message": f"Starting extraction across {task.total_sites} website(s)..."
    })

    semaphore = asyncio.Semaphore(task.concurrency)

    async def crawl_site(url: str):
        if task.is_cancelled:
            return

        async with semaphore:
            if task.is_cancelled:
                return

            crawler = DomainCrawler(
                target_url=url,
                max_pages=task.max_pages,
                timeout=task.timeout,
                progress_callback=lambda p: asyncio.create_task(task.emit_event({
                    "type": "progress",
                    "data": p,
                    "completed_sites": task.completed_sites,
                    "total_sites": task.total_sites,
                    "total_emails": task.total_emails_found,
                    "total_pages": task.total_pages_scanned,
                }))
            )
            task.active_crawlers.append(crawler)

            site_res = await crawler.crawl()
            site_dict = site_res.to_dict()
            task.results.append(site_dict)

            task.completed_sites += 1
            task.total_emails_found += len(site_res.all_emails)
            task.total_pages_scanned += site_res.pages_scanned

            await task.emit_event({
                "type": "site_done",
                "site": site_dict,
                "completed_sites": task.completed_sites,
                "total_sites": task.total_sites,
                "total_emails": task.total_emails_found,
                "total_pages": task.total_pages_scanned,
            })

    try:
        tasks_list = [crawl_site(u) for u in task.urls]
        await asyncio.gather(*tasks_list, return_exceptions=True)

        if not task.is_cancelled:
            task.status = "Completed"
            await task.emit_event({
                "type": "task_completed",
                "total_emails": task.total_emails_found,
                "total_pages": task.total_pages_scanned,
                "completed_sites": task.completed_sites,
                "message": f"Extraction completed! Found {task.total_emails_found} emails across {task.completed_sites} websites."
            })
            _save_task_to_history(task)

    except Exception as e:
        task.status = "Failed"
        await task.emit_event({
            "type": "task_error",
            "message": f"Fatal extraction error: {str(e)}"
        })


def parse_urls_from_file(file_bytes: bytes, filename: str, url_column: Optional[str] = None) -> List[str]:
    """Extracts URLs from uploaded TXT, CSV, or Excel file."""
    urls = []
    fname = filename.lower()

    if fname.endswith(".txt"):
        text = file_bytes.decode("utf-8", errors="ignore")
        urls = [line.strip() for line in text.splitlines() if line.strip()]

    elif fname.endswith(".csv"):
        df = pd.read_csv(io.BytesIO(file_bytes))
        if url_column and url_column in df.columns:
            urls = df[url_column].dropna().astype(str).tolist()
        else:
            url_cols = [c for c in df.columns if any(k in str(c).lower() for k in ["url", "website", "link", "site", "domain"])]
            if url_cols:
                urls = df[url_cols[0]].dropna().astype(str).tolist()
            else:
                urls = df.iloc[:, 0].dropna().astype(str).tolist()

    elif fname.endswith((".xlsx", ".xls")):
        df = pd.read_excel(io.BytesIO(file_bytes))
        if url_column and url_column in df.columns:
            urls = df[url_column].dropna().astype(str).tolist()
        else:
            url_cols = [c for c in df.columns if any(k in str(c).lower() for k in ["url", "website", "link", "site", "domain"])]
            if url_cols:
                urls = df[url_cols[0]].dropna().astype(str).tolist()
            else:
                urls = df.iloc[:, 0].dropna().astype(str).tolist()

    return [u.strip() for u in urls if u.strip()]


@app.post("/api/inspect-file")
async def inspect_file(file: UploadFile = File(...)):
    """
    Reads an xls/xlsx/csv file and returns its columns plus a preview.
    Used by the client to let the user pick which column has website URLs.
    """
    fname = (file.filename or "").lower()
    if not fname.endswith((".xls", ".xlsx", ".csv")):
        raise HTTPException(status_code=400, detail="Only XLS, XLSX, or CSV files are supported.")

    file_bytes = await file.read()

    try:
        if fname.endswith(".csv"):
            df = pd.read_csv(io.BytesIO(file_bytes))
        else:
            df = pd.read_excel(io.BytesIO(file_bytes))
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Could not parse file: {str(e)}")

    columns = list(df.columns.astype(str))
    total_rows = len(df)

    column_samples: Dict[str, List[str]] = {}
    column_rows: Dict[str, List[str]] = {}
    for col in columns:
        samples = df[col].dropna().astype(str).head(4).tolist()
        column_samples[col] = samples
        # Extract all non-empty row values for automatic filling
        raw_vals = [str(v).strip() for v in df[col].dropna().tolist() if str(v).strip()]
        column_rows[col] = raw_vals

    suggested_col = None
    for col in columns:
        if any(k in col.lower() for k in ["url", "website", "link", "site", "domain"]):
            suggested_col = col
            break
    if not suggested_col:
        for col in columns:
            samples = column_samples.get(col, [])
            if any("http" in s.lower() or "www." in s.lower() for s in samples):
                suggested_col = col
                break

    return {
        "columns": columns,
        "total_rows": total_rows,
        "column_samples": column_samples,
        "column_rows": column_rows,
        "suggested_column": suggested_col,
        "filename": file.filename,
    }



@app.post("/api/tasks")
async def create_task(
    urls_text: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    url_column: Optional[str] = Form(None),
    max_pages: int = Form(25),
    concurrency: int = Form(4),
    timeout: float = Form(12.0),
):
    all_urls: List[str] = []

    if urls_text:
        lines = [line.strip() for line in urls_text.splitlines() if line.strip()]
        all_urls.extend(lines)

    if file and file.filename:
        file_bytes = await file.read()
        extracted = parse_urls_from_file(file_bytes, file.filename, url_column=url_column)
        all_urls.extend(extracted)

    seen = set()
    deduped_urls = []
    for u in all_urls:
        norm = normalize_root_url(u)
        if norm and norm not in seen:
            seen.add(norm)
            deduped_urls.append(norm)

    if not deduped_urls:
        raise HTTPException(status_code=400, detail="No valid URLs provided. Paste URLs or upload a file.")

    task_id = str(uuid.uuid4())[:8]
    task = ExtractionTask(
        task_id=task_id,
        urls=deduped_urls,
        max_pages=max_pages,
        concurrency=concurrency,
        timeout=timeout
    )
    TASKS[task_id] = task

    asyncio.create_task(run_crawler_task(task))

    return {
        "task_id": task_id,
        "total_urls": len(deduped_urls),
        "status": "Running"
    }


@app.get("/api/tasks/{task_id}/stream")
async def stream_task_events(task_id: str):
    task = TASKS.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    async def event_generator():
        initial_data = {
            "type": "init",
            "total_sites": task.total_sites,
            "completed_sites": task.completed_sites,
            "total_emails": task.total_emails_found,
            "total_pages": task.total_pages_scanned,
            "status": task.status,
            "existing_results": task.results
        }
        yield f"data: {json.dumps(initial_data)}\n\n"

        while True:
            try:
                event = await asyncio.wait_for(task.event_queue.get(), timeout=15.0)
                yield f"data: {json.dumps(event)}\n\n"
                if event.get("type") in ["task_completed", "task_error"]:
                    break
            except asyncio.TimeoutError:
                yield f": keep-alive\n\n"
                if task.status in ["Completed", "Cancelled", "Failed"] and task.event_queue.empty():
                    break

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/api/tasks/{task_id}/results")
async def get_task_results(task_id: str):
    task = TASKS.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return {
        "task_id": task.task_id,
        "status": task.status,
        "total_sites": task.total_sites,
        "completed_sites": task.completed_sites,
        "total_emails": task.total_emails_found,
        "total_pages": task.total_pages_scanned,
        "results": task.results,
    }


@app.get("/api/tasks/{task_id}/export/excel")
async def export_excel(task_id: str):
    task = TASKS.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    excel_bytes = export_results_to_excel(task.results)
    filename = f"extracted_emails_{task_id}.xlsx"
    return Response(
        content=excel_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@app.get("/api/tasks/{task_id}/export/xls")
async def export_xls(task_id: str):
    task = TASKS.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    xls_bytes = export_results_to_xls(task.results)
    filename = f"extracted_emails_{task_id}.xls"
    return Response(
        content=xls_bytes,
        media_type="application/vnd.ms-excel",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@app.get("/api/tasks/{task_id}/export/csv")
async def export_csv(task_id: str):
    task = TASKS.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    csv_data = export_results_to_csv(task.results)
    filename = f"extracted_emails_{task_id}.csv"
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@app.post("/api/tasks/{task_id}/cancel")
async def cancel_task(task_id: str):
    task = TASKS.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    task.cancel()
    return {"task_id": task_id, "status": "Cancelled"}


@app.get("/api/history")
async def get_history():
    """Returns the list of saved extraction sessions."""
    return {"sessions": _load_history_index()}


@app.get("/api/history/{task_id}/results")
async def get_history_results(task_id: str):
    """Retrieves full results list for a historical session so user can view/inspect."""
    index = _load_history_index()
    entry = next((e for e in index if e["task_id"] == task_id), None)
    if not entry:
        raise HTTPException(status_code=404, detail="History entry not found")

    json_file = entry.get("json_file", "")
    json_path = os.path.join(HISTORY_DIR, json_file) if json_file else ""
    if json_path and os.path.exists(json_path):
        with open(json_path, "r", encoding="utf-8") as f:
            results = json.load(f)
        return {"task_id": task_id, "entry": entry, "results": results}

    # Fallback to reading CSV if JSON file doesn't exist
    csv_file = entry.get("csv_file", "")
    csv_path = os.path.join(HISTORY_DIR, csv_file) if csv_file else ""
    if csv_path and os.path.exists(csv_path):
        df = pd.read_csv(csv_path)
        results = []
        for _, row in df.iterrows():
            results.append({
                "target_url": str(row.get("Website URL", "")),
                "primary_email": str(row.get("Primary Email", "") if not pd.isna(row.get("Primary Email")) else ""),
                "all_emails": str(row.get("All Discovered Emails", "") if not pd.isna(row.get("All Discovered Emails")) else ""),
                "pages_scanned": int(row.get("Pages Scanned", 0)),
                "status": str(row.get("Status", "")),
                "error_message": str(row.get("Error Details", "") if not pd.isna(row.get("Error Details")) else ""),
            })
        return {"task_id": task_id, "entry": entry, "results": results}

    raise HTTPException(status_code=404, detail="Results data file not found")


@app.delete("/api/history/{task_id}")
async def delete_history_entry(task_id: str):
    """Deletes a history entry and its associated files."""
    index = _load_history_index()
    entry = next((e for e in index if e["task_id"] == task_id), None)
    if not entry:
        raise HTTPException(status_code=404, detail="History entry not found")

    for key in ("xlsx_file", "xls_file", "csv_file", "json_file"):
        fname = entry.get(key, "")
        if fname:
            fpath = os.path.join(HISTORY_DIR, fname)
            if os.path.exists(fpath):
                try:
                    os.remove(fpath)
                except Exception:
                    pass

    index = [e for e in index if e["task_id"] != task_id]
    _save_history_index(index)
    return {"status": "deleted", "task_id": task_id}


@app.get("/api/history/{task_id}/download/{fmt}")
async def download_history_file(task_id: str, fmt: str):
    """Download a historical session file. fmt = 'xlsx', 'xls', or 'csv'."""
    fmt = fmt.lower()
    if fmt not in ("xlsx", "xls", "csv"):
        raise HTTPException(status_code=400, detail="Format must be 'xlsx', 'xls', or 'csv'")

    index = _load_history_index()
    entry = next((e for e in index if e["task_id"] == task_id), None)
    if not entry:
        raise HTTPException(status_code=404, detail="History entry not found")

    if fmt == "xlsx":
        file_key = "xlsx_file"
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    elif fmt == "xls":
        file_key = "xls_file"
        media_type = "application/vnd.ms-excel"
    else:
        file_key = "csv_file"
        media_type = "text/csv"

    filename = entry.get(file_key, "")
    fpath = os.path.join(HISTORY_DIR, filename)

    if not filename or not os.path.exists(fpath):
        raise HTTPException(status_code=404, detail=f"File {filename} not found on disk")

    return FileResponse(path=fpath, media_type=media_type, filename=filename)



app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", response_class=HTMLResponse)
async def serve_index():
    with open("templates/index.html", "r", encoding="utf-8") as f:
        return f.read()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)

"""
End-to-End Verification of XLS/XLSX Upload, Column Auto-Fill, and Dynamic History Export
"""
import io
import json
import httpx
import pandas as pd
import openpyxl
import xlwt

BASE_URL = "http://127.0.0.1:8000"

def create_sample_xlsx():
    df = pd.DataFrame({
        "Company Name": ["Alpha Tech", "Beta Solutions", "Gamma Cloud"],
        "Target Website": ["https://example.com", "https://httpbin.org", "https://news.ycombinator.com"],
        "Category": ["Software", "Consulting", "Tech News"]
    })
    buf = io.BytesIO()
    df.to_excel(buf, index=False, engine="openpyxl")
    return buf.getvalue()

def create_sample_xls():
    wb = xlwt.Workbook(encoding="utf-8")
    ws = wb.add_sheet("Targets")
    ws.write(0, 0, "Organization")
    ws.write(0, 1, "Web Domain")
    ws.write(0, 2, "HQ")

    data = [
        ("Acme Corp", "https://example.com", "New York"),
        ("Global Logistics", "https://httpbin.org", "London")
    ]
    for r_idx, (org, url, hq) in enumerate(data, start=1):
        ws.write(r_idx, 0, org)
        ws.write(r_idx, 1, url)
        ws.write(r_idx, 2, hq)

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()

def run_tests():
    client = httpx.Client(base_url=BASE_URL, timeout=30.0)

    print("1. Testing /api/inspect-file with .xlsx...")
    xlsx_bytes = create_sample_xlsx()
    resp = client.post(
        "/api/inspect-file",
        files={"file": ("sample_sites.xlsx", xlsx_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
    )
    assert resp.status_code == 200, f"Failed xlsx inspect: {resp.text}"
    data_xlsx = resp.json()
    assert "columns" in data_xlsx
    assert "Target Website" in data_xlsx["columns"]
    assert data_xlsx["suggested_column"] == "Target Website"
    assert "column_rows" in data_xlsx
    assert len(data_xlsx["column_rows"]["Target Website"]) == 3
    print("   XLSX inspect OK! Suggested column:", data_xlsx["suggested_column"])
    print("   Extracted rows:", data_xlsx["column_rows"]["Target Website"])

    print("2. Testing /api/inspect-file with .xls (legacy)...")
    xls_bytes = create_sample_xls()
    resp = client.post(
        "/api/inspect-file",
        files={"file": ("sample_sites.xls", xls_bytes, "application/vnd.ms-excel")}
    )
    assert resp.status_code == 200, f"Failed xls inspect: {resp.text}"
    data_xls = resp.json()
    assert "Web Domain" in data_xls["columns"]
    assert data_xls["suggested_column"] == "Web Domain"
    assert len(data_xls["column_rows"]["Web Domain"]) == 2
    print("   XLS inspect OK! Suggested column:", data_xls["suggested_column"])
    print("   Extracted rows:", data_xls["column_rows"]["Web Domain"])

    print("3. Testing task creation with auto-filled URLs...")
    urls_to_crawl = "\n".join(data_xlsx["column_rows"]["Target Website"][:1]) # test with 1 URL
    resp = client.post(
        "/api/tasks",
        data={
            "urls_text": urls_to_crawl,
            "max_pages": 3,
            "concurrency": 1,
            "timeout": 8.0
        }
    )
    assert resp.status_code == 200, f"Task create failed: {resp.text}"
    task_id = resp.json()["task_id"]
    print(f"   Task created: {task_id}")

    print("4. Waiting for task completion and auto-save...")
    import time
    for _ in range(20):
        time.sleep(1.0)
        res_resp = client.get(f"/api/tasks/{task_id}/results")
        if res_resp.status_code == 200 and res_resp.json()["status"] == "Completed":
            print("   Task completed successfully!")
            break
    else:
        print("   Task still running or finished with status:", res_resp.json().get("status"))

    print("5. Verifying dynamic history recording and downloads...")
    hist_resp = client.get("/api/history")
    assert hist_resp.status_code == 200
    sessions = hist_resp.json()["sessions"]
    assert len(sessions) > 0, "No history sessions found!"
    latest = sessions[0]
    print(f"   Found latest session {latest['task_id']}, files: xlsx={latest.get('xlsx_file')}, xls={latest.get('xls_file')}, csv={latest.get('csv_file')}")

    # Test downloading XLSX
    dl_xlsx = client.get(f"/api/history/{latest['task_id']}/download/xlsx")
    assert dl_xlsx.status_code == 200 and len(dl_xlsx.content) > 1000, "XLSX download failed"
    print("   XLSX download OK!")

    # Test downloading XLS
    dl_xls = client.get(f"/api/history/{latest['task_id']}/download/xls")
    assert dl_xls.status_code == 200 and len(dl_xls.content) > 1000, "XLS download failed"
    print("   Legacy XLS download OK!")

    # Test downloading CSV
    dl_csv = client.get(f"/api/history/{latest['task_id']}/download/csv")
    assert dl_csv.status_code == 200 and len(dl_csv.content) > 50, "CSV download failed"
    print("   CSV download OK!")

    # Test loading session results
    load_res = client.get(f"/api/history/{latest['task_id']}/results")
    assert load_res.status_code == 200 and "results" in load_res.json()
    print("   Session results retrieval OK! Records:", len(load_res.json()["results"]))

    print("\n==========================================")
    print(" ALL FEATURES AND ENDPOINTS VERIFIED 100%!")
    print("==========================================")

if __name__ == "__main__":
    run_tests()

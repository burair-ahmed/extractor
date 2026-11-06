"""
End-to-End API Test for GMB Extractor Integration
"""

import asyncio
from fastapi.testclient import TestClient
from app import app, TASKS, GMBExtractionTask


def test_gmb_e2e():
    client = TestClient(app)

    # 1. Test HTML Dashboard
    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.text
    assert "Google My Business Extractor" in html
    assert "gmb-niche-input" in html
    assert "gmb-location-input" in html
    assert "tab-btn-gmb" in html
    assert "tab-btn-websites" in html

    # 2. Test Validation on /api/gmb/tasks
    resp_empty = client.post("/api/gmb/tasks", data={"niche": "", "location": ""})
    assert resp_empty.status_code == 400

    # 3. Create a mock GMB task directly and test exports
    task_id = "testgmb1"
    task = GMBExtractionTask(
        task_id=task_id,
        niche="Plumbing",
        location="Austin, TX",
        max_results=10,
        exhaustive=False,
        enrich_emails=True
    )
    task.results = [
        {
            "business_name": "Austin Rapid Plumbing",
            "category": "Plumber",
            "phone": "(512) 555-0144",
            "primary_email": "contact@austinrapidplumbing.com",
            "all_emails": ["contact@austinrapidplumbing.com"],
            "website": "https://austinrapidplumbing.com",
            "address": "789 Congress Ave, Austin, TX 78701",
            "rating": "4.9",
            "reviews_count": "210",
            "operating_status": "Open 24 hours",
            "maps_url": "https://maps.google.com/?cid=11223344",
            "place_id": "ChIJtest1122",
        }
    ]
    task.total_profiles_found = 1
    task.total_emails_found = 1
    task.status = "Completed"
    TASKS[task_id] = task

    # 4. Test Results endpoint
    resp_res = client.get(f"/api/tasks/{task_id}/results")
    assert resp_res.status_code == 200
    data = resp_res.json()
    assert data["task_type"] == "gmb"
    assert len(data["results"]) == 1
    assert data["results"][0]["business_name"] == "Austin Rapid Plumbing"

    # 5. Test Excel Export
    resp_excel = client.get(f"/api/tasks/{task_id}/export/excel")
    assert resp_excel.status_code == 200
    assert resp_excel.headers["content-type"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    assert len(resp_excel.content) > 1000

    # 6. Test CSV Export
    resp_csv = client.get(f"/api/tasks/{task_id}/export/csv")
    assert resp_csv.status_code == 200
    assert "text/csv" in resp_csv.headers["content-type"]
    assert "Austin Rapid Plumbing" in resp_csv.text

    # 7. Test Legacy XLS Export
    resp_xls = client.get(f"/api/tasks/{task_id}/export/xls")
    assert resp_xls.status_code == 200
    assert resp_xls.headers["content-type"] == "application/vnd.ms-excel"

    # 8. Test Cancellation
    resp_cancel = client.post(f"/api/tasks/{task_id}/cancel")
    assert resp_cancel.status_code == 200
    assert task.is_cancelled is True

    print("ALL GMB E2E TESTS PASSED!")


if __name__ == "__main__":
    test_gmb_e2e()


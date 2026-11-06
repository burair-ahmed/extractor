"""
Test verification script for exporter.py
"""
from exporter import export_results_to_excel, export_results_to_csv, export_results_to_xls

sample_results = [
    {
        "target_url": "https://company-alpha.com",
        "primary_email": "contact@company-alpha.com",
        "all_emails": "contact@company-alpha.com, sales@company-alpha.com",
        "all_emails_list": ["contact@company-alpha.com", "sales@company-alpha.com"],
        "email_sources": {
            "contact@company-alpha.com": "https://company-alpha.com/contact-us",
            "sales@company-alpha.com": "https://company-alpha.com/about"
        },
        "pages_scanned": 12,
        "status": "Success",
        "error_message": ""
    },
    {
        "target_url": "https://company-beta.com",
        "primary_email": "",
        "all_emails": "",
        "all_emails_list": [],
        "email_sources": {},
        "pages_scanned": 8,
        "status": "No Email Found",
        "error_message": ""
    }
]

def test_exporter():
    excel_bytes = export_results_to_excel(sample_results)
    assert len(excel_bytes) > 1000, "Excel output too small or empty"
    print(f"Generated Excel XLSX successfully ({len(excel_bytes)} bytes)")

    xls_bytes = export_results_to_xls(sample_results)
    assert len(xls_bytes) > 1000, "Legacy XLS output too small or empty"
    print(f"Generated Legacy XLS successfully ({len(xls_bytes)} bytes)")

    csv_text = export_results_to_csv(sample_results)
    assert "company-alpha.com" in csv_text, "CSV missing domain"
    assert "contact@company-alpha.com" in csv_text, "CSV missing email"
    print(f"Generated CSV successfully ({len(csv_text)} characters)")
    print("ALL EXPORTER TESTS PASSED!")

if __name__ == "__main__":
    test_exporter()


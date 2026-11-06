"""
Excel & CSV Exporter Module
Generates beautifully formatted, styled Excel (.xlsx) workbooks and CSV files
containing extracted contact emails, website targets, and source pages.
"""

import io
from typing import List, Dict, Any
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
import pandas as pd


def export_results_to_excel(results: List[Dict[str, Any]]) -> bytes:
    """
    Creates an Excel (.xlsx) workbook with professional styling,
    auto-fitted columns, color-coded status badges, and frozen headers.
    Returns bytes ready for streaming or saving.
    """
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Contact Emails"

    # Ensure grid lines are visible
    ws.views.sheetView[0].showGridLines = True

    # Header styling
    header_fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    header_align = Alignment(horizontal="center", vertical="center", wrap_text=True)

    # Border style
    thin_border = Border(
        left=Side(style="thin", color="CBD5E1"),
        right=Side(style="thin", color="CBD5E1"),
        top=Side(style="thin", color="CBD5E1"),
        bottom=Side(style="thin", color="CBD5E1"),
    )

    headers = [
        "Website URL",
        "Primary Email",
        "All Discovered Emails",
        "Found On Page(s)",
        "Pages Scanned",
        "Status",
        "Notes / Errors"
    ]

    ws.append(headers)
    ws.row_dimensions[1].height = 28

    for col_idx in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=col_idx)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = header_align
        cell.border = thin_border

    # Status fills
    status_success_fill = PatternFill(start_color="DCFCE7", end_color="DCFCE7", fill_type="solid")  # soft green
    status_success_font = Font(name="Calibri", size=10, bold=True, color="166534")

    status_warning_fill = PatternFill(start_color="FEF3C7", end_color="FEF3C7", fill_type="solid")  # soft amber
    status_warning_font = Font(name="Calibri", size=10, bold=True, color="92400E")

    status_fail_fill = PatternFill(start_color="FEE2E2", end_color="FEE2E2", fill_type="solid")     # soft red
    status_fail_font = Font(name="Calibri", size=10, bold=True, color="991B1B")

    zebra_fill = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
    white_fill = PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid")

    data_font = Font(name="Calibri", size=10)
    primary_email_font = Font(name="Calibri", size=10, bold=True, color="0F172A")

    for row_idx, r in enumerate(results, start=2):
        ws.row_dimensions[row_idx].height = 22

        # Format sources: "email -> page"
        email_sources = r.get("email_sources", {})
        if email_sources:
            sources_str = "\n".join([f"{em}: {pg}" for em, pg in email_sources.items()])
        else:
            sources_str = "N/A"

        all_emails_str = r.get("all_emails", "")
        if isinstance(all_emails_str, list):
            all_emails_str = ", ".join(all_emails_str)

        row_data = [
            r.get("target_url", ""),
            r.get("primary_email", "") or "None",
            all_emails_str or "None",
            sources_str,
            r.get("pages_scanned", 0),
            r.get("status", "Pending"),
            r.get("error_message", "")
        ]
        ws.append(row_data)

        row_fill = zebra_fill if row_idx % 2 == 0 else white_fill

        for col_idx in range(1, len(row_data) + 1):
            cell = ws.cell(row=row_idx, column=col_idx)
            cell.border = thin_border
            cell.fill = row_fill
            cell.font = data_font

            # Alignment per column
            if col_idx in [1, 3, 4]:
                cell.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
            elif col_idx in [2]:
                cell.alignment = Alignment(horizontal="left", vertical="center")
                cell.font = primary_email_font
            elif col_idx in [5, 6]:
                cell.alignment = Alignment(horizontal="center", vertical="center")
            else:
                cell.alignment = Alignment(horizontal="left", vertical="center")

            # Style the Status Column
            if col_idx == 6:
                status_val = str(cell.value).lower()
                if "success" in status_val:
                    cell.fill = status_success_fill
                    cell.font = status_success_font
                elif "no email" in status_val:
                    cell.fill = status_warning_fill
                    cell.font = status_warning_font
                elif "fail" in status_val or "error" in status_val or "invalid" in status_val:
                    cell.fill = status_fail_fill
                    cell.font = status_fail_font

    # Auto-adjust column widths with minimum & maximum bounds
    for col in ws.columns:
        max_len = 0
        col_letter = get_column_letter(col[0].column)
        for cell in col:
            val_str = str(cell.value or "")
            # If multi-line, take longest line
            lines = val_str.split("\n")
            line_max = max(len(l) for l in lines) if lines else 0
            if line_max > max_len:
                max_len = line_max
        # Clamp widths for readability
        adjusted_width = min(max(max_len + 4, 14), 55)
        ws.column_dimensions[col_letter].width = adjusted_width

    # Freeze header row
    ws.freeze_panes = "A2"

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output.getvalue()


def export_results_to_csv(results: List[Dict[str, Any]]) -> str:
    """Exports results to standard CSV string."""
    flat_data = []
    for r in results:
        email_sources = r.get("email_sources", {})
        sources_str = " | ".join([f"{em}: {pg}" for em, pg in email_sources.items()]) if email_sources else ""
        all_emails_str = r.get("all_emails", "")
        if isinstance(all_emails_str, list):
            all_emails_str = ", ".join(all_emails_str)

        flat_data.append({
            "Website URL": r.get("target_url", ""),
            "Primary Email": r.get("primary_email", "") or "",
            "All Discovered Emails": all_emails_str or "",
            "Found On Page": sources_str,
            "Pages Scanned": r.get("pages_scanned", 0),
            "Status": r.get("status", ""),
            "Error Details": r.get("error_message", "")
        })

    df = pd.DataFrame(flat_data)
    return df.to_csv(index=False)


def export_results_to_xls(results: List[Dict[str, Any]]) -> bytes:
    """
    Creates an Excel 97-2003 (.xls) workbook using xlwt for legacy compatibility.
    Returns raw bytes.
    """
    import xlwt

    wb = xlwt.Workbook(encoding="utf-8")
    ws = wb.add_sheet("Contact Emails")

    header_font = xlwt.Font()
    header_font.name = "Arial"
    header_font.bold = True
    header_font.color_index = xlwt.Style.colour_map["white"]

    header_pattern = xlwt.Pattern()
    header_pattern.pattern = xlwt.Pattern.SOLID_PATTERN
    header_pattern.pattern_fore_colour = xlwt.Style.colour_map["gray80"]

    header_align = xlwt.Alignment()
    header_align.horz = xlwt.Alignment.HORZ_CENTER
    header_align.vert = xlwt.Alignment.VERT_CENTER
    header_align.wrap = xlwt.Alignment.WRAP_AT_RIGHT

    header_style = xlwt.XFStyle()
    header_style.font = header_font
    header_style.pattern = header_pattern
    header_style.alignment = header_align

    # Regular style
    item_font = xlwt.Font()
    item_font.name = "Arial"
    item_font.height = 200  # 10pt

    item_align = xlwt.Alignment()
    item_align.vert = xlwt.Alignment.VERT_CENTER
    item_align.wrap = xlwt.Alignment.WRAP_AT_RIGHT

    item_style = xlwt.XFStyle()
    item_style.font = item_font
    item_style.alignment = item_align

    headers = [
        "Website URL",
        "Primary Email",
        "All Discovered Emails",
        "Found On Page(s)",
        "Pages Scanned",
        "Status",
        "Notes / Errors"
    ]

    for col_idx, h in enumerate(headers):
        ws.write(0, col_idx, h, header_style)

    col_widths = [len(h) for h in headers]

    for row_idx, r in enumerate(results, start=1):
        email_sources = r.get("email_sources", {})
        if email_sources:
            sources_str = ", ".join([f"{em}: {pg}" for em, pg in email_sources.items()])
        else:
            sources_str = "N/A"

        all_emails_str = r.get("all_emails", "")
        if isinstance(all_emails_str, list):
            all_emails_str = ", ".join(all_emails_str)

        row_vals = [
            str(r.get("target_url", "")),
            str(r.get("primary_email", "") or "None"),
            str(all_emails_str or "None"),
            sources_str,
            str(r.get("pages_scanned", 0)),
            str(r.get("status", "Pending")),
            str(r.get("error_message", ""))
        ]

        for col_idx, val in enumerate(row_vals):
            ws.write(row_idx, col_idx, val, item_style)
            col_widths[col_idx] = max(col_widths[col_idx], min(len(val), 50))

    # Set column widths (character count * 256)
    for col_idx, w in enumerate(col_widths):
        ws.col(col_idx).width = min(max((w + 4) * 256, 3500), 12000)

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


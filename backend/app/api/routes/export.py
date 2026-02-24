"""Export API endpoints — PDF and Excel report generation."""

from io import BytesIO

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from ..schemas import ExportRequest
from ...reports.excel_report import generate_excel_report
from ...reports.pdf_report import generate_pdf_report

router = APIRouter(prefix="/api/export", tags=["export"])


@router.post("/excel")
def export_excel(req: ExportRequest):
    buf = BytesIO()
    generate_excel_report(buf, req)
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=sulfidity_report.xlsx"},
    )


@router.post("/pdf")
def export_pdf(req: ExportRequest):
    buf = BytesIO()
    generate_pdf_report(buf, req)
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=sulfidity_report.pdf"},
    )

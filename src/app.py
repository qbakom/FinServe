"""FinServe AI Credit Memo Generator — FastAPI application."""

import json
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.templating import Jinja2Templates

from src.models import ApplicationData, CreditMemo
from src.risk_engine import compute_risk_metrics
from src.memo_generator import generate_memo_sections
from src.pdf_export import render_memo_pdf

BASE_DIR = Path(__file__).resolve().parent.parent

app = FastAPI(title="FinServe Credit Memo Generator", version="1.0.0")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

SAMPLE_DATA_DIR = BASE_DIR / "sample_data"


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/samples")
async def list_samples():
    samples = []
    for f in sorted(SAMPLE_DATA_DIR.glob("*.json")):
        data = json.loads(f.read_text())
        samples.append({"filename": f.name, "client_name": data.get("client_name", f.stem)})
    return samples


@app.get("/api/samples/{filename}")
async def get_sample(filename: str):
    path = SAMPLE_DATA_DIR / filename
    if not path.exists():
        return {"error": "not found"}
    return json.loads(path.read_text())


def _build_memo(app_data: ApplicationData) -> CreditMemo:
    metrics = compute_risk_metrics(app_data)
    try:
        sections = generate_memo_sections(app_data, metrics)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    return CreditMemo(
        application=app_data,
        risk_metrics=metrics,
        executive_summary=sections["executive_summary"],
        financial_analysis=sections["financial_analysis"],
        risk_assessment=sections["risk_assessment"],
        collateral_analysis=sections["collateral_analysis"],
        recommendation=sections["recommendation"],
        conditions=sections["conditions"],
        generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    )


@app.post("/api/generate")
async def generate_memo(app_data: ApplicationData):
    memo = _build_memo(app_data)
    return memo.model_dump()


@app.post("/api/generate/pdf")
async def generate_pdf(app_data: ApplicationData):
    memo = _build_memo(app_data)
    pdf_bytes = render_memo_pdf(memo)
    filename = f"credit_memo_{app_data.client_name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.post("/api/memo/pdf")
async def memo_to_pdf(memo: CreditMemo):
    """Convert an already-generated memo to PDF without re-calling AI."""
    pdf_bytes = render_memo_pdf(memo)
    name = memo.application.client_name.replace(" ", "_")
    filename = f"credit_memo_{name}_{datetime.now().strftime('%Y%m%d')}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.app:app", host="0.0.0.0", port=8000, reload=True)

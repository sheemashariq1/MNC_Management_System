import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

import reports
from api.deps import CurrentUser, require_feature

router = APIRouter(prefix="/reports", tags=["Reports (admin)"])
_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _load_or_400():
    df = reports.load_employees()
    if df.empty:
        raise HTTPException(400, "There are no employees yet, so there is nothing to report.")
    return df


@router.get("/summary")
def summary(user: CurrentUser = Depends(require_feature("reports"))):
    """Department-wise count, total / average / median / highest salary, average tenure."""
    df = reports.load_employees()
    if df.empty:
        return []
    return json.loads(reports.build_summary(df).to_json(orient="records"))   # NaN -> null


@router.get("/export/excel")
def export_excel(user: CurrentUser = Depends(require_feature("reports"))):
    df = _load_or_400()
    path = reports.export_excel(df, reports.build_summary(df))
    return FileResponse(path, media_type=_XLSX, filename=path.name)


@router.get("/export/csv")
def export_csv(user: CurrentUser = Depends(require_feature("reports"))):
    path = reports.export_csv(_load_or_400())
    return FileResponse(path, media_type="text/csv", filename=path.name)

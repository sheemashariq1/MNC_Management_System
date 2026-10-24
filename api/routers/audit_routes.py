from typing import Optional

from fastapi import APIRouter, Depends, Query

import audit
from api.deps import CurrentUser, require_feature

router = APIRouter(prefix="/audit", tags=["Audit log (admin)"])


@router.get("")
def read_audit_log(limit: int = Query(50, ge=1, le=500), username: Optional[str] = None,
                   action: Optional[str] = None,
                   user: CurrentUser = Depends(require_feature("audit"))):
    """Newest first. `action` can be part of a name, e.g. LOGIN or EMP_."""
    return [{"id": i, "when": when, "username": who, "role": role,
             "action": act, "details": details}
            for i, when, who, role, act, details in audit.search(limit, username, action)]

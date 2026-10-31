from typing import Optional
from fastapi import APIRouter, Depends, Query, Response
import audit
from api.deps import CurrentUser, require_feature

router = APIRouter(prefix="/audit", tags=["Audit log (admin)"])


@router.get("")
def read_audit_log(response: Response, limit: int = Query(50, ge=1, le=500),
                   offset: int = Query(0, ge=0), username: Optional[str] = None,
                   action: Optional[str] = None,
                   user: CurrentUser = Depends(require_feature("audit"))):
    """Newest first. `action` can be part of a name, e.g. LOGIN or EMP_.

    Paged with `limit` and `offset`; the total number of matches is in the X-Total-Count header.
    """
    response.headers["X-Total-Count"] = str(audit.count(username, action))
    return [{"id": i, "when": when, "username": who, "role": role,
             "action": act, "details": details}
            for i, when, who, role, act, details in audit.search(limit, username, action, offset)]
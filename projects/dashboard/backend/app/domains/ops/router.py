from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.openapi.utils import get_openapi

from ...security.auth import require_session


router = APIRouter(prefix="/ops", tags=["ops"])  # under /api/v1


@router.get("/routes")
def list_routes(request: Request, sess=Depends(require_session)):
    app = request.app
    items: List[Dict[str, Any]] = []
    for r in app.routes:
        path = getattr(r, "path", None)
        name = getattr(r, "name", None)
        methods = sorted(getattr(r, "methods", set())) if hasattr(r, "methods") else []
        if not path or path.startswith("/openapi"):
            continue
        # Skip internal head/option only
        if methods and all(m in {"HEAD", "OPTIONS"} for m in methods):
            continue
        items.append({
            "path": path,
            "name": name,
            "methods": methods,
            "tags": getattr(r, "tags", []),
            "operationId": getattr(r, "operation_id", None) or getattr(r, "name", None),
        })
    return {"routes": items}


@router.post("/openapi")
def generate_openapi(
    request: Request,
    version: str = Query("3.1.0"),
    include_paths: Optional[List[str]] = Query(None),
    include_operation_ids: Optional[List[str]] = Query(None),
    sess=Depends(require_session),
):
    app = request.app
    schema = get_openapi(
        title=app.title,
        version=app.version,
        openapi_version=app.openapi_version,
        description=app.summary,
        routes=app.routes,
    )
    # Filter by paths/operationIds if provided
    if include_paths or include_operation_ids:
        paths = schema.get("paths", {})
        new_paths: Dict[str, Any] = {}
        for p, ops in paths.items():
            if include_paths and not any(p.startswith(ip) for ip in include_paths):
                continue
            if include_operation_ids:
                filtered_ops = {}
                for method, op in ops.items():
                    if isinstance(op, dict) and op.get("operationId") in include_operation_ids:
                        filtered_ops[method] = op
                if filtered_ops:
                    new_paths[p] = filtered_ops
            else:
                new_paths[p] = ops
        schema["paths"] = new_paths
    # Set requested OpenAPI version string (schema structure remains 3.1 compatible)
    if version in {"3.0.0", "3.0.1", "3.0.2", "3.0.3", "3.1.0"}:
        schema["openapi"] = version
    return schema


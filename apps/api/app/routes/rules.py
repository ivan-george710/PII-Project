from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.dependencies import get_db, require_manager
from app.schemas.rules import (
    CreateCustomRuleRequest,
    CustomRuleMutationResponse,
    DeleteCustomRuleResponse,
    PolicySnapshot,
    RulePreviewRequest,
    RulePreviewResponse,
    ToggleAllRequest,
    UpdateBuiltinsRequest,
    UpdateCustomRuleRequest,
)
from app.services.rules import (
    create_custom_rule,
    delete_custom_rule,
    get_snapshot,
    preview_rule,
    toggle_all,
    update_builtins,
    update_custom_rule,
)

router = APIRouter(prefix="/api/v1/rules", tags=["Company rules"])


@router.get("", response_model=PolicySnapshot)
def get_rules_policy(
    identity=Depends(require_manager),
    db: Session = Depends(get_db),
):
    return get_snapshot(db, identity.organization_id)


@router.patch("/builtins", response_model=PolicySnapshot)
def patch_builtins(
    body: UpdateBuiltinsRequest,
    identity=Depends(require_manager),
    db: Session = Depends(get_db),
):
    return update_builtins(db, identity.organization_id, body)


@router.post("/toggle-all", response_model=PolicySnapshot)
def post_toggle_all(
    body: ToggleAllRequest,
    identity=Depends(require_manager),
    db: Session = Depends(get_db),
):
    return toggle_all(db, identity.organization_id, body)


@router.post("/custom", response_model=CustomRuleMutationResponse, status_code=status.HTTP_201_CREATED)
def post_custom_rule(
    body: CreateCustomRuleRequest,
    identity=Depends(require_manager),
    db: Session = Depends(get_db),
):
    rule, policy_version = create_custom_rule(db, identity.organization_id, body)
    return CustomRuleMutationResponse(rule=rule, policy_version=policy_version)


@router.patch("/custom/{id}", response_model=CustomRuleMutationResponse)
def patch_custom_rule(
    id: UUID,
    body: UpdateCustomRuleRequest,
    identity=Depends(require_manager),
    db: Session = Depends(get_db),
):
    rule, policy_version = update_custom_rule(db, identity.organization_id, id, body)
    return CustomRuleMutationResponse(rule=rule, policy_version=policy_version)


@router.delete("/custom/{id}", response_model=DeleteCustomRuleResponse)
def delete_custom_rule_endpoint(
    id: UUID,
    expected_version: int = Query(..., ge=1),
    identity=Depends(require_manager),
    db: Session = Depends(get_db),
):
    deleted_id, policy_version = delete_custom_rule(
        db, identity.organization_id, id, expected_version
    )
    return DeleteCustomRuleResponse(deleted_id=deleted_id, policy_version=policy_version)


@router.post("/preview", response_model=RulePreviewResponse)
def post_preview_rule(
    body: RulePreviewRequest,
    identity=Depends(require_manager),
):
    return preview_rule(body)

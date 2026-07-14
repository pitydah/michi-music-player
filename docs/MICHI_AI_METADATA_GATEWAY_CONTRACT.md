# Michi AI Metadata Gateway Contract

## ProductionMetadataGateway

Located at `core/assistant_metadata_gateway.py`.

### Operations

| Operation | Method | Read/Write | Confirmation | Capability |
|-----------|--------|------------|--------------|------------|
| inspect_metadata | `inspect_metadata(track_id)` | READ | never | metadata.read |
| inspect_selection | `inspect_selection(track_ids)` | READ | never | metadata.read |
| build_proposal | `build_proposal(track_ids)` | READ | never | metadata.read |
| preview_changes | `preview_changes(review_id)` | READ | never | metadata.read |
| apply_review | `apply_review(review_id, confirmation_token)` | WRITE | required | metadata.modify |
| rollback | `rollback(operation_id, confirmation_token)` | WRITE | required | metadata.modify |
| check_consistency | `check_consistency(track_ids)` | READ | never | metadata.read |
| scan_duplicates | `scan_duplicates(track_ids)` | READ | never | metadata.read |

### Confirmation

Apply and rollback require a `confirmation_token` that:
- Is validated against a `ConfirmationService`
- Is single-use
- Is associated with the specific operation ID
- Expires after TTL

### Results

| Code | Description |
|------|-------------|
| COMPLETED | Operation finished successfully |
| JOB_STARTED | Async operation enqueued (batches) |
| TRACK_NOT_FOUND | Track ID not in library |
| INVALID_CONFIRMATION | Token invalid/expired/mismatched |
| REVIEW_NOT_FOUND | Review ID not found |
| ROLLED_BACK | Operation reverted |
| ROLLBACK_FAILED | Rollback could not complete |
| CAPABILITY_UNAVAILABLE | Service not available |
| CANCELLED | Operation cancelled |

### Sanitization

Responses strip: `filepath`, `path`, `full_path`, `token`, `password`, `api_key`, `secret`, `artwork_bytes`.

CLAIM_TO_FIELD = {
    "ADMIN": "is_admin",
    "MEDICAL_RECORDS": "has_medical_records",
}


def sync_claims_to_user(user, claims: dict, *, promote_only: bool = False):
    """Apply claim values to the corresponding User model fields.

    When promote_only=True, only set fields to True, never demote —
    demotion goes through the admin set-claims endpoint instead.
    Returns True if any field changed.
    """
    changed = False
    for claim, field in CLAIM_TO_FIELD.items():
        if claim not in claims:
            continue
        value = bool(claims[claim])
        if promote_only and not value:
            continue
        if getattr(user, field) != value:
            setattr(user, field, value)
            changed = True
    return changed

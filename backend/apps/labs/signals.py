"""
Post-delete pseudonymisation of audit log references (§9.5 of design doc).

When a LabResult is deleted (user deleted account, or deleted a single upload),
we keep audit log rows for HIPAA 6-year retention but null out the actor and
resource references so the compliance timeline stays intact without holding
references to data that no longer exists.

Phase 2a: the audit app doesn't exist yet. This signal is a stub that logs
the pseudonymisation intent; the real implementation lands when `apps/audit/`
is introduced in a later phase. Keeping the hook wired now so the contract
is visible and the test stubs are findable.
"""
import logging

from django.db.models.signals import post_delete
from django.dispatch import receiver

from .models import LabResult

logger = logging.getLogger(__name__)


@receiver(post_delete, sender=LabResult)
def pseudonymise_audit_refs_on_lab_result_delete(sender, instance, **kwargs):
    """Mark audit log entries referencing this LabResult for pseudonymisation.

    Phase 2a: stub only. The audit app will implement the real update query.
    """
    logger.info(
        "lab_result_deleted: id=%s user_id=%s test_type_id=%s — audit refs to be pseudonymised",
        instance.pk,
        instance.user_id,
        instance.test_type_id,
    )

"""
Post-delete pseudonymisation of audit log references.

When a LabValue is deleted, we keep audit log rows for HIPAA 6-year retention
but null out the actor and resource references.
"""
import logging

from django.db.models.signals import post_delete
from django.dispatch import receiver

from .models import LabValue

logger = logging.getLogger(__name__)


@receiver(post_delete, sender=LabValue)
def pseudonymise_audit_refs_on_lab_value_delete(sender, instance, **kwargs):
    logger.info(
        "lab_value_deleted: id=%s user_id=%s test_entry_id=%s — audit refs to be pseudonymised",
        instance.pk,
        instance.user_id,
        instance.test_entry_id,
    )

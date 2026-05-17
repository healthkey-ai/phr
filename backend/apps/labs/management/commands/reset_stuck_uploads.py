from django.core.management.base import BaseCommand

from apps.labs.models import UploadJob, UploadStatus


class Command(BaseCommand):
    help = "Reset stuck PROCESSING uploads and optionally re-queue them."

    def add_arguments(self, parser):
        parser.add_argument(
            "--requeue",
            action="store_true",
            help="Re-dispatch the Celery task after resetting.",
        )
        parser.add_argument(
            "--id",
            type=int,
            help="Reset a specific upload by ID.",
        )

    def handle(self, *args, **options):
        if options["id"]:
            qs = UploadJob.objects.filter(pk=options["id"])
        else:
            qs = UploadJob.objects.filter(status=UploadStatus.PROCESSING)

        count = qs.count()
        if not count:
            self.stdout.write("No stuck uploads found.")
            return

        for upload in qs:
            upload.status = UploadStatus.PENDING
            upload.error_message = ""
            upload.processing_started_at = None
            upload.save(update_fields=["status", "error_message", "processing_started_at"])
            self.stdout.write(f"  Reset upload {upload.pk} → PENDING")

            if options["requeue"]:
                from apps.labs.tasks import process_lab_upload
                task = process_lab_upload.delay(upload.pk)
                self.stdout.write(f"  Re-queued upload {upload.pk} as task {task.id}")

        self.stdout.write(self.style.SUCCESS(f"Done. Reset {count} upload(s)."))

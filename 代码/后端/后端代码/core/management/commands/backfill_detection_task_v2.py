import re

from django.core.management.base import BaseCommand

from core.models import DetectionResult, DetectionTask, FileManagement


LEGACY_PREFIX = re.compile(r"^\[(paper_aigc|resource_check):(\d+)\]\s*(.*)$")
TASK_TYPES = {"image_detection", "paper_aigc", "resource_check", "review_detection"}


class Command(BaseCommand):
    help = (
        "Backfill DetectionTask v2 data fields: task_type, paper_file_id, error_message, "
        "and normalize legacy prefixed task_name."
    )

    def handle(self, *args, **options):
        image_task_ids = set(
            DetectionResult.objects.exclude(detection_task_id__isnull=True).values_list("detection_task_id", flat=True)
        )
        existing_file_ids = set(FileManagement.objects.values_list("id", flat=True))

        updated = 0
        for task in DetectionTask.objects.all().iterator():
            original = {
                "task_type": getattr(task, "task_type", None),
                "paper_file_id": getattr(task, "paper_file_id", None),
                "error_message": getattr(task, "error_message", ""),
                "task_name": task.task_name,
            }

            inferred_type = original["task_type"] if original["task_type"] in TASK_TYPES else None
            inferred_file_id = original["paper_file_id"]
            normalized_name = task.task_name

            match = LEGACY_PREFIX.match(task.task_name or "")
            if match:
                legacy_type, legacy_file_id, display_name = match.groups()
                inferred_type = inferred_type or legacy_type
                if inferred_file_id is None:
                    candidate_id = int(legacy_file_id)
                    if candidate_id in existing_file_ids:
                        inferred_file_id = candidate_id
                normalized_name = (display_name or "").strip() or task.task_name

            if inferred_type is None:
                if task.id in image_task_ids:
                    inferred_type = "image_detection"
                else:
                    inferred_type = "image_detection"

            if inferred_type in {"paper_aigc", "resource_check"} and inferred_file_id is None:
                # Paper tasks should have explicit paper_file if possible.
                # Keep null when no reliable source exists; caller can fix manually.
                pass

            if task.status == "failed" and not (task.error_message or "").strip():
                task.error_message = "任务执行失败，请重试或联系管理员。"
            elif task.status != "failed" and (task.error_message or "").strip():
                # Non-failed tasks should not carry stale errors.
                task.error_message = ""

            task.task_type = inferred_type
            task.paper_file_id = inferred_file_id
            task.task_name = normalized_name

            changed = (
                task.task_type != original["task_type"]
                or task.paper_file_id != original["paper_file_id"]
                or task.error_message != (original["error_message"] or "")
                or task.task_name != original["task_name"]
            )
            if changed:
                task.save(update_fields=["task_type", "paper_file", "error_message", "task_name"])
                updated += 1

        self.stdout.write(self.style.SUCCESS(f"[backfill_detection_task_v2] updated rows: {updated}"))

from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = (
        "Schema migration script for DetectionTask v2: "
        "add task_type / paper_file_id / error_message columns if missing."
    )

    def _existing_columns(self, table_name):
        with connection.cursor() as cursor:
            description = connection.introspection.get_table_description(cursor, table_name)
        return {col.name for col in description}

    def _column_exists(self, table_name, column_name):
        return column_name in self._existing_columns(table_name)

    def _index_exists(self, index_name):
        vendor = connection.vendor
        with connection.cursor() as cursor:
            if vendor == "sqlite":
                cursor.execute(
                    "SELECT name FROM sqlite_master WHERE type='index' AND name=%s",
                    [index_name],
                )
            elif vendor == "mysql":
                cursor.execute(
                    """
                    SELECT INDEX_NAME
                    FROM INFORMATION_SCHEMA.STATISTICS
                    WHERE TABLE_SCHEMA = DATABASE()
                      AND INDEX_NAME = %s
                    """,
                    [index_name],
                )
            else:
                return False
            return cursor.fetchone() is not None

    def _add_task_type(self):
        with connection.cursor() as cursor:
            cursor.execute(
                """
                ALTER TABLE core_detectiontask
                ADD COLUMN task_type VARCHAR(32) NOT NULL DEFAULT 'image_detection'
                """
            )

    def _add_paper_file_id(self):
        with connection.cursor() as cursor:
            cursor.execute(
                """
                ALTER TABLE core_detectiontask
                ADD COLUMN paper_file_id BIGINT NULL
                """
            )

    def _add_error_message(self):
        with connection.cursor() as cursor:
            cursor.execute(
                """
                ALTER TABLE core_detectiontask
                ADD COLUMN error_message TEXT NOT NULL DEFAULT ''
                """
            )

    def _create_paper_file_index(self):
        with connection.cursor() as cursor:
            cursor.execute(
                """
                CREATE INDEX core_detectiontask_paper_file_id_idx
                ON core_detectiontask (paper_file_id)
                """
            )

    def _create_user_upload_index(self):
        with connection.cursor() as cursor:
            cursor.execute(
                """
                CREATE INDEX dt_user_upload_idx
                ON core_detectiontask (user_id, upload_time)
                """
            )

    def _create_type_status_index(self):
        with connection.cursor() as cursor:
            cursor.execute(
                """
                CREATE INDEX dt_type_status_idx
                ON core_detectiontask (task_type, status)
                """
            )

    def _create_fk_if_mysql(self):
        if connection.vendor != "mysql":
            return
        with connection.cursor() as cursor:
            try:
                cursor.execute(
                    """
                    ALTER TABLE core_detectiontask
                    ADD CONSTRAINT core_detectiontask_paper_file_id_fk
                    FOREIGN KEY (paper_file_id) REFERENCES core_filemanagement (id)
                    ON DELETE SET NULL
                    """
                )
            except Exception:
                # Keep command idempotent and tolerant across environments.
                pass

    def handle(self, *args, **options):
        table = "core_detectiontask"
        created = []
        skipped = []

        if not self._column_exists(table, "task_type"):
            self._add_task_type()
            created.append("task_type")
        else:
            skipped.append("task_type")

        if not self._column_exists(table, "paper_file_id"):
            self._add_paper_file_id()
            created.append("paper_file_id")
        else:
            skipped.append("paper_file_id")

        if not self._column_exists(table, "error_message"):
            self._add_error_message()
            created.append("error_message")
        else:
            skipped.append("error_message")

        if not self._index_exists("core_detectiontask_paper_file_id_idx"):
            self._create_paper_file_index()
            created.append("core_detectiontask_paper_file_id_idx")
        else:
            skipped.append("core_detectiontask_paper_file_id_idx")

        if not self._index_exists("dt_user_upload_idx"):
            self._create_user_upload_index()
            created.append("dt_user_upload_idx")
        else:
            skipped.append("dt_user_upload_idx")

        if not self._index_exists("dt_type_status_idx"):
            self._create_type_status_index()
            created.append("dt_type_status_idx")
        else:
            skipped.append("dt_type_status_idx")

        self._create_fk_if_mysql()

        self.stdout.write(self.style.SUCCESS(f"[migrate_detection_task_v2] created: {created or 'none'}"))
        self.stdout.write(self.style.WARNING(f"[migrate_detection_task_v2] skipped: {skipped or 'none'}"))

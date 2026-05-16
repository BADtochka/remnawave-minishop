import io
import os
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from startup_banner import print_startup_banner


class StartupBannerTests(unittest.TestCase):
    def test_startup_banner_marks_services_without_mojibake(self):
        for service in ("frontend", "backend", "worker", "migrate"):
            with self.subTest(service=service):
                buffer = io.StringIO()

                with (
                    patch.dict(
                        os.environ,
                        {
                            "IMAGE_TAG": "test-tag",
                            "POSTGRES_HOST": "postgres",
                            "POSTGRES_DB": "postgres",
                            "REDIS_URL": "redis://redis:6379/0",
                        },
                        clear=False,
                    ),
                    redirect_stdout(buffer),
                ):
                    print_startup_banner(service)

                output = buffer.getvalue()
                self.assertIn(f"container :: {service.upper()}", output)
                self.assertIn("image tag :: test-tag", output)
                self.assertIn("remnawave-minishop", output)
                self.assertIn("███", output)
                self.assertNotIn("в", output)

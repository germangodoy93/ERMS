"""Shared test setup.

Unit tests never touch a real database: a placeholder DATABASE_URL is set before the
application is imported. Integration tests use ERMS_TEST_DATABASE_URL instead.
"""

import os

os.environ.setdefault("DATABASE_URL", "postgresql://unit:unit@127.0.0.1:1/unit")
os.environ.setdefault("LOG_JSON", "false")

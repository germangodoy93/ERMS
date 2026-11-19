"""Export the OpenAPI schema to a file without starting the server.

Usage (from backend/):
    uv run python -m scripts.export_openapi ../docs/api/openapi.json

The frontend generates its TypeScript types from this file (`npm run api:types`),
so the API contract has a single source of truth: the FastAPI code.
"""

import json
import os
import sys
from pathlib import Path


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit("usage: python -m scripts.export_openapi <output.json>")

    # The schema does not depend on the database; a placeholder URL avoids requiring one.
    os.environ.setdefault("DATABASE_URL", "postgresql://openapi:openapi@127.0.0.1:1/openapi")
    from app.main import create_app  # imported here: must run after the env setup above

    output = Path(sys.argv[1])
    output.parent.mkdir(parents=True, exist_ok=True)
    schema = create_app().openapi()
    output.write_text(
        json.dumps(schema, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n"
    )
    print(f"OpenAPI schema written to {output}")


if __name__ == "__main__":
    main()

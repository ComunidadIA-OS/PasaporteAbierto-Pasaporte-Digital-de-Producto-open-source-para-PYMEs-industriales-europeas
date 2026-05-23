"""Borra y recrea la DB desde cero usando Alembic."""

import subprocess
import sys
from pathlib import Path

# Permite ejecutar `uv run python -m scripts.reset_db` desde backend/ sin instalar el paquete.
_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from app.config import settings  # noqa: E402


def main() -> None:
    if settings.database_url.startswith("sqlite:///"):
        db_path = Path(settings.database_url.replace("sqlite:///", ""))
        if db_path.exists():
            db_path.unlink()
            print(f"Borrado: {db_path}")
    subprocess.run(["uv", "run", "alembic", "upgrade", "head"], check=True)
    print("Migraciones aplicadas.")


if __name__ == "__main__":
    main()

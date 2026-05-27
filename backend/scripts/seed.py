"""Seed mínimo: una sesión demo en estado paso 1."""

import sys
from datetime import datetime
from pathlib import Path

# Permite ejecutar `uv run python -m scripts.seed` desde backend/ sin instalar el paquete.
_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from sqlmodel import Session  # noqa: E402

from app.db.session import engine, init_db  # noqa: E402
from app.models import WizardSession  # noqa: E402


def main() -> None:
    init_db()
    with Session(engine) as s:
        demo = WizardSession(
            id="demo-session-001",
            progress={"step": 1, "description": "Batería industrial de demo"},
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        s.merge(demo)
        s.commit()
    print("Seed completado: sesión demo-session-001")


if __name__ == "__main__":
    main()

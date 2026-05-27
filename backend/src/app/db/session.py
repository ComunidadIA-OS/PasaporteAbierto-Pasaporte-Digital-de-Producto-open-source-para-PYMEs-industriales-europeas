from collections.abc import Iterator

from sqlmodel import Session, SQLModel, create_engine

from app.config import settings

engine = create_engine(
    settings.database_url,
    # `startswith("sqlite:")` (con dos puntos) en lugar de `startswith("sqlite")`
    # — más preciso, evita falsos positivos con URLs hipotéticas como
    # `sqlitedb://` o `sqlitex://` que no existen hoy pero podrían en el futuro.
    connect_args={"check_same_thread": False}
    if settings.database_url.startswith("sqlite:")
    else {},
)


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session


def init_db() -> None:
    """Sólo para tests/desarrollo — en runtime se usa Alembic."""
    SQLModel.metadata.create_all(engine)

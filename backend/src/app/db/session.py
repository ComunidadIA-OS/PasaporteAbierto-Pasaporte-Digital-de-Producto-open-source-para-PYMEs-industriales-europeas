from collections.abc import Iterator

from sqlmodel import Session, SQLModel, create_engine, text

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


def _ensure_sqlite_columns() -> None:
    """Migración ligera idempotente para BDs SQLite ya creadas.

    `create_all` crea tablas nuevas (`users`, `auth_sessions`) pero NO altera
    tablas existentes, así que una BD anterior al login se quedaría sin la
    columna `sessions.user_id`. Como el proyecto no usa Alembic en la práctica
    (las tablas nacen de `create_all` al arrancar), añadimos la columna a mano
    si falta. `ADD COLUMN ... NULL` es barato y no reescribe la tabla en SQLite.
    """
    if not settings.database_url.startswith("sqlite:"):
        return
    with engine.begin() as conn:
        cols = {row[1] for row in conn.execute(text("PRAGMA table_info('sessions')"))}
        if cols and "user_id" not in cols:
            conn.execute(text("ALTER TABLE sessions ADD COLUMN user_id VARCHAR"))


def init_db() -> None:
    """Crea las tablas que falten y aplica migraciones ligeras de columnas.

    Se invoca en el lifespan de FastAPI. `create_all` es idempotente; la
    comprobación de columnas cubre el caso de una BD preexistente.
    """
    # Importa los modelos para registrarlos en la metadata antes de create_all.
    import app.models  # noqa: F401

    SQLModel.metadata.create_all(engine)
    _ensure_sqlite_columns()

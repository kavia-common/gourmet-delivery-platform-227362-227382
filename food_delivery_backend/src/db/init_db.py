from sqlalchemy import text

from src.db.models import Base
from src.db.session import get_engine


# PUBLIC_INTERFACE
def create_all_tables() -> None:
    """Create all DB tables if the engine is configured."""
    engine = get_engine()
    if engine is None:
        return
    Base.metadata.create_all(bind=engine)

    # Tiny sanity query ensures connection works; helpful for CI diagnostics.
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
        conn.commit()

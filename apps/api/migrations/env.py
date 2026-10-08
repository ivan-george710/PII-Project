from alembic import context
from sqlalchemy import create_engine

from app.config import get_settings
from app.db.models import Organization

url = get_settings().sqlalchemy_url
if context.is_offline_mode():
    context.configure(
        url=url, target_metadata=Organization.metadata, literal_binds=True
    )
    with context.begin_transaction():
        context.run_migrations()
else:
    engine = create_engine(url)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=Organization.metadata)
        with context.begin_transaction():
            context.run_migrations()

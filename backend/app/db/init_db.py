import logging
from app.db.session import engine, Base
# Import models here so Base.metadata knows about them
from app.models import Batch, Certificate

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_db() -> None:
    # Later when using alembic for real migrations, drop Base.metadata.create_all
    logger.info("Creating initial tables in database...")
    Base.metadata.create_all(bind=engine)
    logger.info("Tables created.")

if __name__ == "__main__":
    init_db()

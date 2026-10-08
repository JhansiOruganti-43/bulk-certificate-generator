import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.session import Base
from app.models.batch import Batch
from app.models.certificate import Certificate
from app.models.enums import BatchStatus, CertificateStatus

# Use an in-memory SQLite for tests
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="module")
def db_session():
    # Setup test DB tables
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

def test_batch_creation(db_session):
    new_batch = Batch(total_recipients=5)
    db_session.add(new_batch)
    db_session.commit()
    db_session.refresh(new_batch)

    assert new_batch.id is not None
    assert new_batch.status == BatchStatus.PENDING
    assert new_batch.total_recipients == 5
    assert new_batch.created_at is not None

def test_certificate_creation_and_relationship(db_session):
    batch = Batch()
    db_session.add(batch)
    db_session.commit()
    
    cert = Certificate(
        batch_id=batch.id,
        recipient_name="John Doe",
        recipient_email="john@example.com",
        course_name="AEREO Internship"
    )
    db_session.add(cert)
    db_session.commit()
    db_session.refresh(cert)

    assert cert.id is not None
    assert cert.status == CertificateStatus.PENDING
    assert cert.batch_id == batch.id

    # Test relationship from batch side
    db_session.refresh(batch)
    assert len(batch.certificates) >= 1
    assert batch.certificates[-1].recipient_name == "John Doe"

def test_enum_saving(db_session):
    batch = Batch(status=BatchStatus.COMPLETED)
    db_session.add(batch)
    db_session.commit()
    db_session.refresh(batch)
    
    # We should get a BatchStatus Enum back
    assert batch.status == BatchStatus.COMPLETED

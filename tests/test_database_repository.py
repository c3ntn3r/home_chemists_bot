import pytest
from repositories.database_repository import DatabaseRepository, Medication
from datetime import datetime, timedelta

@pytest.fixture
def db_repository():
    return DatabaseRepository(":memory:")

def test_add_medication(db_repository):
    # Arrange
    user_id = 1
    name = "Test Med"
    expiry_date = (datetime.now() + timedelta(days=30)).isoformat()
    quantity = 3

    # Act
    db_repository.create_tables()
    db_repository.add_medication(user_id, name, expiry_date, quantity)
    medications = db_repository.list_medications(user_id)

    # Assert
    assert len(medications) == 1
    assert medications[0].name == name
    assert medications[0].quantity == quantity 
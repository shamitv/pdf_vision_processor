
import enum
from sqlalchemy import Column, Integer, String, Enum
from sqlalchemy.orm import declarative_base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

class ProcessingStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

Base = declarative_base()

class TestModel(Base):
    __tablename__ = 'test_model'
    id = Column(Integer, primary_key=True)
    status = Column(Enum(ProcessingStatus))

def test_enum():
    try:
        print(f"Lookup 'pending': {ProcessingStatus('pending')}")
    except Exception as e:
        print(f"Error lookup 'pending': {e}")

    try:
        print(f"Lookup 'PENDING': {ProcessingStatus('PENDING')}")
    except Exception as e:
        print(f"Error lookup 'PENDING': {e}")
        
    print("-" * 20)
    # Test DB interaction logic
    # SA usually does: ProcessingStatus(value_from_db)
    
if __name__ == "__main__":
    test_enum()

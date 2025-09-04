"""
Database connection management for leadgen module within salesbot.
Uses salesbot's existing database connection.
"""
from contextlib import contextmanager
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError
from app.database import get_shared_engine
import logging
from typing import Generator

# Set up logging
logger = logging.getLogger(__name__)

class DatabaseManager:
    """Database connection and session management using salesbot's shared engine"""
    
    def __init__(self):
        """Initialize database manager with salesbot's shared engine"""
        self.engine = get_shared_engine()
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
    
    @contextmanager
    def get_db_session(self) -> Generator[Session, None, None]:
        """Context manager for database sessions"""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            session.close()
    
    def health_check(self) -> dict:
        """Perform database health check"""
        try:
            with self.get_db_session() as session:
                session.execute("SELECT 1")
                return {"status": "healthy", "message": "Database connection successful"}
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {"status": "unhealthy", "message": str(e)}

# Global database manager instance
db_manager = DatabaseManager()

def get_database_manager() -> DatabaseManager:
    """Get the database manager instance"""
    return db_manager

@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """Get a database session (context manager)"""
    with db_manager.get_db_session() as session:
        yield session

def health_check() -> dict:
    """Perform database health check"""
    return db_manager.health_check()
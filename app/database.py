"""
Shared database connection management for Railway PostgreSQL.
This module provides a single, shared database engine to prevent connection limit issues.
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
import threading

class DatabaseManager:
    """Singleton database manager to share a single engine across all models."""
    
    _instance = None
    _lock = threading.Lock()
    _engine = None
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(DatabaseManager, cls).__new__(cls)
        return cls._instance
    
    def get_engine(self):
        """Get the shared database engine, creating it if necessary."""
        if self._engine is None:
            with self._lock:
                if self._engine is None:
                    self._create_engine()
        return self._engine
    
    def _create_engine(self):
        """Create the shared database engine with minimal connection usage."""
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            raise ValueError("DATABASE_URL environment variable not set")
        
        # Use minimal connection pool settings for Railway
        self._engine = create_engine(
            database_url,
            pool_size=1,                    # Only 1 permanent connection
            max_overflow=1,                 # Only 1 overflow connection
            pool_pre_ping=True,             # Verify connections before use
            pool_recycle=900,               # Recycle connections every 15 minutes
            pool_timeout=30,                # 30 second timeout
            poolclass=StaticPool,           # Use static pool for better control
            connect_args={
                "options": "-c statement_timeout=30000"  # 30 second statement timeout
            }
        )
        print(f"✅ Created shared database engine with minimal connection pool")
    
    def close_engine(self):
        """Close the shared engine and all connections."""
        if self._engine:
            with self._lock:
                if self._engine:
                    self._engine.dispose()
                    self._engine = None
                    print("🔄 Closed shared database engine")

# Global database manager instance
db_manager = DatabaseManager()

def get_shared_engine():
    """Get the shared database engine."""
    return db_manager.get_engine()

def close_shared_engine():
    """Close the shared database engine."""
    db_manager.close_engine()
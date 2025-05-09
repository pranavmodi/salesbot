import sqlite3
from datetime import datetime
from typing import Optional

class InteractionsDB:
    def __init__(self, db_path: str = "interactions.db"):
        self.db_path = db_path
        self.init_db()

    def init_db(self):
        """Initialize the database and create tables if they don't exist."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS interactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    lead_email TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    campaign_id TEXT,
                    details TEXT,
                    CONSTRAINT valid_email CHECK (lead_email LIKE '%@%.%')
                )
            ''')
            # Create an index on lead_email for faster lookups
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_lead_email 
                ON interactions(lead_email)
            ''')
            conn.commit()

    def add_interaction(
        self,
        lead_email: str,
        event_type: str,
        campaign_id: Optional[str] = None,
        details: Optional[str] = None
    ) -> bool:
        """
        Add a new interaction to the database.
        
        Args:
            lead_email: Email address of the lead
            event_type: Type of interaction (e.g., 'email_sent', 'email_opened')
            campaign_id: Optional campaign identifier
            details: Optional additional details about the interaction
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            timestamp = datetime.now().isoformat()
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO interactions 
                    (timestamp, lead_email, event_type, campaign_id, details)
                    VALUES (?, ?, ?, ?, ?)
                ''', (timestamp, lead_email, event_type, campaign_id, details))
                conn.commit()
                return True
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            return False

    def get_lead_interactions(self, lead_email: str) -> list:
        """
        Get all interactions for a specific lead.
        
        Args:
            lead_email: Email address of the lead
            
        Returns:
            list: List of interaction records
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT timestamp, event_type, campaign_id, details 
                FROM interactions 
                WHERE lead_email = ?
                ORDER BY timestamp DESC
            ''', (lead_email,))
            return cursor.fetchall()

    def get_recent_interactions(self, limit: int = 50) -> list:
        """
        Get recent interactions across all leads.
        
        Args:
            limit: Maximum number of interactions to return
            
        Returns:
            list: List of recent interaction records
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT timestamp, lead_email, event_type, campaign_id, details 
                FROM interactions 
                ORDER BY timestamp DESC 
                LIMIT ?
            ''', (limit,))
            return cursor.fetchall()

# Example usage:
if __name__ == "__main__":
    # Initialize the database
    db = InteractionsDB()
    
    # Example: Add a test interaction
    success = db.add_interaction(
        lead_email="test@example.com",
        event_type="email_sent",
        campaign_id="CAMP001",
        details="Initial cold email sent"
    )
    print(f"Interaction added successfully: {success}")
    
    # Example: Retrieve interactions for the test lead
    interactions = db.get_lead_interactions("test@example.com")
    print(f"Found {len(interactions)} interactions for test@example.com") 
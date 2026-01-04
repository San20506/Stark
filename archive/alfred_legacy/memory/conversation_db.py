#!/usr/bin/env python3
"""
ConversationDatabase - SQLite-based persistent storage for ALFRED conversations

Stores conversation history locally for long-term memory and context preservation.
Database location: ~/.alfred/conversations.db
"""

import sqlite3
import logging
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
import os

logger = logging.getLogger("ConversationDB")


class ConversationDatabase:
    """Manages persistent storage of conversation history using SQLite."""
    
    DEFAULT_DB_DIR = Path.home() / ".alfred"
    DEFAULT_DB_NAME = "conversations.db"
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize database connection.
        
        Args:
            db_path: Custom database path. If None, uses ~/.alfred/conversations.db
        """
        if db_path is None:
            # Create .alfred directory if it doesn't exist
            self.DEFAULT_DB_DIR.mkdir(parents=True, exist_ok=True)
            db_path = str(self.DEFAULT_DB_DIR / self.DEFAULT_DB_NAME)
        
        self.db_path = db_path
        self.conn: Optional[sqlite3.Connection] = None
        self.current_conversation_id: Optional[int] = None
        
        self._connect()
        self._create_tables()
        
        logger.info(f"✅ ConversationDatabase initialized: {self.db_path}")
    
    def _connect(self):
        """Establish database connection."""
        try:
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self.conn.row_factory = sqlite3.Row  # Enable dict-like access
            logger.debug(f"Connected to database: {self.db_path}")
        except Exception as e:
            logger.exception(f"Failed to connect to database: {e}")
            raise
    
    def _create_tables(self):
        """Create database schema if it doesn't exist."""
        if not self.conn:
            return
        
        try:
            cursor = self.conn.cursor()
            
            # Conversations table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    started_at TEXT NOT NULL,
                    last_updated TEXT NOT NULL
                )
            """)
            
            # Exchanges table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS exchanges (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id INTEGER NOT NULL,
                    user_message TEXT NOT NULL,
                    assistant_message TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    FOREIGN KEY (conversation_id) REFERENCES conversations (id)
                )
            """)
            
            # Index for faster queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_conversation_timestamp 
                ON exchanges(conversation_id, timestamp)
            """)
            
            # User preferences table for personality adaptation
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_preferences (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            
            self.conn.commit()
            logger.debug("Database schema initialized")
            
        except Exception as e:
            logger.exception(f"Failed to create tables: {e}")
            raise
    
    def start_conversation(self) -> int:
        """
        Create a new conversation entry.
        
        Returns:
            Conversation ID
        """
        if not self.conn:
            raise RuntimeError("Database not connected")
        
        try:
            cursor = self.conn.cursor()
            now = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT INTO conversations (started_at, last_updated)
                VALUES (?, ?)
            """, (now, now))
            
            self.conn.commit()
            conversation_id = cursor.lastrowid
            self.current_conversation_id = conversation_id
            
            logger.info(f"Started new conversation: ID={conversation_id}")
            return conversation_id
            
        except Exception as e:
            logger.exception(f"Failed to start conversation: {e}")
            raise
    
    def save_exchange(self, conversation_id: int, user_message: str, assistant_message: str):
        """
        Save a single exchange to the database.
        
        Args:
            conversation_id: ID of the conversation
            user_message: User's input
            assistant_message: Alfred's response
        """
        if not self.conn:
            logger.warning("Database not connected, skipping save")
            return
        
        try:
            cursor = self.conn.cursor()
            timestamp = datetime.now().isoformat()
            
            # Insert exchange
            cursor.execute("""
                INSERT INTO exchanges (conversation_id, user_message, assistant_message, timestamp)
                VALUES (?, ?, ?, ?)
            """, (conversation_id, user_message, assistant_message, timestamp))
            
            # Update conversation last_updated
            cursor.execute("""
                UPDATE conversations
                SET last_updated = ?
                WHERE id = ?
            """, (timestamp, conversation_id))
            
            self.conn.commit()
            logger.debug(f"Saved exchange to conversation {conversation_id}")
            
        except Exception as e:
            logger.exception(f"Failed to save exchange: {e}")
    
    def load_recent_exchanges(self, conversation_id: int, limit: int = 10) -> List[Dict[str, str]]:
        """
        Load recent exchanges from a conversation.
        
        Args:
            conversation_id: ID of the conversation
            limit: Maximum number of exchanges to load
            
        Returns:
            List of exchanges in format [{"user": "...", "assistant": "...", "timestamp": "..."}]
        """
        if not self.conn:
            logger.warning("Database not connected, returning empty history")
            return []
        
        try:
            cursor = self.conn.cursor()
            
            cursor.execute("""
                SELECT user_message, assistant_message, timestamp
                FROM exchanges
                WHERE conversation_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (conversation_id, limit))
            
            rows = cursor.fetchall()
            
            # Convert to list of dicts, reverse to get chronological order
            exchanges = [
                {
                    "user": row["user_message"],
                    "assistant": row["assistant_message"],
                    "timestamp": row["timestamp"]
                }
                for row in reversed(rows)
            ]
            
            logger.debug(f"Loaded {len(exchanges)} exchanges from conversation {conversation_id}")
            return exchanges
            
        except Exception as e:
            logger.exception(f"Failed to load exchanges: {e}")
            return []
    
    def get_active_conversation(self) -> Optional[int]:
        """
        Get the most recent conversation ID.
        
        Returns:
            Conversation ID or None if no conversations exist
        """
        if not self.conn:
            return None
        
        try:
            cursor = self.conn.cursor()
            
            cursor.execute("""
                SELECT id FROM conversations
                ORDER BY last_updated DESC
                LIMIT 1
            """)
            
            row = cursor.fetchone()
            if row:
                conversation_id = row["id"]
                self.current_conversation_id = conversation_id
                logger.debug(f"Active conversation: ID={conversation_id}")
                return conversation_id
            else:
                logger.debug("No active conversation found")
                return None
                
        except Exception as e:
            logger.exception(f"Failed to get active conversation: {e}")
            return None
    
    def get_conversation_count(self) -> int:
        """Get total number of conversations."""
        if not self.conn:
            return 0
        
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT COUNT(*) as count FROM conversations")
            row = cursor.fetchone()
            return row["count"] if row else 0
        except Exception as e:
            logger.exception(f"Failed to count conversations: {e}")
            return 0
    
    def get_exchange_count(self, conversation_id: Optional[int] = None) -> int:
        """
        Get total number of exchanges.
        
        Args:
            conversation_id: If provided, count only for this conversation
        """
        if not self.conn:
            return 0
        
        try:
            cursor = self.conn.cursor()
            
            if conversation_id:
                cursor.execute("""
                    SELECT COUNT(*) as count FROM exchanges 
                    WHERE conversation_id = ?
                """, (conversation_id,))
            else:
                cursor.execute("SELECT COUNT(*) as count FROM exchanges")
            
            row = cursor.fetchone()
            return row["count"] if row else 0
        except Exception as e:
            logger.exception(f"Failed to count exchanges: {e}")
            return 0
    
    def close(self):
        """Close database connection."""
        if self.conn:
            try:
                self.conn.close()
                logger.info("Database connection closed")
            except Exception as e:
                logger.exception(f"Error closing database: {e}")
            finally:
                self.conn = None
    
    def save_preference(self, key: str, value: str):
        """Save or update a user preference."""
        if not self.conn:
            logger.warning("Database not connected, skipping preference save")
            return
        
        try:
            cursor = self.conn.cursor()
            timestamp = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT OR REPLACE INTO user_preferences (key, value, updated_at)
                VALUES (?, ?, ?)
            """, (key, value, timestamp))
            
            self.conn.commit()
            logger.debug(f"Saved preference: {key} = {value}")
        except Exception as e:
            logger.exception(f"Failed to save preference: {e}")
    
    def get_preference(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Retrieve a user preference value."""
        if not self.conn:
            return default
        
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT value FROM user_preferences WHERE key = ?
            """, (key,))
            
            row = cursor.fetchone()
            return row["value"] if row else default
        except Exception as e:
            logger.exception(f"Failed to get preference: {e}")
            return default
    
    def get_all_preferences(self) -> Dict[str, str]:
        """Get all user preferences."""
        if not self.conn:
            return {}
        
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT key, value FROM user_preferences")
            
            rows = cursor.fetchall()
            return {row["key"]: row["value"] for row in rows}
        except Exception as e:
            logger.exception(f"Failed to get preferences: {e}")
            return {}
    
    def __del__(self):
        """Cleanup on deletion."""
        self.close()


# Note for future enhancements:
# - Add data compression for old conversations (gzip TEXT fields)
# - Add conversation search by keyword
# - Add export to JSON/CSV functionality
# - Add encryption at rest option

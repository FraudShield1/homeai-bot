"""
Conversation Memory Module for HomeAI Bot
Handles storing and retrieving conversation history for context-aware responses
"""

import logging
from typing import List, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class ConversationMemory:
    """Manages conversation history for context-aware responses"""
    
    def __init__(self, database):
        """
        Initialize conversation memory
        
        Args:
            database: Database instance
        """
        self.db = database
        self._ensure_table()
    
    def _ensure_table(self):
        """Ensure conversation_history table exists"""
        try:
            conn = self.db._get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS conversation_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    message TEXT,
                    response TEXT,
                    message_type TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            ''')
            conn.commit()
            logger.info("Conversation history table ready")
        except Exception as e:
            logger.error(f"Error creating conversation_history table: {e}")
    
    def add_message(self, user_id: int, message: str, response: str, message_type: str = "chat") -> bool:
        """
        Store a conversation message and response
        
        Args:
            user_id: Telegram user ID
            message: User's message
            response: Bot's response
            message_type: Type of message (chat, command, etc.)
            
        Returns:
            True if successful
        """
        try:
            conn = self.db._get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO conversation_history (user_id, message, response, message_type)
                VALUES (?, ?, ?, ?)
            ''', (user_id, message, response, message_type))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error storing conversation: {e}")
            return False
    
    def get_history(self, user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent conversation history for a user
        
        Args:
            user_id: Telegram user ID
            limit: Number of recent messages to retrieve
            
        Returns:
            List of conversation messages (chronological order)
        """
        try:
            conn = self.db._get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT message, response, message_type, timestamp 
                FROM conversation_history 
                WHERE user_id = ? 
                ORDER BY timestamp DESC 
                LIMIT ?
            ''', (user_id, limit))
            
            # Reverse to get chronological order (oldest first)
            history = [dict(row) for row in cursor.fetchall()]
            history.reverse()
            return history
        except Exception as e:
            logger.error(f"Error retrieving conversation history: {e}")
            return []
    
    def format_for_llm(self, history: List[Dict[str, Any]]) -> str:
        """
        Format conversation history for LLM context
        
        Args:
            history: List of conversation messages
            
        Returns:
            Formatted string for LLM prompt
        """
        if not history:
            return ""
        
        formatted = "\n**Recent Conversation:**\n"
        for msg in history:
            formatted += f"User: {msg['message']}\n"
            formatted += f"Assistant: {msg['response']}\n\n"
        
        return formatted
    
    def clear_old_messages(self, days: int = 7) -> int:
        """
        Clear conversation history older than specified days
        
        Args:
            days: Number of days to keep
            
        Returns:
            Number of messages deleted
        """
        try:
            conn = self.db._get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                DELETE FROM conversation_history 
                WHERE timestamp < datetime('now', '-' || ? || ' days')
            ''', (days,))
            conn.commit()
            deleted = cursor.rowcount
            logger.info(f"Cleared {deleted} old conversation messages")
            return deleted
        except Exception as e:
            logger.error(f"Error clearing old conversations: {e}")
            return 0
    
    def get_stats(self, user_id: int) -> Dict[str, Any]:
        """
        Get conversation statistics for a user
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            Dictionary with stats
        """
        try:
            conn = self.db._get_connection()
            cursor = conn.cursor()
            
            # Total messages
            cursor.execute('SELECT COUNT(*) as total FROM conversation_history WHERE user_id = ?', (user_id,))
            total = cursor.fetchone()['total']
            
            # Messages today
            cursor.execute('''
                SELECT COUNT(*) as today FROM conversation_history 
                WHERE user_id = ? AND DATE(timestamp) = DATE('now')
            ''', (user_id,))
            today = cursor.fetchone()['today']
            
            # First message
            cursor.execute('''
                SELECT timestamp FROM conversation_history 
                WHERE user_id = ? ORDER BY timestamp ASC LIMIT 1
            ''', (user_id,))
            first_row = cursor.fetchone()
            first_message = first_row['timestamp'] if first_row else None
            
            return {
                "total_messages": total,
                "messages_today": today,
                "first_message": first_message
            }
        except Exception as e:
            logger.error(f"Error getting conversation stats: {e}")
            return {}

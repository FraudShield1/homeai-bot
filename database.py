"""
Database Manager for HomeAI Bot
Handles persistent storage for user preferences, history, and automation
"""

import sqlite3
import json
import logging
from typing import Optional, Dict, List, Any, Tuple
from datetime import datetime, timedelta
from pathlib import Path
import threading

logger = logging.getLogger(__name__)


class Database:
    """SQLite database manager for HomeAI bot"""
    
    def __init__(self, db_path: str = "data/homeai.db"):
        """
        Initialize database
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()
        self._init_database()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get thread-local database connection"""
        if not hasattr(self._local, 'conn'):
            self._local.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn
    
    def _init_database(self):
        """Initialize database schema"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                permission_level TEXT DEFAULT 'admin',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # User preferences
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_preferences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                key TEXT,
                value TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id),
                UNIQUE(user_id, key)
            )
        ''')
        
        # Command history
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS command_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                command TEXT,
                command_type TEXT,
                success BOOLEAN,
                response TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        ''')
        
        # Scenes
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS scenes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                description TEXT,
                actions TEXT,
                created_by INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (created_by) REFERENCES users(user_id)
            )
        ''')
        
        # Schedules/Reminders
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS schedules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                name TEXT,
                schedule_type TEXT,
                cron_expression TEXT,
                action TEXT,
                enabled BOOLEAN DEFAULT 1,
                last_run TIMESTAMP,
                next_run TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        ''')
        
        # Documents/Files
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                filename TEXT,
                file_type TEXT,
                file_path TEXT,
                drive_id TEXT,
                tags TEXT,
                ocr_text TEXT,
                metadata TEXT,
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        ''')
        
        # Energy tracking
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS energy_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date DATE,
                total_kwh REAL,
                cost REAL,
                breakdown TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(date)
            )
        ''')
        
        # Automation patterns (learned behaviors)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern_type TEXT,
                pattern_data TEXT,
                confidence REAL,
                occurrences INTEGER DEFAULT 1,
                last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Alerts/Notifications log
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alert_type TEXT,
                entity_id TEXT,
                message TEXT,
                severity TEXT,
                acknowledged BOOLEAN DEFAULT 0,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        logger.info("Database initialized successfully")
    
    # User Management
    def add_user(self, user_id: int, username: str = None, first_name: str = None, 
                 last_name: str = None, permission_level: str = 'admin') -> bool:
        """Add or update user"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO users (user_id, username, first_name, last_name, permission_level, last_active)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (user_id, username, first_name, last_name, permission_level))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error adding user: {e}")
            return False
    
    def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user by ID"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
        except Exception as e:
            logger.error(f"Error getting user: {e}")
            return None
    
    def get_all_users(self) -> List[Dict[str, Any]]:
        """Get all users"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users ORDER BY created_at')
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error getting users: {e}")
            return []
    
    def update_user_activity(self, user_id: int):
        """Update user's last active timestamp"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('UPDATE users SET last_active = CURRENT_TIMESTAMP WHERE user_id = ?', (user_id,))
            conn.commit()
        except Exception as e:
            logger.error(f"Error updating user activity: {e}")
    
    # User Preferences
    def set_preference(self, user_id: int, key: str, value: Any) -> bool:
        """Set user preference"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            value_str = json.dumps(value) if not isinstance(value, str) else value
            cursor.execute('''
                INSERT OR REPLACE INTO user_preferences (user_id, key, value, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ''', (user_id, key, value_str))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error setting preference: {e}")
            return False
    
    def get_preference(self, user_id: int, key: str, default: Any = None) -> Any:
        """Get user preference"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT value FROM user_preferences WHERE user_id = ? AND key = ?', (user_id, key))
            row = cursor.fetchone()
            if row:
                try:
                    return json.loads(row['value'])
                except:
                    return row['value']
            return default
        except Exception as e:
            logger.error(f"Error getting preference: {e}")
            return default
    
    def get_all_preferences(self, user_id: int) -> Dict[str, Any]:
        """Get all preferences for a user"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT key, value FROM user_preferences WHERE user_id = ?', (user_id,))
            prefs = {}
            for row in cursor.fetchall():
                try:
                    prefs[row['key']] = json.loads(row['value'])
                except:
                    prefs[row['key']] = row['value']
            return prefs
        except Exception as e:
            logger.error(f"Error getting preferences: {e}")
            return {}
    
    # Command History
    def log_command(self, user_id: int, command: str, command_type: str, 
                   success: bool, response: str = None) -> bool:
        """Log command execution"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO command_history (user_id, command, command_type, success, response)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, command, command_type, success, response))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error logging command: {e}")
            return False
    
    def get_command_history(self, user_id: int = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Get command history"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            if user_id:
                cursor.execute('''
                    SELECT * FROM command_history WHERE user_id = ? 
                    ORDER BY timestamp DESC LIMIT ?
                ''', (user_id, limit))
            else:
                cursor.execute('SELECT * FROM command_history ORDER BY timestamp DESC LIMIT ?', (limit,))
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error getting command history: {e}")
            return []
    
    # Scenes
    def save_scene(self, name: str, description: str, actions: Dict[str, Any], created_by: int) -> bool:
        """Save or update a scene"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            actions_json = json.dumps(actions)
            cursor.execute('''
                INSERT OR REPLACE INTO scenes (name, description, actions, created_by, updated_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (name, description, actions_json, created_by))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error saving scene: {e}")
            return False
    
    def get_scene(self, name: str) -> Optional[Dict[str, Any]]:
        """Get scene by name"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM scenes WHERE name = ?', (name,))
            row = cursor.fetchone()
            if row:
                scene = dict(row)
                scene['actions'] = json.loads(scene['actions'])
                return scene
            return None
        except Exception as e:
            logger.error(f"Error getting scene: {e}")
            return None
    
    def get_all_scenes(self) -> List[Dict[str, Any]]:
        """Get all scenes"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM scenes ORDER BY name')
            scenes = []
            for row in cursor.fetchall():
                scene = dict(row)
                scene['actions'] = json.loads(scene['actions'])
                scenes.append(scene)
            return scenes
        except Exception as e:
            logger.error(f"Error getting scenes: {e}")
            return []
    
    def delete_scene(self, name: str) -> bool:
        """Delete a scene"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('DELETE FROM scenes WHERE name = ?', (name,))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error deleting scene: {e}")
            return False
    
    # Schedules
    def add_schedule(self, user_id: int, name: str, schedule_type: str, 
                    cron_expression: str, action: str) -> Optional[int]:
        """Add a schedule/reminder"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO schedules (user_id, name, schedule_type, cron_expression, action)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, name, schedule_type, cron_expression, action))
            conn.commit()
            return cursor.lastrowid
        except Exception as e:
            logger.error(f"Error adding schedule: {e}")
            return None
    
    def get_active_schedules(self) -> List[Dict[str, Any]]:
        """Get all active schedules"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM schedules WHERE enabled = 1 ORDER BY next_run')
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error getting schedules: {e}")
            return []
    
    def update_schedule_run(self, schedule_id: int, next_run: datetime):
        """Update schedule last/next run times"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE schedules 
                SET last_run = CURRENT_TIMESTAMP, next_run = ?
                WHERE id = ?
            ''', (next_run, schedule_id))
            conn.commit()
        except Exception as e:
            logger.error(f"Error updating schedule: {e}")
    
    # Documents
    def add_document(self, user_id: int, filename: str, file_type: str, 
                    file_path: str, tags: List[str] = None, ocr_text: str = None,
                    metadata: Dict[str, Any] = None, drive_id: str = None) -> Optional[int]:
        """Add document record"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            tags_str = json.dumps(tags) if tags else None
            metadata_str = json.dumps(metadata) if metadata else None
            cursor.execute('''
                INSERT INTO documents (user_id, filename, file_type, file_path, drive_id, tags, ocr_text, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, filename, file_type, file_path, drive_id, tags_str, ocr_text, metadata_str))
            conn.commit()
            return cursor.lastrowid
        except Exception as e:
            logger.error(f"Error adding document: {e}")
            return None
    
    def search_documents(self, user_id: int, query: str = None, tags: List[str] = None,
                        file_type: str = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Search documents"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            sql = 'SELECT * FROM documents WHERE user_id = ?'
            params = [user_id]
            
            if query:
                sql += ' AND (filename LIKE ? OR ocr_text LIKE ?)'
                params.extend([f'%{query}%', f'%{query}%'])
            
            if file_type:
                sql += ' AND file_type = ?'
                params.append(file_type)
            
            sql += ' ORDER BY uploaded_at DESC LIMIT ?'
            params.append(limit)
            
            cursor.execute(sql, params)
            docs = []
            for row in cursor.fetchall():
                doc = dict(row)
                if doc['tags']:
                    doc['tags'] = json.loads(doc['tags'])
                if doc['metadata']:
                    doc['metadata'] = json.loads(doc['metadata'])
                
                # Filter by tags if specified
                if tags and doc['tags']:
                    if any(tag in doc['tags'] for tag in tags):
                        docs.append(doc)
                else:
                    docs.append(doc)
            
            return docs
        except Exception as e:
            logger.error(f"Error searching documents: {e}")
            return []
    
    # Energy Usage
    def log_energy_usage(self, date: str, total_kwh: float, cost: float, 
                        breakdown: Dict[str, float] = None) -> bool:
        """Log daily energy usage"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            breakdown_str = json.dumps(breakdown) if breakdown else None
            cursor.execute('''
                INSERT OR REPLACE INTO energy_usage (date, total_kwh, cost, breakdown)
                VALUES (?, ?, ?, ?)
            ''', (date, total_kwh, cost, breakdown_str))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error logging energy usage: {e}")
            return False
    
    def get_energy_usage(self, start_date: str, end_date: str = None) -> List[Dict[str, Any]]:
        """Get energy usage for date range"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            if end_date:
                cursor.execute('''
                    SELECT * FROM energy_usage 
                    WHERE date BETWEEN ? AND ? 
                    ORDER BY date
                ''', (start_date, end_date))
            else:
                cursor.execute('SELECT * FROM energy_usage WHERE date = ?', (start_date,))
            
            usage = []
            for row in cursor.fetchall():
                entry = dict(row)
                if entry['breakdown']:
                    entry['breakdown'] = json.loads(entry['breakdown'])
                usage.append(entry)
            return usage
        except Exception as e:
            logger.error(f"Error getting energy usage: {e}")
            return []
    
    # Patterns
    def save_pattern(self, pattern_type: str, pattern_data: Dict[str, Any], confidence: float) -> bool:
        """Save learned pattern"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            data_str = json.dumps(pattern_data)
            cursor.execute('''
                INSERT INTO patterns (pattern_type, pattern_data, confidence, last_seen)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ''', (pattern_type, data_str, confidence))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error saving pattern: {e}")
            return False
    
    def get_patterns(self, pattern_type: str = None, min_confidence: float = 0.5) -> List[Dict[str, Any]]:
        """Get learned patterns"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            if pattern_type:
                cursor.execute('''
                    SELECT * FROM patterns 
                    WHERE pattern_type = ? AND confidence >= ?
                    ORDER BY confidence DESC, occurrences DESC
                ''', (pattern_type, min_confidence))
            else:
                cursor.execute('''
                    SELECT * FROM patterns 
                    WHERE confidence >= ?
                    ORDER BY confidence DESC, occurrences DESC
                ''', (min_confidence,))
            
            patterns = []
            for row in cursor.fetchall():
                pattern = dict(row)
                pattern['pattern_data'] = json.loads(pattern['pattern_data'])
                patterns.append(pattern)
            return patterns
        except Exception as e:
            logger.error(f"Error getting patterns: {e}")
            return []
    
    # Alerts
    def log_alert(self, alert_type: str, entity_id: str, message: str, severity: str = 'info') -> bool:
        """Log an alert"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO alerts (alert_type, entity_id, message, severity)
                VALUES (?, ?, ?, ?)
            ''', (alert_type, entity_id, message, severity))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error logging alert: {e}")
            return False
    
    def get_unacknowledged_alerts(self) -> List[Dict[str, Any]]:
        """Get unacknowledged alerts"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM alerts 
                WHERE acknowledged = 0 
                ORDER BY timestamp DESC
            ''')
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error getting alerts: {e}")
            return []
    
    def acknowledge_alert(self, alert_id: int) -> bool:
        """Mark alert as acknowledged"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('UPDATE alerts SET acknowledged = 1 WHERE id = ?', (alert_id,))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error acknowledging alert: {e}")
            return False
    
    def close(self):
        """Close database connection"""
        if hasattr(self._local, 'conn'):
            self._local.conn.close()

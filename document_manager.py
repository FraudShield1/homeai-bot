"""
Document Manager for HomeAI Bot
Handles file uploads, OCR, Google Drive integration, and document search
"""

import os
import logging
from typing import Optional, Dict, List, Any
from pathlib import Path
import json
from datetime import datetime

try:
    from PIL import Image
    import pytesseract
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    logging.warning("PIL/pytesseract not installed. OCR features will be disabled.")

try:
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    GDRIVE_AVAILABLE = True
except ImportError:
    GDRIVE_AVAILABLE = False
    logging.warning("Google API client not installed. Google Drive features will be disabled.")

from database import Database

logger = logging.getLogger(__name__)


class DocumentManager:
    """Manages document uploads, OCR, and cloud storage"""
    
    def __init__(self, db: Database, upload_dir: str = "data/uploads"):
        """
        Initialize document manager
        
        Args:
            db: Database instance
            upload_dir: Directory for uploaded files
        """
        self.db = db
        self.upload_dir = Path(upload_dir)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        
        self.ocr_enabled = OCR_AVAILABLE
        self.gdrive_enabled = GDRIVE_AVAILABLE and os.getenv('GOOGLE_DRIVE_ENABLED', 'false').lower() == 'true'
        
        if self.gdrive_enabled:
            self._init_gdrive()
        
        logger.info(f"Document manager initialized (OCR: {self.ocr_enabled}, GDrive: {self.gdrive_enabled})")
    
    def _init_gdrive(self):
        """Initialize Google Drive API"""
        try:
            creds_path = os.getenv('GOOGLE_CREDENTIALS_PATH', 'config/google_credentials.json')
            if os.path.exists(creds_path):
                self.gdrive_service = build('drive', 'v3', credentials=Credentials.from_authorized_user_file(creds_path))
                logger.info("Google Drive initialized")
            else:
                logger.warning(f"Google credentials not found at {creds_path}")
                self.gdrive_enabled = False
        except Exception as e:
            logger.error(f"Error initializing Google Drive: {e}")
            self.gdrive_enabled = False
    
    async def process_photo(self, file_path: str, user_id: int, caption: str = None) -> Dict[str, Any]:
        """
        Process uploaded photo
        
        Args:
            file_path: Path to the photo file
            user_id: User ID
            caption: Optional caption/description
            
        Returns:
            Processing result dictionary
        """
        result = {
            "success": False,
            "file_id": None,
            "ocr_text": None,
            "drive_id": None,
            "tags": [],
            "metadata": {}
        }
        
        try:
            # Extract tags from caption
            tags = self._extract_tags(caption) if caption else []
            
            # Perform OCR if enabled
            ocr_text = None
            if self.ocr_enabled:
                ocr_text = self._perform_ocr(file_path)
                result["ocr_text"] = ocr_text
            
            # Extract metadata
            metadata = self._extract_metadata(file_path, caption, ocr_text)
            result["metadata"] = metadata
            
            # Upload to Google Drive if enabled
            drive_id = None
            if self.gdrive_enabled:
                drive_id = await self._upload_to_gdrive(file_path, metadata, tags)
                result["drive_id"] = drive_id
            
            # Save to database
            filename = Path(file_path).name
            file_id = self.db.add_document(
                user_id=user_id,
                filename=filename,
                file_type="image",
                file_path=file_path,
                tags=tags,
                ocr_text=ocr_text,
                metadata=metadata,
                drive_id=drive_id
            )
            
            result["file_id"] = file_id
            result["tags"] = tags
            result["success"] = True
            
            logger.info(f"Photo processed: {filename} (OCR: {bool(ocr_text)}, GDrive: {bool(drive_id)})")
            
        except Exception as e:
            logger.error(f"Error processing photo: {e}")
            result["error"] = str(e)
        
        return result
    
    async def process_document(self, file_path: str, user_id: int, caption: str = None) -> Dict[str, Any]:
        """
        Process uploaded document (PDF, etc.)
        
        Args:
            file_path: Path to the document file
            user_id: User ID
            caption: Optional caption/description
            
        Returns:
            Processing result dictionary
        """
        result = {
            "success": False,
            "file_id": None,
            "drive_id": None,
            "tags": [],
            "metadata": {}
        }
        
        try:
            # Extract tags from caption
            tags = self._extract_tags(caption) if caption else []
            
            # Extract metadata
            metadata = self._extract_metadata(file_path, caption)
            result["metadata"] = metadata
            
            # Upload to Google Drive if enabled
            drive_id = None
            if self.gdrive_enabled:
                drive_id = await self._upload_to_gdrive(file_path, metadata, tags)
                result["drive_id"] = drive_id
            
            # Save to database
            filename = Path(file_path).name
            file_type = Path(file_path).suffix.lstrip('.')
            file_id = self.db.add_document(
                user_id=user_id,
                filename=filename,
                file_type=file_type,
                file_path=file_path,
                tags=tags,
                metadata=metadata,
                drive_id=drive_id
            )
            
            result["file_id"] = file_id
            result["tags"] = tags
            result["success"] = True
            
            logger.info(f"Document processed: {filename} (GDrive: {bool(drive_id)})")
            
        except Exception as e:
            logger.error(f"Error processing document: {e}")
            result["error"] = str(e)
        
        return result
    
    def _perform_ocr(self, image_path: str) -> Optional[str]:
        """Perform OCR on image"""
        if not self.ocr_enabled:
            return None
        
        try:
            image = Image.open(image_path)
            text = pytesseract.image_to_string(image)
            return text.strip() if text else None
        except Exception as e:
            logger.error(f"OCR error: {e}")
            return None
    
    def _extract_tags(self, caption: str) -> List[str]:
        """Extract tags from caption"""
        if not caption:
            return []
        
        tags = []
        caption_lower = caption.lower()
        
        # Common tag keywords
        tag_keywords = {
            "office": ["office", "work", "business"],
            "expenses": ["expense", "receipt", "bill"],
            "tax": ["tax", "deductible"],
            "personal": ["personal"],
            "home": ["home"],
            "medical": ["medical", "health", "doctor"],
            "travel": ["travel", "trip"],
            "food": ["food", "restaurant", "dining"],
            "shopping": ["shopping", "purchase"]
        }
        
        for tag, keywords in tag_keywords.items():
            if any(keyword in caption_lower for keyword in keywords):
                tags.append(tag)
        
        # Extract hashtags
        import re
        hashtags = re.findall(r'#(\w+)', caption)
        tags.extend(hashtags)
        
        return list(set(tags))  # Remove duplicates
    
    def _extract_metadata(self, file_path: str, caption: str = None, ocr_text: str = None) -> Dict[str, Any]:
        """Extract metadata from file and content"""
        metadata = {
            "filename": Path(file_path).name,
            "size": os.path.getsize(file_path),
            "uploaded_at": datetime.now().isoformat(),
            "caption": caption
        }
        
        # Try to extract receipt information from OCR
        if ocr_text:
            metadata.update(self._parse_receipt(ocr_text))
        
        return metadata
    
    def _parse_receipt(self, ocr_text: str) -> Dict[str, Any]:
        """Parse receipt information from OCR text"""
        import re
        
        receipt_data = {}
        
        # Try to extract total amount
        amount_patterns = [
            r'total[:\s]+\$?(\d+\.?\d*)',
            r'amount[:\s]+\$?(\d+\.?\d*)',
            r'\$(\d+\.\d{2})'
        ]
        
        for pattern in amount_patterns:
            match = re.search(pattern, ocr_text, re.IGNORECASE)
            if match:
                receipt_data["amount"] = float(match.group(1))
                break
        
        # Try to extract date
        date_patterns = [
            r'(\d{1,2}/\d{1,2}/\d{2,4})',
            r'(\d{4}-\d{2}-\d{2})'
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, ocr_text)
            if match:
                receipt_data["date"] = match.group(1)
                break
        
        # Try to extract store/merchant name (usually at the top)
        lines = ocr_text.split('\n')
        if lines:
            receipt_data["merchant"] = lines[0].strip()
        
        return receipt_data
    
    async def _upload_to_gdrive(self, file_path: str, metadata: Dict[str, Any], tags: List[str]) -> Optional[str]:
        """Upload file to Google Drive"""
        if not self.gdrive_enabled:
            return None
        
        try:
            filename = Path(file_path).name
            file_metadata = {
                'name': filename,
                'description': json.dumps(metadata),
                'properties': {
                    'tags': ','.join(tags),
                    'uploaded_by': 'homeai_bot'
                }
            }
            
            media = MediaFileUpload(file_path, resumable=True)
            file = self.gdrive_service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()
            
            return file.get('id')
            
        except Exception as e:
            logger.error(f"Error uploading to Google Drive: {e}")
            return None
    
    def search_documents(self, user_id: int, query: str = None, tags: List[str] = None,
                        file_type: str = None, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Search documents
        
        Args:
            user_id: User ID
            query: Search query (searches filename and OCR text)
            tags: Filter by tags
            file_type: Filter by file type
            limit: Maximum results
            
        Returns:
            List of matching documents
        """
        return self.db.search_documents(user_id, query, tags, file_type, limit)
    
    def generate_expense_report(self, user_id: int, start_date: str = None, 
                               end_date: str = None, tags: List[str] = None) -> Dict[str, Any]:
        """
        Generate expense report
        
        Args:
            user_id: User ID
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            tags: Filter by tags
            
        Returns:
            Report data
        """
        # Search for expense documents
        documents = self.search_documents(user_id, tags=tags or ["expenses", "receipt"])
        
        # Filter by date if specified
        if start_date or end_date:
            filtered_docs = []
            for doc in documents:
                doc_date = doc.get('metadata', {}).get('date')
                if doc_date:
                    # Simple date comparison (could be improved)
                    if start_date and doc_date < start_date:
                        continue
                    if end_date and doc_date > end_date:
                        continue
                filtered_docs.append(doc)
            documents = filtered_docs
        
        # Calculate totals
        total_amount = 0
        expenses_by_category = {}
        
        for doc in documents:
            amount = doc.get('metadata', {}).get('amount', 0)
            if amount:
                total_amount += amount
                
                # Categorize by tags
                doc_tags = doc.get('tags', [])
                for tag in doc_tags:
                    if tag not in expenses_by_category:
                        expenses_by_category[tag] = 0
                    expenses_by_category[tag] += amount
        
        return {
            "total_expenses": total_amount,
            "num_receipts": len(documents),
            "by_category": expenses_by_category,
            "documents": documents,
            "period": {
                "start": start_date,
                "end": end_date
            }
        }

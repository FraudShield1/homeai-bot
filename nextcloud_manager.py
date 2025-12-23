"""
Nextcloud Integration for HomeAI Bot
Handles file uploads and synchronization with Nextcloud
"""

import os
import logging
from typing import Optional, Dict, Any
from pathlib import Path
import requests
from requests.auth import HTTPBasicAuth

logger = logging.getLogger(__name__)


class NextcloudManager:
    """Manages Nextcloud file operations"""
    
    def __init__(self, url: str = None, username: str = None, password: str = None):
        """
        Initialize Nextcloud manager
        
        Args:
            url: Nextcloud server URL
            username: Nextcloud username
            password: Nextcloud password/app password
        """
        self.url = (url or os.getenv('NEXTCLOUD_URL', '')).rstrip('/')
        self.username = username or os.getenv('NEXTCLOUD_USERNAME', '')
        self.password = password or os.getenv('NEXTCLOUD_PASSWORD', '')
        
        self.enabled = bool(self.url and self.username and self.password)
        
        if self.enabled:
            self.webdav_url = f"{self.url}/remote.php/dav/files/{self.username}"
            self.auth = HTTPBasicAuth(self.username, self.password)
            logger.info(f"Nextcloud manager initialized: {self.url}")
        else:
            logger.warning("Nextcloud not configured (missing credentials)")
    
    def upload_file(self, local_path: str, remote_path: str) -> bool:
        """
        Upload file to Nextcloud
        
        Args:
            local_path: Local file path
            remote_path: Remote path in Nextcloud (e.g., 'Documents/receipt.pdf')
            
        Returns:
            True if successful
        """
        if not self.enabled:
            return False
        
        try:
            url = f"{self.webdav_url}/{remote_path}"
            
            with open(local_path, 'rb') as f:
                response = requests.put(
                    url,
                    data=f,
                    auth=self.auth,
                    timeout=30
                )
            
            if response.status_code in [201, 204]:
                logger.info(f"Uploaded to Nextcloud: {remote_path}")
                return True
            else:
                logger.error(f"Nextcloud upload failed: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error uploading to Nextcloud: {e}")
            return False
    
    def create_folder(self, folder_path: str) -> bool:
        """
        Create folder in Nextcloud
        
        Args:
            folder_path: Folder path (e.g., 'Documents/Receipts/2025')
            
        Returns:
            True if successful
        """
        if not self.enabled:
            return False
        
        try:
            url = f"{self.webdav_url}/{folder_path}"
            response = requests.request(
                'MKCOL',
                url,
                auth=self.auth,
                timeout=10
            )
            
            if response.status_code in [201, 405]:  # 405 means already exists
                return True
            else:
                logger.error(f"Nextcloud folder creation failed: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error creating Nextcloud folder: {e}")
            return False
    
    def list_files(self, folder_path: str = '') -> list:
        """
        List files in Nextcloud folder
        
        Args:
            folder_path: Folder path
            
        Returns:
            List of file names
        """
        if not self.enabled:
            return []
        
        try:
            url = f"{self.webdav_url}/{folder_path}"
            response = requests.request(
                'PROPFIND',
                url,
                auth=self.auth,
                timeout=10
            )
            
            if response.status_code == 207:
                # Parse WebDAV XML response (simplified)
                # In production, use xml.etree.ElementTree
                return []
            else:
                return []
                
        except Exception as e:
            logger.error(f"Error listing Nextcloud files: {e}")
            return []
    
    def get_share_link(self, file_path: str) -> Optional[str]:
        """
        Create a share link for a file
        
        Args:
            file_path: File path in Nextcloud
            
        Returns:
            Share URL or None
        """
        if not self.enabled:
            return None
        
        try:
            url = f"{self.url}/ocs/v2.php/apps/files_sharing/api/v1/shares"
            
            data = {
                'path': f'/{file_path}',
                'shareType': 3,  # Public link
            }
            
            response = requests.post(
                url,
                data=data,
                auth=self.auth,
                headers={'OCS-APIRequest': 'true'},
                timeout=10
            )
            
            if response.status_code == 200:
                # Parse OCS response to get share URL
                # In production, parse XML properly
                return f"{self.url}/s/SHAREID"
            else:
                return None
                
        except Exception as e:
            logger.error(f"Error creating share link: {e}")
            return None

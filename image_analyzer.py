"""
Image Analysis Module for HomeAI Bot
Uses Gemini Vision to understand and describe image content
"""

import os
import logging
from typing import Optional, Dict, Any
from pathlib import Path

try:
    import google.generativeai as genai
    from PIL import Image
    VISION_AVAILABLE = True
except ImportError:
    VISION_AVAILABLE = False
    logging.warning("Gemini Vision not available - install google-generativeai and pillow")

logger = logging.getLogger(__name__)


class ImageAnalyzer:
    """Analyzes images using Gemini Vision"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize image analyzer
        
        Args:
            api_key: Google API key for Gemini
        """
        self.enabled = False
        self.api_key = api_key or os.getenv('GOOGLE_API_KEY')
        
        if self.api_key and VISION_AVAILABLE:
            try:
                genai.configure(api_key=self.api_key)
                self.model = genai.GenerativeModel('gemini-1.5-flash')
                self.enabled = True
                logger.info("Image analyzer initialized with Gemini Vision")
            except Exception as e:
                logger.error(f"Error initializing Gemini Vision: {e}")
        else:
            logger.warning("Image analysis disabled (no API key or libraries missing)")
    
    async def analyze_image(self, image_path: str, question: str = None) -> Optional[str]:
        """
        Analyze an image and optionally answer a question about it
        
        Args:
            image_path: Path to image file
            question: Optional question about the image
            
        Returns:
            Analysis or answer as text
        """
        if not self.enabled:
            return None
        
        try:
            # Load image
            img = Image.open(image_path)
            
            # Create prompt
            if question:
                prompt = f"""Analyze this image and answer the question.

Question: {question}

Provide a direct, detailed answer based on what you see in the image."""
            else:
                prompt = """Analyze this image in detail. Describe:
1. What you see (objects, people, scenes)
2. Notable details or features
3. Context or setting
4. Any text visible in the image
5. Overall impression or purpose

Be specific and comprehensive."""
            
            # Generate response
            response = self.model.generate_content([prompt, img])
            
            return response.text
            
        except Exception as e:
            logger.error(f"Error analyzing image: {e}")
            return None
    
    async def describe_scene(self, image_path: str) -> Optional[str]:
        """
        Get a brief description of what's in the image
        
        Args:
            image_path: Path to image file
            
        Returns:
            Brief scene description
        """
        if not self.enabled:
            return None
        
        try:
            img = Image.open(image_path)
            
            prompt = """Describe what you see in this image in 2-3 sentences. 
Be concise but informative. Focus on the main subjects and context."""
            
            response = self.model.generate_content([prompt, img])
            return response.text
            
        except Exception as e:
            logger.error(f"Error describing scene: {e}")
            return None
    
    async def extract_text(self, image_path: str) -> Optional[str]:
        """
        Extract any text visible in the image
        
        Args:
            image_path: Path to image file
            
        Returns:
            Extracted text
        """
        if not self.enabled:
            return None
        
        try:
            img = Image.open(image_path)
            
            prompt = """Extract all visible text from this image. 
If there's no text, say "No text found". 
If there is text, provide it exactly as it appears."""
            
            response = self.model.generate_content([prompt, img])
            return response.text
            
        except Exception as e:
            logger.error(f"Error extracting text: {e}")
            return None
    
    async def identify_objects(self, image_path: str) -> Optional[Dict[str, Any]]:
        """
        Identify and list objects in the image
        
        Args:
            image_path: Path to image file
            
        Returns:
            Dictionary with object information
        """
        if not self.enabled:
            return None
        
        try:
            img = Image.open(image_path)
            
            prompt = """List all objects you can identify in this image.
For each object, provide:
- Name
- Location (where in the image)
- Confidence (high/medium/low)

Format as a simple list."""
            
            response = self.model.generate_content([prompt, img])
            
            return {
                "objects": response.text,
                "count": response.text.count('\n') + 1
            }
            
        except Exception as e:
            logger.error(f"Error identifying objects: {e}")
            return None
    
    async def smart_analysis(self, image_path: str, context: str = None) -> Optional[str]:
        """
        Smart analysis with context awareness
        
        Args:
            image_path: Path to image file
            context: Additional context (e.g., "This is from my security camera")
            
        Returns:
            Intelligent analysis
        """
        if not self.enabled:
            return None
        
        try:
            img = Image.open(image_path)
            
            context_str = f"\n\nContext: {context}" if context else ""
            
            prompt = f"""You are a smart home assistant analyzing this image.{context_str}

Provide:
1. What you see
2. Any concerns or notable observations
3. Suggested actions (if any)
4. Relevant insights

Be helpful, specific, and actionable."""
            
            response = self.model.generate_content([prompt, img])
            return response.text
            
        except Exception as e:
            logger.error(f"Error in smart analysis: {e}")
            return None

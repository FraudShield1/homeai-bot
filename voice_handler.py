"""
Voice Message Handler for HomeAI Bot
Transcribes voice messages using Google Gemini 1.5 Flash (Free & Business Grade)
"""

import os
import logging
from typing import Optional
from pathlib import Path

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    logging.warning("Gemini not available - install google-generativeai")

logger = logging.getLogger(__name__)


class VoiceHandler:
    """Handles voice message transcription using Gemini"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize voice handler with Google Gemini
        """
        self.enabled = False
        self.api_key = api_key or os.getenv('GOOGLE_API_KEY')
        
        if self.api_key and GEMINI_AVAILABLE:
            try:
                genai.configure(api_key=self.api_key)
                self.model = genai.GenerativeModel('gemini-1.5-flash')
                self.enabled = True
                logger.info("Voice handler initialized with Google Gemini (Free Tier)")
            except Exception as e:
                logger.error(f"Error initializing Gemini Voice: {e}")
        else:
            logger.warning("Voice transcription disabled (no Google API key)")
    
    async def transcribe(self, audio_path: str, language: str = None) -> Optional[str]:
        """
        Transcribe audio file to text using Gemini Vision/Audio capabilities
        """
        if not self.enabled:
            return None
        
        try:
            # Upload the audio file to Gemini
            # Note: For efficiency in a bot, we might need a temporary upload
            # But Gemini 1.5 Flash accepts audio directly in some client versions
            # We will use the standard file API
            
            audio_file = genai.upload_file(path=audio_path)
            
            prompt = "Transcribe this audio file exactly as spoken. Do not add any commentary."
            
            response = self.model.generate_content([prompt, audio_file])
            
            # Clean up (optional, good practice)
            # audio_file.delete() 
            
            text = response.text.strip()
            logger.info(f"Gemini transcribed: {text[:50]}...")
            return text
                
        except Exception as e:
            logger.error(f"Gemini transcription error: {e}")
            return None
    
    def get_supported_formats(self) -> list:
        return ['.mp3', '.wav', '.aac', '.ogg', '.m4a']
    
    def is_supported_format(self, filename: str) -> bool:
        ext = Path(filename).suffix.lower()
        return ext in self.get_supported_formats()


class VoiceCommandProcessor:
    """Processes voice commands"""
    
    def __init__(self, voice_handler: VoiceHandler):
        self.voice_handler = voice_handler
    
    async def process_voice_message(self, audio_path: str, user_context: dict = None) -> dict:
        if not self.voice_handler.enabled:
            return {"success": False, "error": "Voice disabled"}
        
        try:
            text = await self.voice_handler.transcribe(audio_path)
            
            if not text:
                return {"success": False, "error": "Transcription failed"}
            
            return {
                "success": True,
                "text": text,
                "word_count": len(text.split()),
                "audio_path": audio_path
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}

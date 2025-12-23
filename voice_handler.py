"""
Voice Message Handler for HomeAI Bot
Transcribes voice messages using OpenAI Whisper API
"""

import os
import logging
from typing import Optional
from pathlib import Path

try:
    from openai import AsyncOpenAI
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False
    logging.warning("Voice transcription not available - install openai")

logger = logging.getLogger(__name__)


class VoiceHandler:
    """Handles voice message transcription"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize voice handler
        
        Args:
            api_key: OpenAI API key for Whisper
        """
        self.enabled = False
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        
        if self.api_key and WHISPER_AVAILABLE:
            try:
                self.client = AsyncOpenAI(api_key=self.api_key)
                self.enabled = True
                logger.info("Voice handler initialized with OpenAI Whisper")
            except Exception as e:
                logger.error(f"Error initializing Whisper: {e}")
        else:
            logger.warning("Voice transcription disabled (no API key or library missing)")
    
    async def transcribe(self, audio_path: str, language: str = None) -> Optional[str]:
        """
        Transcribe audio file to text
        
        Args:
            audio_path: Path to audio file
            language: Optional language code (e.g., 'en', 'fr')
            
        Returns:
            Transcribed text or None
        """
        if not self.enabled:
            return None
        
        try:
            # Open audio file
            with open(audio_path, 'rb') as audio_file:
                # Transcribe using Whisper
                params = {
                    "model": "whisper-1",
                    "file": audio_file
                }
                
                if language:
                    params["language"] = language
                
                transcript = await self.client.audio.transcriptions.create(**params)
                
                text = transcript.text
                logger.info(f"Transcribed audio: {text[:50]}...")
                return text
                
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            return None
    
    async def transcribe_with_timestamps(self, audio_path: str) -> Optional[dict]:
        """
        Transcribe with word-level timestamps
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            Dictionary with text and timestamps
        """
        if not self.enabled:
            return None
        
        try:
            with open(audio_path, 'rb') as audio_file:
                transcript = await self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    response_format="verbose_json",
                    timestamp_granularities=["word"]
                )
                
                return {
                    "text": transcript.text,
                    "language": transcript.language,
                    "duration": transcript.duration,
                    "words": transcript.words if hasattr(transcript, 'words') else []
                }
                
        except Exception as e:
            logger.error(f"Transcription with timestamps error: {e}")
            return None
    
    def get_supported_formats(self) -> list:
        """
        Get list of supported audio formats
        
        Returns:
            List of supported file extensions
        """
        return ['.mp3', '.mp4', '.mpeg', '.mpga', '.m4a', '.wav', '.webm', '.ogg']
    
    def is_supported_format(self, filename: str) -> bool:
        """
        Check if audio format is supported
        
        Args:
            filename: Audio filename
            
        Returns:
            True if format is supported
        """
        ext = Path(filename).suffix.lower()
        return ext in self.get_supported_formats()


class VoiceCommandProcessor:
    """Processes voice commands with context awareness"""
    
    def __init__(self, voice_handler: VoiceHandler):
        """
        Initialize voice command processor
        
        Args:
            voice_handler: VoiceHandler instance
        """
        self.voice_handler = voice_handler
    
    async def process_voice_message(self, audio_path: str, user_context: dict = None) -> dict:
        """
        Process voice message and extract command
        
        Args:
            audio_path: Path to audio file
            user_context: Optional user context
            
        Returns:
            Dictionary with transcription and metadata
        """
        if not self.voice_handler.enabled:
            return {
                "success": False,
                "error": "Voice transcription not available"
            }
        
        try:
            # Transcribe audio
            text = await self.voice_handler.transcribe(audio_path)
            
            if not text:
                return {
                    "success": False,
                    "error": "Failed to transcribe audio"
                }
            
            # Detect language and confidence
            result = {
                "success": True,
                "text": text,
                "length": len(text),
                "word_count": len(text.split()),
                "audio_path": audio_path
            }
            
            # Add context if available
            if user_context:
                result["context"] = user_context
            
            return result
            
        except Exception as e:
            logger.error(f"Voice processing error: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def format_transcription(self, result: dict) -> str:
        """
        Format transcription result for display
        
        Args:
            result: Transcription result
            
        Returns:
            Formatted string
        """
        if not result.get("success"):
            return f"❌ Error: {result.get('error', 'Unknown error')}"
        
        text = result.get("text", "")
        word_count = result.get("word_count", 0)
        
        formatted = f"🎤 **Transcribed:**\n\n_{text}_\n\n"
        formatted += f"📊 {word_count} words"
        
        return formatted

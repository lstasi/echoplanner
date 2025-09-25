"""Voice agent for transcribing audio files using speech-to-text."""

import logging
from pathlib import Path
from typing import Optional

import openai

from ..config.settings import Settings

logger = logging.getLogger(__name__)


class VoiceAgent:
    """AI agent for processing audio files and converting speech to text."""
    
    def __init__(self, settings: Settings):
        """Initialize voice agent with settings."""
        self.settings = settings
        
        # Initialize OpenAI client if API key is provided
        if settings.openai_api_key:
            openai.api_key = settings.openai_api_key
    
    async def transcribe_audio(self, audio_path: str) -> str:
        """Transcribe audio file to text."""
        try:
            audio_path_obj = Path(audio_path)
            if not audio_path_obj.exists():
                logger.error(f"Audio file not found: {audio_path}")
                return ""
            
            # Check file size
            file_size = audio_path_obj.stat().st_size
            if file_size > 25 * 1024 * 1024:  # 25MB limit for OpenAI Whisper
                logger.warning(f"Audio file {audio_path} is too large ({file_size} bytes)")
                return ""
            
            # Try OpenAI Whisper API if available
            if self.settings.openai_api_key:
                try:
                    return await self._transcribe_with_whisper(audio_path)
                except Exception as e:
                    logger.warning(f"Whisper API failed, trying fallback methods: {e}")
            
            # Try local transcription methods
            return await self._transcribe_with_local_methods(audio_path)
            
        except Exception as e:
            logger.error(f"Error transcribing audio {audio_path}: {e}")
            return ""
    
    async def _transcribe_with_whisper(self, audio_path: str) -> str:
        """Transcribe audio using OpenAI Whisper API."""
        try:
            with open(audio_path, "rb") as audio_file:
                response = await openai.Audio.atranscribe(
                    model="whisper-1",
                    file=audio_file,
                    response_format="text"
                )
            
            transcribed_text = response.strip()
            logger.info(f"Whisper transcribed audio: {len(transcribed_text)} characters")
            return transcribed_text
            
        except Exception as e:
            logger.error(f"Whisper API error: {e}")
            raise
    
    async def _transcribe_with_local_methods(self, audio_path: str) -> str:
        """Try local transcription methods as fallback."""
        try:
            # Try speech_recognition library if available
            try:
                import speech_recognition as sr
                return await self._transcribe_with_speech_recognition(audio_path)
            except ImportError:
                logger.warning("speech_recognition library not available")
            
            # If no transcription methods are available, return placeholder
            return self._create_audio_placeholder(audio_path)
            
        except Exception as e:
            logger.error(f"Local transcription error: {e}")
            return ""
    
    async def _transcribe_with_speech_recognition(self, audio_path: str) -> str:
        """Transcribe audio using speech_recognition library."""
        import speech_recognition as sr
        
        try:
            recognizer = sr.Recognizer()
            
            # Convert audio file if necessary and load
            with sr.AudioFile(audio_path) as source:
                audio_data = recognizer.record(source)
            
            # Try different recognition services
            services = [
                ("Google", lambda: recognizer.recognize_google(audio_data)),
                ("Sphinx", lambda: recognizer.recognize_sphinx(audio_data)),
            ]
            
            for service_name, recognize_func in services:
                try:
                    text = recognize_func()
                    logger.info(f"{service_name} transcribed audio: {len(text)} characters")
                    return text
                except Exception as e:
                    logger.warning(f"{service_name} recognition failed: {e}")
                    continue
            
            return ""
            
        except Exception as e:
            logger.error(f"Speech recognition error: {e}")
            return ""
    
    def _create_audio_placeholder(self, audio_path: str) -> str:
        """Create a placeholder description for audio file."""
        audio_path_obj = Path(audio_path)
        file_size = audio_path_obj.stat().st_size
        
        placeholder = f"Audio file analysis: {audio_path_obj.name}, "
        placeholder += f"Size: {file_size} bytes. "
        placeholder += "Audio transcription requires speech-to-text capability. "
        placeholder += "Please configure OpenAI Whisper API or install speech_recognition library."
        
        logger.info("Created audio placeholder description")
        return placeholder
    
    def is_supported_audio_format(self, audio_path: str) -> bool:
        """Check if audio format is supported for transcription."""
        supported_extensions = {'.mp3', '.wav', '.m4a', '.flac', '.ogg', '.opus'}
        
        audio_path_obj = Path(audio_path)
        return audio_path_obj.suffix.lower() in supported_extensions
    
    def get_audio_info(self, audio_path: str) -> dict:
        """Get basic information about audio file."""
        try:
            audio_path_obj = Path(audio_path)
            
            info = {
                "filename": audio_path_obj.name,
                "size": audio_path_obj.stat().st_size,
                "extension": audio_path_obj.suffix.lower(),
                "supported": self.is_supported_audio_format(audio_path)
            }
            
            # Try to get more detailed audio info if possible
            try:
                import wave
                if audio_path_obj.suffix.lower() == '.wav':
                    with wave.open(audio_path, 'rb') as wav_file:
                        info.update({
                            "channels": wav_file.getnchannels(),
                            "sample_rate": wav_file.getframerate(),
                            "duration_seconds": wav_file.getnframes() / wav_file.getframerate()
                        })
            except ImportError:
                pass
            except Exception as e:
                logger.debug(f"Could not extract detailed audio info: {e}")
            
            return info
            
        except Exception as e:
            logger.error(f"Error getting audio info: {e}")
            return {"error": str(e)}
    
    def estimate_transcription_time(self, audio_path: str) -> Optional[float]:
        """Estimate how long transcription might take."""
        try:
            audio_info = self.get_audio_info(audio_path)
            
            # If we have duration, estimate based on that
            if "duration_seconds" in audio_info:
                duration = audio_info["duration_seconds"]
                # Rough estimate: transcription takes about 1/10 of audio duration
                return duration / 10
            
            # Otherwise estimate based on file size
            file_size = audio_info.get("size", 0)
            # Very rough estimate: 1MB = ~1 minute of audio = ~6 seconds transcription
            estimated_duration = file_size / (1024 * 1024) * 60
            return estimated_duration / 10
            
        except Exception as e:
            logger.error(f"Error estimating transcription time: {e}")
            return None
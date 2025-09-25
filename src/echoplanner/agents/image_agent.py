"""Image agent for extracting text from images using OCR and AI."""

import logging
from pathlib import Path
from typing import Optional

from PIL import Image
import openai

from ..config.settings import Settings

logger = logging.getLogger(__name__)


class ImageAgent:
    """AI agent for processing images and extracting text content."""
    
    def __init__(self, settings: Settings):
        """Initialize image agent with settings."""
        self.settings = settings
        
        # Initialize OpenAI client if API key is provided
        if settings.openai_api_key:
            openai.api_key = settings.openai_api_key
    
    async def extract_text_from_image(self, image_path: str) -> str:
        """Extract text from an image using OCR and AI analysis."""
        try:
            image_path_obj = Path(image_path)
            if not image_path_obj.exists():
                logger.error(f"Image file not found: {image_path}")
                return ""
            
            # First try to use OpenAI Vision API if available
            if self.settings.openai_api_key:
                try:
                    return await self._extract_with_openai_vision(image_path)
                except Exception as e:
                    logger.warning(f"OpenAI Vision API failed, falling back to basic OCR: {e}")
            
            # Fallback to basic image analysis
            return self._extract_with_basic_ocr(image_path)
            
        except Exception as e:
            logger.error(f"Error extracting text from image {image_path}: {e}")
            return ""
    
    async def _extract_with_openai_vision(self, image_path: str) -> str:
        """Extract text using OpenAI Vision API."""
        import base64
        
        try:
            # Read and encode image
            with open(image_path, "rb") as image_file:
                image_data = base64.b64encode(image_file.read()).decode('utf-8')
            
            # Prepare the prompt
            prompt = """
Analyze this image and extract any text that might be relevant for calendar events.
Look for:
- Dates and times
- Event titles or descriptions
- Locations
- Names of people
- Any scheduling information

Please return the extracted text in a clear, structured format.
If no relevant text is found, return an empty string.
"""
            
            # Make API call
            response = await openai.ChatCompletion.acreate(
                model="gpt-4-vision-preview",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_data}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=500
            )
            
            extracted_text = response.choices[0].message.content.strip()
            logger.info(f"OpenAI Vision extracted text from image: {len(extracted_text)} characters")
            return extracted_text
            
        except Exception as e:
            logger.error(f"OpenAI Vision API error: {e}")
            raise
    
    def _extract_with_basic_ocr(self, image_path: str) -> str:
        """Extract text using basic image processing (fallback method)."""
        try:
            # Try to use pytesseract if available
            try:
                import pytesseract
                
                # Open and process image
                image = Image.open(image_path)
                
                # Convert to RGB if necessary
                if image.mode != 'RGB':
                    image = image.convert('RGB')
                
                # Extract text using Tesseract
                extracted_text = pytesseract.image_to_string(image)
                
                logger.info(f"Tesseract OCR extracted text from image: {len(extracted_text)} characters")
                return extracted_text.strip()
                
            except ImportError:
                logger.warning("pytesseract not available, using basic image analysis")
                return self._basic_image_analysis(image_path)
                
        except Exception as e:
            logger.error(f"Basic OCR error: {e}")
            return ""
    
    def _basic_image_analysis(self, image_path: str) -> str:
        """Very basic image analysis as last resort."""
        try:
            # Open image to verify it's valid
            image = Image.open(image_path)
            
            # Get basic image properties
            width, height = image.size
            format_name = image.format
            
            # Return basic information about the image
            # This is a placeholder - in a real implementation you might:
            # - Use cloud OCR services
            # - Implement more sophisticated image processing
            # - Use other computer vision libraries
            
            result = f"Image analysis: {format_name} format, {width}x{height} pixels. "
            result += "Text extraction requires OCR capability. "
            result += "Please install pytesseract or configure OpenAI Vision API for text extraction."
            
            logger.info("Basic image analysis completed")
            return result
            
        except Exception as e:
            logger.error(f"Basic image analysis error: {e}")
            return ""
    
    def is_calendar_related_image(self, image_path: str) -> bool:
        """Determine if an image might contain calendar-related content."""
        try:
            # This is a placeholder for more sophisticated image classification
            # In a real implementation, you might:
            # - Use image classification models
            # - Analyze image content with AI
            # - Look for specific visual patterns
            
            image = Image.open(image_path)
            
            # Basic heuristics based on image properties
            width, height = image.size
            
            # Screenshots and documents are more likely to contain calendar info
            aspect_ratio = width / height if height > 0 else 1
            
            # Typical document or screenshot aspect ratios
            if 0.5 <= aspect_ratio <= 2.0:
                return True
            
            # Very wide or very tall images are less likely to be calendar-related
            return False
            
        except Exception as e:
            logger.error(f"Error analyzing image for calendar content: {e}")
            return False
    
    def get_image_metadata(self, image_path: str) -> dict:
        """Extract metadata from image file."""
        try:
            image = Image.open(image_path)
            
            metadata = {
                "format": image.format,
                "size": image.size,
                "mode": image.mode,
                "filename": Path(image_path).name
            }
            
            # Try to get EXIF data if available
            if hasattr(image, '_getexif'):
                exif = image._getexif()
                if exif:
                    metadata["exif"] = exif
            
            return metadata
            
        except Exception as e:
            logger.error(f"Error extracting image metadata: {e}")
            return {}
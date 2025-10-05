"""
Prescription Image Processing Handler
Integrates OCR + Google Gemini AI for prescription analysis
Compatible with Twilio WhatsApp integration
"""
import os
import logging
import platform
from io import BytesIO
from PIL import Image
import pytesseract
import cv2
import numpy as np
import google.generativeai as genai
from pathlib import Path
from datetime import datetime
import httpx
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

# Configure Tesseract path for Windows
if platform.system() == 'Windows':
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Configure Google Gemini
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)
    try:
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
    except Exception as e:
        logger.warning(f"Primary Gemini model load failed: {e}")
        try:
            model = genai.GenerativeModel('gemini-1.5-flash')
        except Exception as e2:
            logger.warning(f"Fallback Gemini model load failed: {e2}")
            model = genai.GenerativeModel('gemini-pro')
    logger.info(f"Gemini model initialized: {model._model_name}")
else:
    logger.warning("GOOGLE_API_KEY not set - prescription analysis will not work")
    model = None

class PrescriptionHandler:
    """Handler for processing prescription images via WhatsApp"""
    
    def __init__(self):
        self.output_dir = Path("output/ocr_extracts")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"PrescriptionHandler initialized. Output dir: {self.output_dir}")
    
    async def download_image(self, media_url: str, auth: tuple) -> Image.Image:
        """Download image from Twilio media URL"""
        try:
            logger.info(f"Downloading image from: {media_url[:80]}...")
            # Twilio media endpoints often redirect to a CDN (307). Enable following redirects.
            async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
                response = await client.get(media_url, auth=auth)
                logger.info(f"Download final URL: {response.url} status: {response.status_code}")
                response.raise_for_status()
                image = Image.open(BytesIO(response.content))
                logger.info(f"Image downloaded successfully. Size: {image.size}")
                return image
        except Exception as e:
            logger.error(f"Error downloading image: {str(e)}")
            raise Exception(f"Failed to download image: {str(e)}")
    
    def extract_text(self, image: Image.Image) -> str:
        """Extract text from prescription image using OCR"""
        try:
            logger.info("Starting OCR text extraction...")
            
            # Convert to numpy array
            img_array = np.array(image)
            
            # Convert to grayscale
            if len(img_array.shape) == 3:
                gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            else:
                gray = img_array
            
            # Denoise
            denoised = cv2.fastNlMeansDenoising(gray)
            
            # Threshold
            _, thresh = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # Extract text using Tesseract
            text = pytesseract.image_to_string(thresh)
            
            extracted_length = len(text.strip())
            logger.info(f"Extracted {extracted_length} characters from image")
            
            if extracted_length < 10:
                logger.warning("Very little text extracted - image may be unclear")
            
            return text.strip()
            
        except Exception as e:
            logger.error(f"OCR failed: {str(e)}")
            raise Exception(f"OCR failed: {str(e)}. Check Tesseract installation.")
    
    def analyze_prescription(self, extracted_text: str) -> str:
        """Analyze prescription with Google Gemini AI"""
        if not model:
            return "⚠️ AI analysis unavailable. GOOGLE_API_KEY not configured."
        
        logger.info("Starting AI analysis...")
        
        prompt = f"""Analyze this prescription and provide a CONCISE summary (under 1400 characters for WhatsApp):

📋 **Medications:**
List each medication with:
- Name
- Dosage (e.g., 500mg)
- Frequency (e.g., twice daily)

⏰ **Timing & Duration:**
- When to take (morning/evening)
- Duration of treatment

🍽️ **Instructions:**
- Before/after food
- Special timing requirements

⚠️ **Important Warnings:**
- Side effects to watch for
- Precautions

Use clear formatting with emojis for WhatsApp readability.

Prescription text:
{extracted_text}

Keep total response under 1400 characters. If unclear, say "Not clearly visible"."""
        
        try:
            response = model.generate_content(prompt)
            analysis = response.text
            
            # Ensure not too long for WhatsApp
            if len(analysis) > 1400:
                logger.warning(f"Analysis too long ({len(analysis)} chars), truncating...")
                analysis = analysis[:1400] + "\n\n...(truncated)"
            
            logger.info(f"AI analysis complete ({len(analysis)} characters)")
            return analysis
            
        except Exception as e:
            logger.error(f"AI analysis failed: {str(e)}")
            raise Exception(f"AI analysis failed: {str(e)}")
    
    def save_prescription(self, extracted_text: str, analysis: str) -> str:
        """Save prescription data and return timestamp"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        try:
            # Save extracted text
            text_file = self.output_dir / f"prescription_{timestamp}.txt"
            with open(text_file, 'w', encoding='utf-8') as f:
                f.write("=== OCR EXTRACTED TEXT ===\n")
                f.write(f"Timestamp: {datetime.now().isoformat()}\n")
                f.write(f"{'='*50}\n\n")
                f.write(extracted_text)
            
            # Save analysis
            analysis_file = self.output_dir / f"prescription_{timestamp}_analysis.txt"
            with open(analysis_file, 'w', encoding='utf-8') as f:
                f.write("=== AI ANALYSIS ===\n")
                f.write(f"Timestamp: {datetime.now().isoformat()}\n")
                f.write(f"{'='*50}\n\n")
                f.write(analysis)
            
            logger.info(f"Saved prescription data: {timestamp}")
            return timestamp
            
        except Exception as e:
            logger.error(f"Error saving prescription: {str(e)}")
            # Don't fail the whole process if save fails
            return timestamp
    
    async def process_prescription(self, media_url: str, auth: tuple) -> str:
        """
        Main processing pipeline
        Returns: WhatsApp-formatted response string
        """
        try:
            logger.info("=" * 50)
            logger.info("Starting prescription processing pipeline")
            
            # Step 1: Download image
            logger.info("Step 1: Downloading image...")
            image = await self.download_image(media_url, auth)
            
            # Step 2: Extract text with OCR
            logger.info("Step 2: Extracting text with OCR...")
            extracted_text = self.extract_text(image)
            
            if not extracted_text or len(extracted_text) < 10:
                logger.warning("Insufficient text extracted")
                return """❌ *Could not extract readable text from image*

💡 *Tips for better results:*
• Take photo in good lighting
• Keep camera steady and focused
• Capture entire prescription clearly
• Avoid shadows and glare
• Try a higher resolution image

Please try again with a clearer photo."""
            
            # Step 3: Analyze with AI
            logger.info("Step 3: Analyzing with AI...")
            analysis = self.analyze_prescription(extracted_text)
            
            # Step 4: Save data
            logger.info("Step 4: Saving data...")
            timestamp = self.save_prescription(extracted_text, analysis)
            
            # Step 5: Format response for WhatsApp
            response = f"""📋 *PRESCRIPTION ANALYSIS*
━━━━━━━━━━━━━━━━━━━━

{analysis}

━━━━━━━━━━━━━━━━━━━━
⚠️ *IMPORTANT DISCLAIMER*

This is AI-generated analysis for reference only.

*Always consult your doctor before:*
• Taking any medications
• Changing dosages
• Stopping treatment

*Report side effects immediately to your healthcare provider.*

📁 Reference: {timestamp}
━━━━━━━━━━━━━━━━━━━━"""
            
            logger.info("Prescription processed successfully")
            logger.info("=" * 50)
            return response
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error in processing pipeline: {error_msg}")
            logger.error("=" * 50)
            
            return f"""❌ *Error Processing Prescription*

{error_msg}

💡 *Troubleshooting:*
• Ensure image is clear and well-lit
• Try a different photo angle
• Check image file size (not too large)
• Verify image format (JPG/PNG)

If problem persists, contact support.

🔧 Technical details saved for debugging."""
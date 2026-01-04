"""
ALFRED VISION MODULE
Vision capabilities for ALFRED using local LLaVA + OCR.

Features:
- Screenshot capture (mss)
- OCR text extraction (pytesseract)
- Image description via LLaVA (Ollama)
- Object/scene analysis

Works fully offline on local GPU (RTX 4060 8GB recommended).
"""

import os
import io
import base64
import logging
from typing import Optional, Dict, Any, List
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger("Alfred.Vision")


@dataclass
class VisionResult:
    """Result from a vision analysis."""
    success: bool
    description: str = ""
    extracted_text: str = ""
    objects: List[str] = field(default_factory=list)
    confidence: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    error: Optional[str] = None


class VisionClient:
    """
    ALFRED Vision Client - Local image understanding.
    
    Uses:
    - LLaVA via Ollama for image description/analysis
    - pytesseract for OCR text extraction
    - mss for fast screenshot capture
    """
    
    # Default vision model (LLaVA 7B fits in 8GB VRAM)
    DEFAULT_VISION_MODEL = "llava:7b"
    
    def __init__(self, vision_model: str = None):
        """
        Initialize vision client.
        
        Args:
            vision_model: Ollama vision model name (default: llava:7b)
        """
        self.vision_model = vision_model or self.DEFAULT_VISION_MODEL
        self.ollama_client = None
        self.tesseract_available = False
        self.mss_available = False
        
        self._initialize()
    
    def _initialize(self):
        """Initialize all vision components."""
        # Check Ollama
        try:
            import ollama
            self.ollama_client = ollama
            logger.info(f"✅ Ollama connected for vision model: {self.vision_model}")
        except ImportError:
            logger.warning("⚠️ Ollama not installed. Image description disabled.")
        
        # Check pytesseract
        try:
            import pytesseract
            # Quick test
            pytesseract.get_tesseract_version()
            self.tesseract_available = True
            logger.info("✅ Tesseract OCR available")
        except Exception as e:
            logger.warning(f"⚠️ Tesseract OCR not available: {e}")
            logger.info("   Install with: pip install pytesseract")
            logger.info("   Also install Tesseract: https://github.com/tesseract-ocr/tesseract")
        
        # Check mss for screenshots
        try:
            import mss
            self.mss_available = True
            logger.info("✅ Screenshot capture (mss) available")
        except ImportError:
            logger.warning("⚠️ mss not installed. Screenshot capture disabled.")
            logger.info("   Install with: pip install mss")
    
    def capture_screenshot(self, monitor: int = 1, save_path: Optional[str] = None) -> Optional[str]:
        """
        Capture a screenshot of the specified monitor.
        
        Args:
            monitor: Monitor number (1 = primary, 0 = all monitors)
            save_path: Optional path to save the screenshot
            
        Returns:
            Path to saved screenshot, or None on failure
        """
        if not self.mss_available:
            logger.error("Screenshot capture not available (mss not installed)")
            return None
        
        try:
            import mss
            from PIL import Image
            
            with mss.mss() as sct:
                # Capture
                screenshot = sct.grab(sct.monitors[monitor])
                
                # Convert to PIL Image
                img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
                
                # Save path
                if not save_path:
                    # Default to temp location
                    alfred_dir = Path.home() / ".alfred" / "screenshots"
                    alfred_dir.mkdir(parents=True, exist_ok=True)
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    save_path = str(alfred_dir / f"screenshot_{timestamp}.png")
                
                img.save(save_path)
                logger.info(f"📸 Screenshot saved: {save_path}")
                return save_path
                
        except Exception as e:
            logger.error(f"Screenshot capture failed: {e}")
            return None
    
    def ocr_image(self, image_path: str, lang: str = "eng") -> str:
        """
        Extract text from an image using OCR.
        
        Args:
            image_path: Path to the image
            lang: Language code (default: eng)
            
        Returns:
            Extracted text or empty string
        """
        if not self.tesseract_available:
            return "[OCR not available - Tesseract not installed]"
        
        try:
            import pytesseract
            from PIL import Image
            
            img = Image.open(image_path)
            text = pytesseract.image_to_string(img, lang=lang)
            
            # Clean up
            text = text.strip()
            
            logger.info(f"📝 OCR extracted {len(text)} characters from {image_path}")
            return text
            
        except Exception as e:
            logger.error(f"OCR failed: {e}")
            return f"[OCR Error: {e}]"
    
    def _encode_image_base64(self, image_path: str) -> Optional[str]:
        """Encode image to base64 for Ollama."""
        try:
            with open(image_path, "rb") as f:
                return base64.b64encode(f.read()).decode("utf-8")
        except Exception as e:
            logger.error(f"Failed to encode image: {e}")
            return None
    
    def describe_image(
        self, 
        image_path: str, 
        prompt: str = "Describe this image in detail.",
        include_ocr: bool = True
    ) -> VisionResult:
        """
        Analyze and describe an image using LLaVA.
        
        Args:
            image_path: Path to the image
            prompt: Custom prompt for the analysis
            include_ocr: Also run OCR and include text
            
        Returns:
            VisionResult with description and extracted text
        """
        result = VisionResult(success=False)
        
        # Check if image exists
        if not os.path.exists(image_path):
            result.error = f"Image not found: {image_path}"
            return result
        
        # Get OCR text if requested
        if include_ocr and self.tesseract_available:
            result.extracted_text = self.ocr_image(image_path)
        
        # If Ollama not available, return OCR only
        if not self.ollama_client:
            if result.extracted_text:
                result.success = True
                result.description = f"[Vision model not available. OCR text: {result.extracted_text[:200]}...]"
            else:
                result.error = "Vision model not available and OCR failed"
            return result
        
        # Encode image for Ollama
        image_b64 = self._encode_image_base64(image_path)
        if not image_b64:
            result.error = "Failed to encode image"
            return result
        
        try:
            # Call LLaVA via Ollama
            response = self.ollama_client.chat(
                model=self.vision_model,
                messages=[{
                    "role": "user",
                    "content": prompt,
                    "images": [image_b64]
                }]
            )
            
            result.description = response['message']['content'].strip()
            result.success = True
            result.confidence = 0.85  # LLaVA generally reliable
            
            logger.info(f"👁️ Image described: {result.description[:100]}...")
            
        except Exception as e:
            logger.error(f"Vision analysis failed: {e}")
            result.error = str(e)
            
            # Fallback to OCR-only if we have it
            if result.extracted_text:
                result.success = True
                result.description = f"[Vision model error. Text found: {result.extracted_text[:200]}]"
        
        return result
    
    def describe_screen(self, monitor: int = 1) -> VisionResult:
        """
        Capture and describe the current screen.
        
        Args:
            monitor: Which monitor to capture (1 = primary)
            
        Returns:
            VisionResult with screen description
        """
        # Capture screenshot
        screenshot_path = self.capture_screenshot(monitor=monitor)
        
        if not screenshot_path:
            return VisionResult(
                success=False,
                error="Failed to capture screenshot"
            )
        
        # Describe it
        result = self.describe_image(
            screenshot_path,
            prompt="You are analyzing a computer screenshot. Describe what you see: "
                   "What application is open? What is the user doing? "
                   "What text or UI elements are visible?"
        )
        
        # Optionally clean up screenshot
        # os.remove(screenshot_path)
        
        return result
    
    def analyze_for_task(self, image_path: str, task_description: str) -> VisionResult:
        """
        Analyze an image in the context of a specific task.
        
        Args:
            image_path: Path to the image
            task_description: What the user is trying to do
            
        Returns:
            VisionResult with task-relevant analysis
        """
        prompt = f"""You are helping with this task: {task_description}

Analyze this image and provide information relevant to the task.
Be specific and actionable. If you see text, read it carefully.
If you see UI elements, describe their state and purpose.
"""
        return self.describe_image(image_path, prompt=prompt)
    
    def find_text_in_image(self, image_path: str, search_text: str) -> Dict[str, Any]:
        """
        Search for specific text in an image.
        
        Args:
            image_path: Path to the image
            search_text: Text to find
            
        Returns:
            Dict with 'found' (bool), 'context' (surrounding text)
        """
        ocr_text = self.ocr_image(image_path)
        
        if not ocr_text:
            return {"found": False, "context": "", "error": "OCR failed"}
        
        search_lower = search_text.lower()
        text_lower = ocr_text.lower()
        
        if search_lower in text_lower:
            # Find surrounding context
            idx = text_lower.find(search_lower)
            start = max(0, idx - 50)
            end = min(len(ocr_text), idx + len(search_text) + 50)
            context = ocr_text[start:end]
            
            return {
                "found": True,
                "context": f"...{context}...",
                "full_text": ocr_text
            }
        
        return {
            "found": False,
            "context": "",
            "full_text": ocr_text
        }


# =============================================================================
# CONVENIENCE FUNCTIONS (for tool registration)
# =============================================================================

_vision_client = None

def get_vision_client() -> VisionClient:
    """Get or create the singleton vision client."""
    global _vision_client
    if _vision_client is None:
        _vision_client = VisionClient()
    return _vision_client


def capture_screenshot(monitor: int = 1) -> str:
    """
    Capture a screenshot of the current screen.
    
    Args:
        monitor: Monitor number (1 = primary)
        
    Returns:
        Path to saved screenshot or error message
    """
    client = get_vision_client()
    path = client.capture_screenshot(monitor=monitor)
    return path if path else "Error: Screenshot capture failed"


def analyze_image(image_path: str, prompt: str = None) -> str:
    """
    Analyze an image and describe its contents.
    
    Args:
        image_path: Path to the image file
        prompt: Optional custom prompt
        
    Returns:
        Description of the image
    """
    client = get_vision_client()
    result = client.describe_image(
        image_path, 
        prompt=prompt or "Describe this image in detail."
    )
    
    if result.success:
        response = result.description
        if result.extracted_text:
            response += f"\n\nText found in image:\n{result.extracted_text[:500]}"
        return response
    else:
        return f"Error: {result.error}"


def ocr_image(image_path: str) -> str:
    """
    Extract text from an image using OCR.
    
    Args:
        image_path: Path to the image file
        
    Returns:
        Extracted text
    """
    client = get_vision_client()
    return client.ocr_image(image_path)


def describe_screen() -> str:
    """
    Capture and describe the current screen.
    
    Returns:
        Description of what's on screen
    """
    client = get_vision_client()
    result = client.describe_screen()
    
    if result.success:
        return result.description
    else:
        return f"Error: {result.error}"


# =============================================================================
# MAIN (for testing)
# =============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("=" * 60)
    print("🔍 ALFRED Vision Module Test")
    print("=" * 60)
    
    client = VisionClient()
    
    # Test screenshot
    print("\n[TEST 1] Screenshot capture...")
    path = client.capture_screenshot()
    if path:
        print(f"✅ Screenshot saved: {path}")
        
        # Test OCR
        print("\n[TEST 2] OCR extraction...")
        text = client.ocr_image(path)
        print(f"✅ OCR found {len(text)} characters")
        if text:
            print(f"   Preview: {text[:200]}...")
        
        # Test description
        print("\n[TEST 3] Image description...")
        result = client.describe_image(path)
        if result.success:
            print(f"✅ Description: {result.description[:300]}...")
        else:
            print(f"⚠️ Description failed: {result.error}")
    else:
        print("❌ Screenshot failed")
    
    print("\n" + "=" * 60)
    print("Vision module test complete!")

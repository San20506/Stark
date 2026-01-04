#!/usr/bin/env python3
"""
ALFRED Vision Module Test
Tests the vision capabilities: screenshots, OCR, and image description.

Run with: python tests/test_vision.py
"""

import sys
import os
import time

# Add ALFRED root to path
alfred_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, alfred_root)

# ============================================================================
# VISION TESTS
# ============================================================================

def test_vision_module():
    """Run vision module tests."""
    
    print("=" * 60)
    print("🔍 ALFRED Vision Module Test")
    print("=" * 60)
    
    results = {"passed": 0, "failed": 0, "skipped": 0}
    
    # Test 1: Import vision module
    print("\n[TEST 1] Import vision module...")
    try:
        from agents.vision import VisionClient, get_vision_client, VisionResult
        print("✅ Vision module imported successfully")
        results["passed"] += 1
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        results["failed"] += 1
        return results
    
    # Test 2: Create vision client
    print("\n[TEST 2] Create VisionClient...")
    try:
        client = VisionClient()
        print(f"✅ VisionClient created")
        print(f"   Vision model: {client.vision_model}")
        print(f"   Tesseract available: {client.tesseract_available}")
        print(f"   Screenshot available: {client.mss_available}")
        results["passed"] += 1
    except Exception as e:
        print(f"❌ VisionClient creation failed: {e}")
        results["failed"] += 1
        return results
    
    # Test 3: Screenshot capture
    print("\n[TEST 3] Screenshot capture...")
    if client.mss_available:
        try:
            path = client.capture_screenshot()
            if path and os.path.exists(path):
                size = os.path.getsize(path)
                print(f"✅ Screenshot saved: {path}")
                print(f"   Size: {size / 1024:.1f} KB")
                results["passed"] += 1
                
                # Use this screenshot for further tests
                screenshot_path = path
            else:
                print("❌ Screenshot capture returned None")
                results["failed"] += 1
                screenshot_path = None
        except Exception as e:
            print(f"❌ Screenshot failed: {e}")
            results["failed"] += 1
            screenshot_path = None
    else:
        print("⏭️ Skipped - mss not installed")
        print("   Install with: pip install mss")
        results["skipped"] += 1
        screenshot_path = None
    
    # Test 4: OCR extraction
    print("\n[TEST 4] OCR text extraction...")
    if client.tesseract_available and screenshot_path:
        try:
            text = client.ocr_image(screenshot_path)
            if text:
                print(f"✅ OCR extracted {len(text)} characters")
                print(f"   Preview: {text[:100].replace(chr(10), ' ')}...")
                results["passed"] += 1
            else:
                print("⚠️ OCR returned empty text (may be normal if no text on screen)")
                results["passed"] += 1
        except Exception as e:
            print(f"❌ OCR failed: {e}")
            results["failed"] += 1
    elif not client.tesseract_available:
        print("⏭️ Skipped - Tesseract not installed")
        print("   Install Tesseract: https://github.com/tesseract-ocr/tesseract")
        print("   Then: pip install pytesseract")
        results["skipped"] += 1
    else:
        print("⏭️ Skipped - No screenshot available")
        results["skipped"] += 1
    
    # Test 5: Image description (requires LLaVA)
    print("\n[TEST 5] Image description (LLaVA)...")
    if client.ollama_client and screenshot_path:
        try:
            start = time.time()
            result = client.describe_image(screenshot_path)
            elapsed = time.time() - start
            
            if result.success:
                print(f"✅ Image described in {elapsed:.1f}s")
                print(f"   Description: {result.description[:150]}...")
                print(f"   Confidence: {result.confidence:.2f}")
                results["passed"] += 1
            else:
                print(f"⚠️ Description failed: {result.error}")
                results["failed"] += 1
        except Exception as e:
            print(f"❌ Description failed: {e}")
            results["failed"] += 1
    elif not client.ollama_client:
        print("⏭️ Skipped - Ollama not available")
        print("   Install Ollama and run: ollama pull llava:7b")
        results["skipped"] += 1
    else:
        print("⏭️ Skipped - No screenshot available")
        results["skipped"] += 1
    
    # Test 6: Benchmark tools integration
    print("\n[TEST 6] Benchmark tools integration...")
    try:
        from core.benchmark_tools import BENCHMARK_TOOLS
        
        vision_tools = ["screenshot", "describe_image", "describe_screen", "ocr", "image_objects"]
        found = []
        for tool in vision_tools:
            if tool in BENCHMARK_TOOLS:
                found.append(tool)
        
        print(f"✅ Vision tools registered: {found}")
        print(f"   Total tools in registry: {len(BENCHMARK_TOOLS)}")
        results["passed"] += 1
    except Exception as e:
        print(f"❌ Benchmark tools check failed: {e}")
        results["failed"] += 1
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST RESULTS")
    print("=" * 60)
    print(f"✅ Passed: {results['passed']}")
    print(f"❌ Failed: {results['failed']}")
    print(f"⏭️ Skipped: {results['skipped']}")
    
    if results["failed"] == 0:
        print("\n🎉 All tests passed!")
    else:
        print("\n⚠️ Some tests failed. Check dependencies.")
    
    # Installation hints
    if results["skipped"] > 0:
        print("\n" + "-" * 40)
        print("💡 To enable all vision features:")
        print("   pip install mss pillow pytesseract")
        print("   Install Tesseract OCR on your system")
        print("   ollama pull llava:7b")
    
    print("=" * 60)
    
    return results


def test_interactive():
    """Interactive test - describe current screen."""
    print("\n" + "=" * 60)
    print("🖥️ INTERACTIVE TEST: Describe Current Screen")
    print("=" * 60)
    
    try:
        from agents.vision import get_vision_client
        client = get_vision_client()
        
        print("\n📸 Capturing screen in 3 seconds...")
        time.sleep(3)
        
        result = client.describe_screen()
        
        if result.success:
            print(f"\n👁️ ALFRED sees:\n{result.description}")
            if result.extracted_text:
                print(f"\n📝 Text found:\n{result.extracted_text[:500]}")
        else:
            print(f"\n❌ Failed: {result.error}")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Test ALFRED Vision Module")
    parser.add_argument("--interactive", "-i", action="store_true", 
                        help="Run interactive screen description test")
    args = parser.parse_args()
    
    if args.interactive:
        test_interactive()
    else:
        results = test_vision_module()
        sys.exit(0 if results["failed"] == 0 else 1)

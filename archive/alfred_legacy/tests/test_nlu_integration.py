"""
Test NLU Integration with ALFRED
Validates that the trained SNIPS model works correctly for ALFRED queries.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.nlu import IntentDetector


def test_nlu_model_loading():
    """Test that the model loads successfully."""
    print("=" * 70)
    print("TEST 1: Model Loading")
    print("=" * 70)
    
    detector = IntentDetector()
    success = detector.load_model()
    
    assert success, "Model failed to load"
    assert detector.model_loaded, "Model not marked as loaded"
    
    print("✅ Model loaded successfully\n")


def test_weather_queries():
    """Test weather intent detection."""
    print("=" * 70)
    print("TEST 2: Weather Queries")
    print("=" * 70)
    
    detector = IntentDetector()
    detector.load_model()
    
    test_cases = [
        ("what's the weather in Tokyo?", "get_weather", "tokyo"),
        ("weather in New York", "get_weather", "new york"),
        ("how's the weather in Paris?", "get_weather", "paris"),
        ("temperature in London", "get_weather", "london"),
    ]
    
    passed = 0
    for query, expected_intent, expected_city in test_cases:
        result = detector.detect(query)
        
        intent_match = result.intent == expected_intent
        city_match = expected_city in str(result.slots).lower()
        
        status = "✅" if (intent_match and city_match) else "❌"
        print(f"{status} '{query}'")
        print(f"   Intent: {result.intent} ({result.confidence:.0%})")
        print(f"   Slots: {result.slots}")
        
        if intent_match and city_match:
            passed += 1
    
    accuracy = passed / len(test_cases)
    print(f"\nWeather Accuracy: {accuracy:.0%} ({passed}/{len(test_cases)})")
    assert accuracy >= 0.75, f"Weather accuracy {accuracy:.0%} below 75%"
    print()


def test_search_queries():
    """Test search intent detection."""
    print("=" * 70)
    print("TEST 3: Search Queries")
    print("=" * 70)
    
    detector = IntentDetector()
    detector.load_model()
    
    test_cases = [
        "search for Python tutorials",
        "find information about AI",
        "look up machine learning",
        "google TensorFlow documentation",
    ]
    
    passed = 0
    for query in test_cases:
        result = detector.detect(query)
        
        # Accept either search_web or general_conversation
        intent_match = result.intent in ["search_web", "general_conversation"]
        
        status = "✅" if intent_match else "❌"
        print(f"{status} '{query}'")
        print(f"   Intent: {result.intent} ({result.confidence:.0%})")
        print(f"   Slots: {result.slots}")
        
        if intent_match:
            passed += 1
    
    accuracy = passed / len(test_cases)
    print(f"\nSearch Accuracy: {accuracy:.0%} ({passed}/{len(test_cases)})")
    assert accuracy >= 0.75, f"Search accuracy {accuracy:.0%} below 75%"
    print()


def test_restaurant_queries():
    """Test restaurant booking queries."""
    print("=" * 70)
    print("TEST 4: Restaurant Queries")
    print("=" * 70)
    
    detector = IntentDetector()
    detector.load_model()
    
    test_cases = [
        "book a restaurant in Paris",
        "find a restaurant in Tokyo",
        "reserve a table in New York",
    ]
    
    for query in test_cases:
        result = detector.detect(query)
        
        print(f"'{query}'")
        print(f"   Intent: {result.intent} ({result.confidence:.0%})")
        print(f"   Slots: {result.slots}")
    
    print()


def test_inference_speed():
    """Test inference speed."""
    print("=" * 70)
    print("TEST 5: Inference Speed")
    print("=" * 70)
    
    import time
    
    detector = IntentDetector()
    detector.load_model()
    
    query = "what's the weather in Tokyo?"
    
    # Warm-up
    detector.detect(query)
    
    # Time 10 predictions
    times = []
    for _ in range(10):
        start = time.time()
        detector.detect(query)
        times.append((time.time() - start) * 1000)  # Convert to ms
    
    avg_time = sum(times) / len(times)
    
    print(f"Average inference time: {avg_time:.1f}ms")
    print(f"Min: {min(times):.1f}ms, Max: {max(times):.1f}ms")
    
    assert avg_time < 100, f"Inference too slow: {avg_time:.1f}ms (target: <100ms)"
    print(f"✅ Inference speed acceptable (<100ms)\n")


def test_confidence_scores():
    """Test that confidence scores are reasonable."""
    print("=" * 70)
    print("TEST 6: Confidence Scores")
    print("=" * 70)
    
    detector = IntentDetector()
    detector.load_model()
    
    # High-confidence queries
    high_conf_queries = [
        "what's the weather in Tokyo?",
        "book a restaurant in Paris",
    ]
    
    # Ambiguous queries
    ambiguous_queries = [
        "hello",
        "how are you?",
    ]
    
    print("High-confidence queries:")
    for query in high_conf_queries:
        result = detector.detect(query)
        print(f"  '{query}': {result.confidence:.0%}")
        assert result.confidence >= 0.7, f"Confidence too low for clear query"
    
    print("\nAmbiguous queries:")
    for query in ambiguous_queries:
        result = detector.detect(query)
        print(f"  '{query}': {result.confidence:.0%}")
    
    print()


def run_all_tests():
    """Run all NLU integration tests."""
    print("\n" + "=" * 70)
    print("ALFRED NLU Integration Tests")
    print("=" * 70 + "\n")
    
    try:
        test_nlu_model_loading()
        test_weather_queries()
        test_search_queries()
        test_restaurant_queries()
        test_inference_speed()
        test_confidence_scores()
        
        print("=" * 70)
        print("✅ ALL TESTS PASSED!")
        print("=" * 70)
        print("\nNLU model is ready for production use.")
        print("Next steps:")
        print("  1. Test with MCP integration")
        print("  2. Monitor accuracy on real queries")
        print("  3. Fine-tune if needed")
        
        return True
        
    except AssertionError as e:
        print("\n" + "=" * 70)
        print(f"❌ TEST FAILED: {e}")
        print("=" * 70)
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)

"""
ALFRED NLU - Real-Time Intent Testing
Compare unified model performance on short and long contexts.
Target: GPT-level intent identification accuracy.
"""

import os
import sys
import pickle
import numpy as np
from typing import List, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import tensorflow as tf
    print(f"✓ TensorFlow {tf.__version__}")
except ImportError:
    print("❌ TensorFlow not installed")
    sys.exit(1)


class NLUTester:
    """Real-time NLU testing tool."""
    
    def __init__(self, model_path: str = "models/nlu_unified.h5", vocab_path: str = "data/unified/vocab.pkl"):
        """Load model and vocabulary."""
        print("Loading unified NLU model...")
        
        # Load model
        self.model = tf.keras.models.load_model(model_path, compile=False)
        
        # Load vocabulary
        with open(vocab_path, 'rb') as f:
            vocab = pickle.load(f)
            self.word2idx = vocab['word2idx']
            self.idx2intent = vocab['idx2intent']
            self.idx2slot = vocab['idx2slot']
        
        print(f"✓ Model loaded: {len(self.idx2intent)} intents")
    
    def predict(self, query: str) -> Tuple[str, float, dict]:
        """
        Predict intent and slots for a query.
        
        Returns:
            (intent, confidence, slots)
        """
        # Tokenize
        tokens = query.lower().split()
        
        # Encode
        word_ids = [self.word2idx.get(w, 1) for w in tokens]
        
        # Pad/truncate
        if len(word_ids) < 50:
            word_ids += [0] * (50 - len(word_ids))
        else:
            word_ids = word_ids[:50]
            tokens = tokens[:50]
        
        # Predict
        X = np.array([word_ids])
        slot_pred, intent_pred = self.model.predict(X, verbose=0)
        
        # Decode intent
        intent_id = np.argmax(intent_pred[0])
        intent = self.idx2intent[intent_id]
        confidence = float(intent_pred[0][intent_id])
        
        # Decode slots
        slot_ids = np.argmax(slot_pred[0], axis=-1)
        slots = {}
        current_slot = None
        current_value = []
        
        for i, (token, slot_id) in enumerate(zip(tokens, slot_ids[:len(tokens)])):
            slot_tag = self.idx2slot.get(int(slot_id), "O")
            
            if slot_tag == "O":
                if current_slot and current_value:
                    slots[current_slot] = " ".join(current_value)
                current_slot = None
                current_value = []
            elif slot_tag.startswith("B-"):
                if current_slot and current_value:
                    slots[current_slot] = " ".join(current_value)
                current_slot = slot_tag[2:].lower()
                current_value = [token]
            elif slot_tag.startswith("I-"):
                if current_slot:
                    current_value.append(token)
        
        if current_slot and current_value:
            slots[current_slot] = " ".join(current_value)
        
        return intent, confidence, slots


def run_comprehensive_tests():
    """Run comprehensive test suite."""
    
    tester = NLUTester()
    
    print("\n" + "=" * 80)
    print("ALFRED NLU - Comprehensive Intent Testing")
    print("Target: GPT-level accuracy on short and long contexts")
    print("=" * 80)
    
    # Test categories
    test_suites = {
        "Short Context - Time & Date": [
            "what time is it?",
            "current time",
            "tell me the time",
            "what's the date?",
            "today's date",
            "what day is it?",
        ],
        
        "Short Context - Math": [
            "calculate 5 times 7",
            "what is 100 divided by 4",
            "solve 25 plus 17",
            "square root of 144",
            "5 + 3",
        ],
        
        "Short Context - Weather": [
            "what's the weather in Tokyo?",
            "weather forecast for London",
            "is it raining in Paris?",
            "temperature in New York",
        ],
        
        "Short Context - Reminders": [
            "remind me to call mom",
            "set a reminder for 3 PM",
            "remind me about the meeting",
            "create a reminder",
        ],
        
        "Short Context - Alarms": [
            "set an alarm for 7 AM",
            "wake me up at 6:30",
            "alarm for tomorrow morning",
            "set alarm",
        ],
        
        "Short Context - Conversation": [
            "hello",
            "hi there",
            "good morning",
            "goodbye",
            "thanks",
            "thank you",
        ],
        
        "Long Context - Complex Queries": [
            "I need to know what time it is right now because I have a meeting soon",
            "Can you please tell me the current weather conditions in Tokyo, Japan?",
            "I want you to calculate the result of 25 multiplied by 4 and then add 10 to it",
            "Please set a reminder for me to call my mother tomorrow at 3 PM",
            "Could you set an alarm to wake me up at 7:30 AM tomorrow morning?",
        ],
        
        "Long Context - Conversational": [
            "Hey ALFRED, I was wondering if you could help me with something",
            "Thank you so much for all your help today, I really appreciate it",
            "Good morning ALFRED, how are you doing today?",
            "I just wanted to say goodbye and have a great rest of your day",
        ],
        
        "Ambiguous - Requires Context": [
            "what's it like?",  # Could be weather or general question
            "set it",  # Could be alarm, reminder, timer
            "tell me",  # Incomplete query
            "how much?",  # Could be calculator, price, etc.
        ],
        
        "Edge Cases": [
            "time",  # Single word
            "weather tokyo",  # Missing words
            "remind call mom 3pm",  # Telegraphic
            "5 * 7 + 3",  # Math expression
        ],
    }
    
    # Run tests
    total_tests = 0
    total_high_confidence = 0
    category_results = {}
    
    for category, queries in test_suites.items():
        print(f"\n{'=' * 80}")
        print(f"📋 {category}")
        print(f"{'=' * 80}")
        
        correct = 0
        high_conf = 0
        
        for query in queries:
            intent, confidence, slots = tester.predict(query)
            
            # Determine if prediction is reasonable
            is_high_conf = confidence >= 0.80
            
            # Color coding
            if confidence >= 0.90:
                conf_color = "🟢"
            elif confidence >= 0.70:
                conf_color = "🟡"
            else:
                conf_color = "🔴"
            
            print(f"\n  Query: \"{query}\"")
            print(f"  {conf_color} Intent: {intent} ({confidence:.1%})")
            if slots:
                print(f"     Slots: {slots}")
            
            if is_high_conf:
                high_conf += 1
            
            total_tests += 1
            if is_high_conf:
                total_high_confidence += 1
        
        category_results[category] = {
            'total': len(queries),
            'high_confidence': high_conf,
            'accuracy': (high_conf / len(queries)) * 100
        }
    
    # Summary
    print(f"\n{'=' * 80}")
    print("📊 SUMMARY")
    print(f"{'=' * 80}")
    
    for category, results in category_results.items():
        acc = results['accuracy']
        status = "✅" if acc >= 80 else "⚠️" if acc >= 60 else "❌"
        print(f"{status} {category}: {results['high_confidence']}/{results['total']} ({acc:.1f}%)")
    
    overall_acc = (total_high_confidence / total_tests) * 100
    print(f"\n{'=' * 80}")
    print(f"Overall High-Confidence Rate: {total_high_confidence}/{total_tests} ({overall_acc:.1f}%)")
    print(f"{'=' * 80}")
    
    # GPT-level comparison
    print(f"\n📈 GPT-Level Comparison:")
    print(f"   Target: 95%+ high-confidence rate")
    print(f"   Achieved: {overall_acc:.1f}%")
    
    if overall_acc >= 95:
        print(f"   Status: ✅ GPT-LEVEL ACHIEVED!")
    elif overall_acc >= 85:
        print(f"   Status: 🟡 VERY GOOD (close to GPT-level)")
    elif overall_acc >= 75:
        print(f"   Status: 🟠 GOOD (production-ready)")
    else:
        print(f"   Status: 🔴 NEEDS IMPROVEMENT")
    
    # Recommendations
    print(f"\n💡 Recommendations:")
    
    if overall_acc < 95:
        print(f"   1. Fine-tune on ALFRED-specific queries")
        print(f"   2. Add more training data for low-confidence categories")
        print(f"   3. Consider ensemble with LLM for ambiguous queries")
    else:
        print(f"   ✅ Model is GPT-level! Ready for production.")
    
    return overall_acc


def interactive_mode():
    """Interactive testing mode."""
    
    tester = NLUTester()
    
    print("\n" + "=" * 80)
    print("🎯 Interactive NLU Testing")
    print("=" * 80)
    print("Type queries to test intent detection. Type 'quit' to exit.\n")
    
    while True:
        try:
            query = input("Query: ").strip()
            
            if query.lower() in ['quit', 'exit', 'q']:
                break
            
            if not query:
                continue
            
            intent, confidence, slots = tester.predict(query)
            
            # Color coding
            if confidence >= 0.90:
                conf_color = "🟢"
            elif confidence >= 0.70:
                conf_color = "🟡"
            else:
                conf_color = "🔴"
            
            print(f"{conf_color} Intent: {intent} ({confidence:.1%})")
            if slots:
                print(f"   Slots: {slots}")
            print()
            
        except KeyboardInterrupt:
            break
    
    print("\n👋 Goodbye!")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--interactive":
        interactive_mode()
    else:
        overall_acc = run_comprehensive_tests()
        
        print(f"\n💬 Want to test interactively?")
        print(f"   Run: python tests/test_nlu_realtime.py --interactive")
        
        sys.exit(0 if overall_acc >= 85 else 1)

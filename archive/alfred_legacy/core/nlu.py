"""
ALFRED Intent Detection & Slot Filling
Using BiLSTM-CRF architecture based on SNUDerek/multiLSTM

This provides proper NLU (Natural Language Understanding):
- Intent Detection: What the user wants (time, weather, math, etc.)
- Slot Filling: Extract parameters (city name, numbers, dates, etc.)
"""

import numpy as np
import pickle
import os
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class NLUResult:
    """Result from NLU processing."""
    intent: str
    confidence: float
    slots: Dict[str, str]
    raw_query: str


class IntentDetector:
    """
    BiLSTM-CRF based intent detection and slot filling.
    
    For now, uses a hybrid approach:
    - Rule-based patterns for high-confidence cases
    - LLM-based classification for ambiguous cases
    
    TODO: Train actual BiLSTM-CRF model on ATIS/SNIPS dataset
    """
    
    # Intent labels
    INTENTS = [
        "get_time",
        "get_date", 
        "get_weather",
        "calculate",
        "convert_units",
        "search_web",
        "create_todo",
        "take_screenshot",
        "describe_screen",
        "generate_code",
        "general_conversation"
    ]
    
    # Slot types
    SLOT_TYPES = [
        "B-CITY",      # Beginning of city name
        "I-CITY",      # Inside city name
        "B-NUMBER",    # Beginning of number
        "I-NUMBER",    # Inside number
        "B-UNIT",      # Beginning of unit (celsius, km, etc.)
        "I-UNIT",      # Inside unit
        "B-DATE",      # Beginning of date
        "I-DATE",      # Inside date
        "O"            # Outside (no slot)
    ]
    
    def __init__(self, llm_client=None):
        """
        Initialize intent detector.
        
        Args:
            llm_client: Optional LLM for ambiguous cases
        """
        self.llm = llm_client
        self.model_loaded = False
    
    def detect(self, query: str) -> NLUResult:
        """
        Detect intent and extract slots from query.
        
        Pure ML-based approach:
        1. Trained model (JARVIS: 157 intents, 86.6% accuracy)
        2. LLM fallback (for out-of-domain queries)
        
        Args:
            query: User's natural language query
            
        Returns:
            NLUResult with intent, confidence, and slots
        """
        query_lower = query.lower()
        
        # Step 1: Try trained model (if loaded)
        if self.model_loaded:
            try:
                result = self._model_predict(query)
                # Trust model if reasonably confident
                if result.confidence >= 0.70:
                    return result
                # Low confidence - fall through to LLM
            except Exception as e:
                print(f"⚠️ Model prediction failed: {e}")
                # Fall through to LLM
        
        # Step 2: LLM fallback for out-of-domain or low-confidence queries
        if self.llm:
            intent, confidence = self._llm_classify(query)
            slots = self._extract_slots(query, intent)
            return NLUResult(
                intent=intent,
                confidence=confidence,
                slots=slots,
                raw_query=query
            )
        
        # Step 3: Default to conversation
        return NLUResult(
            intent="general_conversation",
            confidence=0.5,
            slots={},
            raw_query=query
        )
    
    def _model_predict(self, query: str) -> NLUResult:
        """
        Use trained BiLSTM model for prediction.
        
        Args:
            query: User query
            
        Returns:
            NLUResult with predictions
        """
        # Tokenize
        tokens = query.lower().split()
        
        # Encode words
        word_ids = [self.word2idx.get(w, 1) for w in tokens]  # 1 = <UNK>
        
        # Pad/truncate to max_len
        if len(word_ids) > self.max_len:
            word_ids = word_ids[:self.max_len]
        else:
            pad_len = self.max_len - len(word_ids)
            word_ids += [0] * pad_len
        
        # Convert to numpy array
        X = np.array([word_ids])
        
        # Predict
        slot_pred, intent_pred = self.model.predict(X, verbose=0)
        
        # Decode intent
        intent_id = np.argmax(intent_pred[0])
        intent_snips = self.idx2intent[intent_id]
        confidence = float(intent_pred[0][intent_id])
        
        # Map SNIPS intent to ALFRED intent
        intent_alfred = self._map_snips_to_alfred(intent_snips)
        
        # Decode slots
        slot_ids = np.argmax(slot_pred[0], axis=-1)
        slots = self._decode_slots(tokens, slot_ids[:len(tokens)])
        
        return NLUResult(
            intent=intent_alfred,
            confidence=confidence,
            slots=slots,
            raw_query=query
        )
    
    def _map_snips_to_alfred(self, model_intent: str) -> str:
        """Map model intent to ALFRED intent.
        
        For SNIPS intents (PascalCase), map to lowercase.
        For CLINC150 intents (snake_case), return as-is.
        """
        # SNIPS intents use PascalCase - map to standardized lowercase
        snips_mapping = {
            "GetWeather": "get_weather",
            "PlayMusic": "play_music",
            "BookRestaurant": "book_restaurant",
            "AddToPlaylist": "add_to_playlist",
            "RateBook": "rate_book",
            "SearchCreativeWork": "search_creative_work",
            "SearchScreeningEvent": "search_screening_event",
        }
        
        # If it's a SNIPS intent, map it
        if model_intent in snips_mapping:
            return snips_mapping[model_intent]
        
        # Otherwise return as-is (CLINC150 uses snake_case already)
        return model_intent
    
    def _decode_slots(self, tokens: List[str], slot_ids: np.ndarray) -> Dict[str, str]:
        """
        Decode slot predictions to extract entities.
        
        Args:
            tokens: Original tokens
            slot_ids: Predicted slot IDs
            
        Returns:
            Dictionary of slot_type -> value
        """
        slots = {}
        current_slot = None
        current_value = []
        
        for token, slot_id in zip(tokens, slot_ids):
            slot_tag = self.idx2slot.get(int(slot_id), "O")
            
            if slot_tag == "O":
                # Save current slot if any
                if current_slot and current_value:
                    slots[current_slot] = " ".join(current_value)
                current_slot = None
                current_value = []
            
            elif slot_tag.startswith("B-"):
                # Save previous slot if any
                if current_slot and current_value:
                    slots[current_slot] = " ".join(current_value)
                
                # Start new slot
                current_slot = slot_tag[2:].lower()  # Remove "B-"
                current_value = [token]
            
            elif slot_tag.startswith("I-"):
                # Continue current slot
                if current_slot:
                    current_value.append(token)
        
        # Save last slot
        if current_slot and current_value:
            slots[current_slot] = " ".join(current_value)
        
        return slots
    
    def _llm_classify(self, query: str) -> Tuple[str, float]:
        """Use LLM to classify intent for ambiguous queries."""
        
        prompt = f"""Classify the intent of this query. Choose ONE from:
{', '.join(self.INTENTS)}

Query: "{query}"

Respond with ONLY the intent name, nothing else."""
        
        try:
            response = self.llm.generate(prompt).strip().lower()
            
            # Find closest matching intent
            for intent in self.INTENTS:
                if intent.replace("_", " ") in response or intent in response:
                    return intent, 0.75
            
            return "general_conversation", 0.6
        except:
            return "general_conversation", 0.5
    
    def _extract_slots(self, query: str, intent: str) -> Dict[str, str]:
        """
        Extract slot values based on intent.
        
        This is a simplified version. Full BiLSTM-CRF would do proper
        sequence tagging with BIO labels.
        """
        import re
        
        slots = {}
        query_lower = query.lower()
        
        if intent == "get_weather":
            # Extract city name
            match = re.search(r'(?:in|at|for)\s+([a-zA-Z\s]+?)(?:\s|$|\?)', query_lower)
            if match:
                slots["city"] = match.group(1).strip()
        
        elif intent == "calculate":
            # Extract mathematical expression
            # Remove common prefixes
            expr = query_lower
            for prefix in ["calculate", "compute", "solve", "what is", "how much is"]:
                expr = expr.replace(prefix, "")
            expr = expr.strip().rstrip("?")
            if expr:
                slots["expression"] = expr
        
        elif intent == "convert_units":
            # Extract value, from_unit, to_unit
            match = re.search(r'(\d+(?:\.\d+)?)\s*([a-z]+)\s+(?:to|in)\s+([a-z]+)', query_lower)
            if match:
                slots["value"] = match.group(1)
                slots["from_unit"] = match.group(2)
                slots["to_unit"] = match.group(3)
        
        elif intent == "search_web":
            # Extract search query
            match = re.search(r'(?:search|look up|find)\s+(?:for\s+)?(.+)', query_lower)
            if match:
                slots["query"] = match.group(1).strip().rstrip("?")
        
        return slots
    
    def train_model(self, training_data_path: str):
        """
        Train BiLSTM-CRF model on ATIS or SNIPS dataset.
        
        TODO: Implement full training pipeline:
        1. Load ATIS/SNIPS data
        2. Build vocabulary
        3. Create character and word embeddings
        4. Build BiLSTM-CRF architecture
        5. Train with early stopping
        6. Save model weights
        
        Args:
            training_data_path: Path to training data
        """
        raise NotImplementedError("Model training not yet implemented. Using rule-based + LLM hybrid.")
    
    def load_model(self, model_path: str = "models/nlu_compact.h5", vocab_path: str = "data/snips/vocab.pkl"):
        """
        Load pre-trained BiLSTM model.
        
        Args:
            model_path: Path to saved model
            vocab_path: Path to vocabulary pickle
        """
        try:
            import tensorflow as tf
            
            # Load model
            if not os.path.exists(model_path):
                print(f"⚠️ Model not found at {model_path}")
                return False
            
            self.model = tf.keras.models.load_model(model_path, compile=False)
            
            # Load vocabulary
            if not os.path.exists(vocab_path):
                print(f"⚠️ Vocabulary not found at {vocab_path}")
                return False
            
            with open(vocab_path, 'rb') as f:
                vocab = pickle.load(f)
                self.word2idx = vocab['word2idx']
                self.idx2word = vocab['idx2word']
                self.intent2idx = vocab['intent2idx']
                self.idx2intent = vocab['idx2intent']
                self.slot2idx = vocab['slot2idx']
                self.idx2slot = vocab['idx2slot']
            
            self.model_loaded = True
            self.max_len = 50  # Same as training
            
            print(f"✓ NLU model loaded successfully")
            print(f"  Intents: {len(self.intent2idx)}")
            print(f"  Slots: {len(self.slot2idx)}")
            print(f"  Vocabulary: {len(self.word2idx)} words")
            
            return True
            
        except Exception as e:
            print(f"❌ Error loading model: {e}")
            self.model_loaded = False
            return False


# Singleton
_detector = None

def get_intent_detector(llm_client=None) -> IntentDetector:
    """Get or create the intent detector singleton."""
    global _detector
    if _detector is None:
        _detector = IntentDetector(llm_client)
    return _detector


# Quick test
if __name__ == "__main__":
    detector = IntentDetector()
    
    test_queries = [
        "What time is it?",
        "What's the weather in Tokyo?",
        "Calculate 25 times 4",
        "Convert 100 fahrenheit to celsius",
        "Search for Python tutorials",
        "Tell me a joke",
        "What is the square root of 144?",
    ]
    
    print("=" * 60)
    print("Intent Detection Test")
    print("=" * 60)
    
    for query in test_queries:
        result = detector.detect(query)
        print(f"\n'{query}'")
        print(f"  Intent: {result.intent} ({result.confidence:.0%})")
        if result.slots:
            print(f"  Slots: {result.slots}")

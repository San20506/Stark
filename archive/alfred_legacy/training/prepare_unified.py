"""
ALFRED NLU - Unified Training on CLINC150 + SNIPS
Combines both datasets for comprehensive intent coverage.

CLINC150: 150 intents, 23,700 samples (time, date, calculator, etc.)
SNIPS: 7 intents, 13,784 samples (weather, restaurant, music, etc.)

Total: ~157 intents, ~37K samples
Target: 95%+ accuracy on ALL ALFRED queries
"""

import os
import json
import pickle
import numpy as np
from collections import Counter
from typing import Dict, List, Tuple

# Import SNIPS loader
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from prepare_snips import SNIPSDataLoader, CompactEmbeddings


class UnifiedDataLoader:
    """Load and combine CLINC150 + SNIPS datasets."""
    
    def __init__(self, data_dir_clinc: str = "data", data_dir_snips: str = "data/snips"):
        self.data_dir_clinc = os.path.join("training", data_dir_clinc)
        self.data_dir_snips = data_dir_snips
        
        self.word2idx = {"<PAD>": 0, "<UNK>": 1}
        self.idx2word = {0: "<PAD>", 1: "<UNK>"}
        self.intent2idx = {}
        self.idx2intent = {}
        self.slot2idx = {"O": 0}
        self.idx2slot = {0: "O"}
    
    def load_clinc150(self, filter_intents: List[str] = None):
        """
        Load CLINC150 dataset.
        
        Args:
            filter_intents: Optional list of intents to keep (None = keep all)
            
        Returns:
            train_samples, test_samples
        """
        filepath = os.path.join(self.data_dir_clinc, "data_full.json")
        
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        train_samples = []
        test_samples = []
        
        # Process training data
        for text, intent in data['train']:
            if filter_intents and intent not in filter_intents:
                continue
            
            words = text.lower().split()
            slots = ['O'] * len(words)  # CLINC150 doesn't have slot labels
            train_samples.append((words, slots, intent))
        
        # Process test data
        for text, intent in data['test']:
            if filter_intents and intent not in filter_intents:
                continue
            
            words = text.lower().split()
            slots = ['O'] * len(words)
            test_samples.append((words, slots, intent))
        
        return train_samples, test_samples
    
    def load_snips(self):
        """Load SNIPS dataset."""
        loader = SNIPSDataLoader(self.data_dir_snips)
        return loader.load_all_domains()
    
    def combine_datasets(
        self,
        clinc_intents: List[str] = None,
        clinc_weight: float = 0.7
    ):
        """
        Combine CLINC150 and SNIPS datasets.
        
        Args:
            clinc_intents: Which CLINC150 intents to include (None = all)
            clinc_weight: Proportion of CLINC150 in final dataset (0.7 = 70%)
            
        Returns:
            combined_train, combined_test
        """
        print("Loading CLINC150...")
        clinc_train, clinc_test = self.load_clinc150(clinc_intents)
        print(f"  CLINC150 train: {len(clinc_train)}")
        print(f"  CLINC150 test: {len(clinc_test)}")
        
        print("\nLoading SNIPS...")
        snips_train, snips_test = self.load_snips()
        print(f"  SNIPS train: {len(snips_train)}")
        print(f"  SNIPS test: {len(snips_test)}")
        
        # Balance datasets
        target_clinc_train = int(len(clinc_train) * clinc_weight / (1 - clinc_weight))
        target_snips_train = len(snips_train)
        
        # If SNIPS is too small, oversample it
        if target_snips_train < target_clinc_train:
            multiplier = int(target_clinc_train / target_snips_train) + 1
            snips_train = snips_train * multiplier
            snips_train = snips_train[:target_clinc_train]
        
        # Combine
        combined_train = clinc_train + snips_train
        combined_test = clinc_test + snips_test
        
        # Shuffle
        import random
        random.shuffle(combined_train)
        random.shuffle(combined_test)
        
        print(f"\nCombined dataset:")
        print(f"  Train: {len(combined_train)}")
        print(f"  Test: {len(combined_test)}")
        
        return combined_train, combined_test
    
    def build_vocab(self, samples: List[Tuple], min_freq: int = 2):
        """Build vocabulary from combined samples."""
        word_counter = Counter()
        intent_set = set()
        slot_set = set()
        
        for words, slots, intent in samples:
            word_counter.update(words)
            intent_set.add(intent)
            slot_set.update(slots)
        
        # Build word vocabulary
        idx = 2  # Start after <PAD> and <UNK>
        for word, count in word_counter.most_common():
            if count >= min_freq:
                self.word2idx[word] = idx
                self.idx2word[idx] = word
                idx += 1
        
        # Build intent vocabulary
        for i, intent in enumerate(sorted(intent_set)):
            self.intent2idx[intent] = i
            self.idx2intent[i] = intent
        
        # Build slot vocabulary
        idx = 1  # Start after "O"
        for slot in sorted(slot_set):
            if slot != "O":
                self.slot2idx[slot] = idx
                self.idx2slot[idx] = slot
                idx += 1
        
        print(f"\nVocabulary built:")
        print(f"  Words: {len(self.word2idx)}")
        print(f"  Intents: {len(self.intent2idx)}")
        print(f"  Slots: {len(self.slot2idx)}")
    
    def encode_samples(self, samples: List[Tuple], max_len: int = 50):
        """Encode samples to numpy arrays."""
        X_words = []
        y_slots = []
        y_intents = []
        
        for words, slots, intent in samples:
            # Encode words
            word_ids = [self.word2idx.get(w, 1) for w in words]
            
            # Encode slots
            slot_ids = [self.slot2idx.get(s, 0) for s in slots]
            
            # Encode intent
            intent_id = self.intent2idx.get(intent, 0)
            
            # Pad/truncate
            if len(word_ids) > max_len:
                word_ids = word_ids[:max_len]
                slot_ids = slot_ids[:max_len]
            else:
                pad_len = max_len - len(word_ids)
                word_ids += [0] * pad_len
                slot_ids += [0] * pad_len
            
            X_words.append(word_ids)
            y_slots.append(slot_ids)
            y_intents.append(intent_id)
        
        return (
            np.array(X_words),
            np.array(y_slots),
            np.array(y_intents)
        )


# ALFRED-specific intents from CLINC150
ALFRED_CLINC_INTENTS = [
    # Time & Date
    "time", "date", "timezone",
    
    # Math & Conversion
    "calculator", "measurement_conversion",
    
    # Weather
    "weather",
    
    # Reminders & Scheduling
    "alarm", "reminder", "timer", "calendar",
    "calendar_update", "reminder_update",
    
    # Search & Info
    "definition", "spelling", "translate",
    "fun_fact", "next_holiday",
    
    # Conversation
    "greeting", "goodbye", "thank_you",
    "tell_joke", "yes", "no", "maybe",
    
    # Meta
    "cancel", "repeat",
    
    # Lists & Tasks
    "todo_list", "todo_list_update",
    "shopping_list", "shopping_list_update",
]


def prepare_unified_data():
    """Prepare unified CLINC150 + SNIPS dataset."""
    print("=" * 70)
    print("ALFRED NLU - Unified Training Data Preparation")
    print("CLINC150 (filtered) + SNIPS")
    print("=" * 70)
    
    loader = UnifiedDataLoader()
    
    # Combine datasets (70% CLINC150, 30% SNIPS)
    train_samples, test_samples = loader.combine_datasets(
        clinc_intents=ALFRED_CLINC_INTENTS,
        clinc_weight=0.7
    )
    
    # Build vocabulary
    loader.build_vocab(train_samples, min_freq=2)
    
    # Encode data
    print("\nEncoding data...")
    X_train, y_slots_train, y_intent_train = loader.encode_samples(train_samples)
    X_test, y_slots_test, y_intent_test = loader.encode_samples(test_samples)
    
    # Load embeddings
    print("\n" + "=" * 70)
    embedder = CompactEmbeddings(embedding_dim=50)
    embedding_matrix = embedder.create_embedding_matrix(loader.word2idx)
    
    # Save vocabulary
    vocab_path = "data/unified/vocab.pkl"
    os.makedirs(os.path.dirname(vocab_path), exist_ok=True)
    with open(vocab_path, 'wb') as f:
        pickle.dump({
            'word2idx': loader.word2idx,
            'idx2word': loader.idx2word,
            'intent2idx': loader.intent2idx,
            'idx2intent': loader.idx2intent,
            'slot2idx': loader.slot2idx,
            'idx2slot': loader.idx2slot
        }, f)
    print(f"\n✓ Vocabulary saved to {vocab_path}")
    
    print("\n" + "=" * 70)
    print("Data preparation complete!")
    print("=" * 70)
    print(f"Train samples: {len(X_train)}")
    print(f"Test samples: {len(X_test)}")
    print(f"Vocabulary size: {len(loader.word2idx)}")
    print(f"Intent classes: {len(loader.intent2idx)}")
    print(f"Slot classes: {len(loader.slot2idx)}")
    print(f"Embedding matrix shape: {embedding_matrix.shape}")
    
    return {
        'train': (X_train, y_slots_train, y_intent_train),
        'test': (X_test, y_slots_test, y_intent_test),
        'vocab': loader,
        'embeddings': embedding_matrix
    }


if __name__ == "__main__":
    data = prepare_unified_data()
    
    print("\n✅ Ready for unified model training!")
    print("\nNext: python training/train_unified.py")

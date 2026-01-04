"""
ALFRED NLU - Compact Architecture for Offline Use
Based on best practices for on-device NLU

Architecture:
- 50d word embeddings (compact)
- 64-unit biLSTM (1 layer)
- CRF for slot tagging
- Simple attention for intent

Datasets:
- SNIPS (primary): 7 domains, ~14K utterances
- CLINC150 (secondary): Selected domains
- ATIS (optional): Small fraction for travel

Target: 95%+ intent, 93%+ slot F1 with <500K parameters
"""

import os
import numpy as np
import pickle
import requests
import json
import zipfile
from typing import Dict, List, Tuple
from collections import Counter


class SNIPSDataLoader:
    """Load and preprocess SNIPS NLU benchmark dataset."""
    
    def __init__(self, data_dir: str = "data/snips"):
        self.data_dir = data_dir
        self.word2idx = {"<PAD>": 0, "<UNK>": 1}
        self.idx2word = {0: "<PAD>", 1: "<UNK>"}
        self.intent2idx = {}
        self.idx2intent = {}
        self.slot2idx = {"O": 0}
        self.idx2slot = {0: "O"}
        
        # SNIPS domains (all 7)
        self.domains = [
            "AddToPlaylist",
            "BookRestaurant", 
            "GetWeather",
            "PlayMusic",
            "RateBook",
            "SearchCreativeWork",
            "SearchScreeningEvent"
        ]
    
    def download_dataset(self):
        """Download SNIPS benchmark from GitHub."""
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Download from sonos/nlu-benchmark
        base_url = "https://github.com/sonos/nlu-benchmark/raw/master/2017-06-custom-intent-engines/"
        
        for domain in self.domains:
            train_file = f"{domain}/train_{domain}_full.json"
            test_file = f"{domain}/validate_{domain}.json"
            
            for filename in [train_file, test_file]:
                url = base_url + filename
                local_path = os.path.join(self.data_dir, filename.split('/')[-1])
                
                if not os.path.exists(local_path):
                    print(f"Downloading {filename.split('/')[-1]}...")
                    try:
                        response = requests.get(url)
                        response.raise_for_status()
                        with open(local_path, 'wb') as f:
                            f.write(response.content)
                        print(f"✓ Downloaded")
                    except Exception as e:
                        print(f"⚠️ Failed to download {filename}: {e}")
                else:
                    print(f"✓ {filename.split('/')[-1]} exists")
    
    def parse_snips_json(self, filepath: str) -> List[Tuple[List[str], List[str], str]]:
        """
        Parse SNIPS JSON format.
        
        Returns:
            List of (words, slots, intent)
        """
        samples = []
        
        # Extract domain from filename
        # e.g., "train_GetWeather_full.json" -> "GetWeather"
        filename = os.path.basename(filepath)
        if 'AddToPlaylist' in filename:
            domain = 'AddToPlaylist'
        elif 'BookRestaurant' in filename:
            domain = 'BookRestaurant'
        elif 'GetWeather' in filename:
            domain = 'GetWeather'
        elif 'PlayMusic' in filename:
            domain = 'PlayMusic'
        elif 'RateBook' in filename:
            domain = 'RateBook'
        elif 'SearchCreativeWork' in filename:
            domain = 'SearchCreativeWork'
        elif 'SearchScreeningEvent' in filename:
            domain = 'SearchScreeningEvent'
        else:
            domain = 'unknown'
        
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                data = json.load(f)
            
            # SNIPS format: {domain: [{data: [...], intent: ...}, ...]}
            domain_data = data.get(domain, [])
            
            for item in domain_data:
                words = []
                slots = []
                
                for token in item.get('data', []):
                    text = token.get('text', '').strip()
                    if not text:
                        continue
                    
                    # Split multi-word tokens
                    token_words = text.split()
                    slot_tag = token.get('entity', 'O')
                    
                    for i, word in enumerate(token_words):
                        words.append(word.lower())
                        # BIO tagging
                        if slot_tag == 'O' or not slot_tag:
                            slots.append('O')
                        elif i == 0:
                            slots.append(f'B-{slot_tag}')
                        else:
                            slots.append(f'I-{slot_tag}')
                
                intent = item.get('intent', domain)
                
                if words:
                    samples.append((words, slots, intent))
        
        except Exception as e:
            print(f"⚠️ Error parsing {filepath}: {e}")
        
        return samples
    
    def load_all_domains(self):
        """Load all SNIPS domains."""
        all_train = []
        all_test = []
        
        for domain in self.domains:
            train_file = os.path.join(self.data_dir, f"train_{domain}_full.json")
            test_file = os.path.join(self.data_dir, f"validate_{domain}.json")
            
            if os.path.exists(train_file):
                all_train.extend(self.parse_snips_json(train_file))
            
            if os.path.exists(test_file):
                all_test.extend(self.parse_snips_json(test_file))
        
        return all_train, all_test
    
    def build_vocab(self, samples: List[Tuple], min_freq: int = 2):
        """Build vocabulary from samples."""
        word_counter = Counter()
        intent_set = set()
        slot_set = set()
        
        for words, slots, intent in samples:
            word_counter.update(words)
            intent_set.add(intent)
            slot_set.update(slots)
        
        # Build word vocabulary (keep words with freq >= min_freq)
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
        
        print(f"Vocabulary built:")
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
            word_ids = [self.word2idx.get(w, 1) for w in words]  # 1 = <UNK>
            
            # Encode slots
            slot_ids = [self.slot2idx.get(s, 0) for s in slots]  # 0 = O
            
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


class CompactEmbeddings:
    """Compact 50d embeddings for offline use."""
    
    def __init__(self, embedding_dim: int = 50):
        self.embedding_dim = embedding_dim
        self.embeddings = {}
    
    def load_glove_50d(self, glove_dir: str = "data/glove"):
        """Load GloVe 50d (smallest, fastest)."""
        filepath = os.path.join(glove_dir, "glove.6B.50d.txt")
        
        if not os.path.exists(filepath):
            print(f"⚠️ GloVe 50d not found at {filepath}")
            print("   Download from: https://nlp.stanford.edu/data/glove.6B.zip")
            return {}
        
        print(f"Loading GloVe 50d embeddings...")
        
        embeddings = {}
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                parts = line.strip().split()
                word = parts[0]
                vector = np.array([float(x) for x in parts[1:]])
                embeddings[word] = vector
        
        print(f"✓ Loaded {len(embeddings)} word vectors")
        return embeddings
    
    def create_embedding_matrix(self, word2idx: Dict[str, int]):
        """Create compact embedding matrix."""
        if not self.embeddings:
            self.embeddings = self.load_glove_50d()
        
        vocab_size = len(word2idx)
        embedding_matrix = np.random.randn(vocab_size, self.embedding_dim) * 0.01
        
        # Set <PAD> to zeros
        embedding_matrix[0] = np.zeros(self.embedding_dim)
        
        found = 0
        for word, idx in word2idx.items():
            if word in self.embeddings:
                embedding_matrix[idx] = self.embeddings[word]
                found += 1
        
        coverage = (found / vocab_size) * 100
        print(f"✓ Embedding coverage: {found}/{vocab_size} ({coverage:.1f}%)")
        
        return embedding_matrix


def prepare_snips_data():
    """Prepare SNIPS dataset for training."""
    print("=" * 60)
    print("ALFRED NLU - Compact Architecture Data Prep")
    print("Dataset: SNIPS (Siri-like tasks)")
    print("=" * 60)
    
    # Load SNIPS
    loader = SNIPSDataLoader()
    loader.download_dataset()
    
    print("\nLoading SNIPS domains...")
    train_samples, test_samples = loader.load_all_domains()
    print(f"✓ Train: {len(train_samples)} samples")
    print(f"✓ Test: {len(test_samples)} samples")
    
    # Build vocabulary
    loader.build_vocab(train_samples, min_freq=2)
    
    # Encode data
    print("\nEncoding data...")
    X_train, y_slots_train, y_intent_train = loader.encode_samples(train_samples)
    X_test, y_slots_test, y_intent_test = loader.encode_samples(test_samples)
    
    # Load compact embeddings (50d)
    print("\n" + "=" * 60)
    embedder = CompactEmbeddings(embedding_dim=50)
    embedding_matrix = embedder.create_embedding_matrix(loader.word2idx)
    
    # Save vocabulary
    vocab_path = "data/snips/vocab.pkl"
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
    
    return {
        'train': (X_train, y_slots_train, y_intent_train),
        'test': (X_test, y_slots_test, y_intent_test),
        'vocab': loader,
        'embeddings': embedding_matrix
    }


if __name__ == "__main__":
    data = prepare_snips_data()
    
    print("\n" + "=" * 60)
    print("Data preparation complete!")
    print("=" * 60)
    print(f"Train samples: {len(data['train'][0])}")
    print(f"Test samples: {len(data['test'][0])}")
    print(f"Vocabulary size: {len(data['vocab'].word2idx)}")
    print(f"Intent classes: {len(data['vocab'].intent2idx)}")
    print(f"Slot classes: {len(data['vocab'].slot2idx)}")
    print(f"Embedding matrix shape: {data['embeddings'].shape}")
    print("\nReady for compact model training!")

"""
ALFRED NLU Model Training
BiLSTM-CRF for Intent Detection and Slot Filling

Dataset: ATIS from JointSLU (https://github.com/yvchen/JointSLU)
Embeddings: GloVe 6B (pre-trained, merged after training)

Training Pipeline:
1. Download ATIS dataset
2. Preprocess data (tokenize, create vocab)
3. Build BiLSTM-CRF model
4. Train on ATIS
5. Load GloVe embeddings and merge
6. Save trained model
"""

import os
import numpy as np
import pickle
import requests
import zipfile
from typing import Dict, List, Tuple
from collections import Counter


class ATISDataLoader:
    """Load and preprocess ATIS dataset from JointSLU."""
    
    def __init__(self, data_dir: str = "data/atis"):
        self.data_dir = data_dir
        self.word2idx = {"<PAD>": 0, "<UNK>": 1}
        self.idx2word = {0: "<PAD>", 1: "<UNK>"}
        self.intent2idx = {}
        self.idx2intent = {}
        self.slot2idx = {"O": 0}
        self.idx2slot = {0: "O"}
        
    def download_dataset(self):
        """Download ATIS dataset from JointSLU repo."""
        os.makedirs(self.data_dir, exist_ok=True)
        
        base_url = "https://raw.githubusercontent.com/yvchen/JointSLU/master/data/"
        files = [
            "atis.train.w-intent.iob",
            "atis.test.w-intent.iob"
        ]
        
        for filename in files:
            url = base_url + filename
            filepath = os.path.join(self.data_dir, filename)
            
            if not os.path.exists(filepath):
                print(f"Downloading {filename}...")
                response = requests.get(url)
                with open(filepath, 'wb') as f:
                    f.write(response.content)
                print(f"✓ {filename} downloaded")
            else:
                print(f"✓ {filename} already exists")
    
    def parse_line(self, line: str) -> Tuple[List[str], List[str], str]:
        """
        Parse ATIS format line.
        
        Format: BOS word1 slot1 word2 slot2 ... EOS intent
        Example: BOS show O me O flights O EOS atis_flight
        
        Returns:
            (words, slots, intent)
        """
        parts = line.strip().split()
        
        if len(parts) < 3:
            return [], [], ""
        
        # Remove BOS/EOS
        if parts[0] == "BOS":
            parts = parts[1:]
        
        # Last element is intent
        intent = parts[-1]
        parts = parts[:-1]
        
        if parts[-1] == "EOS":
            parts = parts[:-1]
        
        # Alternate between words and slots
        words = []
        slots = []
        for i in range(0, len(parts), 2):
            if i + 1 < len(parts):
                words.append(parts[i])
                slots.append(parts[i + 1])
        
        return words, slots, intent
    
    def build_vocab(self, train_file: str):
        """Build vocabulary from training data."""
        filepath = os.path.join(self.data_dir, train_file)
        
        word_counter = Counter()
        intent_set = set()
        slot_set = set()
        
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                words, slots, intent = self.parse_line(line)
                word_counter.update(words)
                intent_set.add(intent)
                slot_set.update(slots)
        
        # Build word vocabulary (keep words with freq > 1)
        idx = 2  # Start after <PAD> and <UNK>
        for word, count in word_counter.most_common():
            if count > 1:
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
    
    def load_data(self, filename: str, max_len: int = 50) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Load and encode data.
        
        Returns:
            (X_words, y_slots, y_intents)
        """
        filepath = os.path.join(self.data_dir, filename)
        
        X_words = []
        y_slots = []
        y_intents = []
        
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                words, slots, intent = self.parse_line(line)
                
                if not words:
                    continue
                
                # Encode words
                word_ids = [self.word2idx.get(w, 1) for w in words]  # 1 = <UNK>
                
                # Encode slots
                slot_ids = [self.slot2idx.get(s, 0) for s in slots]  # 0 = O
                
                # Encode intent
                intent_id = self.intent2idx.get(intent, 0)
                
                # Pad/truncate to max_len
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


class GloVeLoader:
    """Load pre-trained GloVe embeddings."""
    
    def __init__(self, glove_dir: str = "data/glove"):
        self.glove_dir = glove_dir
        self.embeddings = {}
    
    def download_glove(self):
        """Download GloVe 6B embeddings."""
        os.makedirs(self.glove_dir, exist_ok=True)
        
        zip_path = os.path.join(self.glove_dir, "glove.6B.zip")
        
        if not os.path.exists(zip_path):
            print("Downloading GloVe 6B (862MB)...")
            print("This may take several minutes...")
            
            url = "https://nlp.stanford.edu/data/wordvecs/glove.6B.zip"
            response = requests.get(url, stream=True)
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(zip_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0:
                        percent = (downloaded / total_size) * 100
                        print(f"\rProgress: {percent:.1f}%", end="")
            
            print("\n✓ GloVe downloaded")
            
            # Extract
            print("Extracting...")
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(self.glove_dir)
            print("✓ Extracted")
    
    def load_embeddings(self, dim: int = 100) -> Dict[str, np.ndarray]:
        """
        Load GloVe embeddings.
        
        Args:
            dim: Embedding dimension (50, 100, 200, or 300)
        
        Returns:
            Dict mapping word -> embedding vector
        """
        filename = f"glove.6B.{dim}d.txt"
        filepath = os.path.join(self.glove_dir, filename)
        
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"GloVe file not found: {filepath}")
        
        print(f"Loading GloVe {dim}d embeddings...")
        
        embeddings = {}
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                parts = line.strip().split()
                word = parts[0]
                vector = np.array([float(x) for x in parts[1:]])
                embeddings[word] = vector
        
        print(f"✓ Loaded {len(embeddings)} word vectors")
        return embeddings
    
    def create_embedding_matrix(self, word2idx: Dict[str, int], dim: int = 100) -> np.ndarray:
        """
        Create embedding matrix for vocabulary.
        
        Args:
            word2idx: Vocabulary mapping
            dim: Embedding dimension
        
        Returns:
            Embedding matrix (vocab_size x dim)
        """
        if not self.embeddings:
            self.embeddings = self.load_embeddings(dim)
        
        vocab_size = len(word2idx)
        embedding_matrix = np.random.randn(vocab_size, dim) * 0.01
        
        # Set <PAD> to zeros
        embedding_matrix[0] = np.zeros(dim)
        
        found = 0
        for word, idx in word2idx.items():
            if word in self.embeddings:
                embedding_matrix[idx] = self.embeddings[word]
                found += 1
        
        coverage = (found / vocab_size) * 100
        print(f"✓ Embedding coverage: {found}/{vocab_size} ({coverage:.1f}%)")
        
        return embedding_matrix


def prepare_training_data():
    """
    Download and prepare ATIS dataset + GloVe embeddings.
    
    Returns:
        (train_data, test_data, vocab, embeddings)
    """
    print("=" * 60)
    print("ALFRED NLU Training - Data Preparation")
    print("=" * 60)
    
    # Load ATIS dataset
    loader = ATISDataLoader()
    loader.download_dataset()
    loader.build_vocab("atis.train.w-intent.iob")
    
    print("\nLoading training data...")
    X_train, y_slots_train, y_intent_train = loader.load_data("atis.train.w-intent.iob")
    print(f"✓ Train: {len(X_train)} samples")
    
    print("\nLoading test data...")
    X_test, y_slots_test, y_intent_test = loader.load_data("atis.test.w-intent.iob")
    print(f"✓ Test: {len(X_test)} samples")
    
    # Load GloVe embeddings
    print("\n" + "=" * 60)
    glove = GloVeLoader()
    glove.download_glove()
    embedding_matrix = glove.create_embedding_matrix(loader.word2idx, dim=100)
    
    # Save vocabulary
    vocab_path = "data/atis/vocab.pkl"
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
    # Prepare data
    data = prepare_training_data()
    
    print("\n" + "=" * 60)
    print("Data preparation complete!")
    print("=" * 60)
    print(f"Train samples: {len(data['train'][0])}")
    print(f"Test samples: {len(data['test'][0])}")
    print(f"Vocabulary size: {len(data['vocab'].word2idx)}")
    print(f"Intent classes: {len(data['vocab'].intent2idx)}")
    print(f"Slot classes: {len(data['vocab'].slot2idx)}")
    print(f"Embedding matrix shape: {data['embeddings'].shape}")
    print("\nReady for model training!")

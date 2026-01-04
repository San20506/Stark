"""
ALFRED NLU - Compact Model for Offline Use
Target: <500K parameters, 95%+ intent, 93%+ slot F1

Architecture:
- 50d embeddings (compact)
- 64-unit biLSTM (single layer)
- TimeDistributed Dense for slots (CRF alternative)
- Simple max-pooling + dense for intent

This is optimized for on-device inference with minimal memory footprint.
"""

import os
import sys
import numpy as np

alfred_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, alfred_root)

try:
    import tensorflow as tf
    from tensorflow import keras
    from tensorflow.keras import layers, Model
    from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint, ReduceLROnPlateau
    print(f"✓ TensorFlow {tf.__version__}")
except ImportError:
    print("❌ TensorFlow not installed")
    sys.exit(1)


class CompactNLUModel:
    """
    Compact BiLSTM model for offline NLU.
    
    Target: <500K parameters
    Expected: 95%+ intent, 93%+ slot F1
    """
    
    def __init__(
        self,
        vocab_size: int,
        num_intents: int,
        num_slots: int,
        embedding_dim: int = 50,      # Compact
        lstm_units: int = 64,          # Small but effective
        dropout: float = 0.2           # Light regularization
    ):
        self.vocab_size = vocab_size
        self.num_intents = num_intents
        self.num_slots = num_slots
        self.embedding_dim = embedding_dim
        self.lstm_units = lstm_units
        self.dropout = dropout
        self.model = None
    
    def build_model(self, embedding_matrix: np.ndarray = None, max_len: int = 50):
        """Build compact model."""
        
        # Input
        input_words = layers.Input(shape=(max_len,), dtype='int32', name='input_words')
        
        # Embedding layer (50d, compact)
        if embedding_matrix is not None:
            embedding = layers.Embedding(
                input_dim=self.vocab_size,
                output_dim=self.embedding_dim,
                weights=[embedding_matrix],
                trainable=True,  # Fine-tune
                mask_zero=True,
                name='embedding'
            )(input_words)
        else:
            embedding = layers.Embedding(
                input_dim=self.vocab_size,
                output_dim=self.embedding_dim,
                mask_zero=True,
                name='embedding'
            )(input_words)
        
        # Light dropout
        embedding = layers.Dropout(self.dropout)(embedding)
        
        # Single biLSTM layer (64 units = 128 total)
        lstm_out = layers.Bidirectional(
            layers.LSTM(
                self.lstm_units,
                return_sequences=True,
                dropout=self.dropout,
                recurrent_dropout=0.1
            ),
            name='bilstm'
        )(embedding)
        
        # Slot filling: TimeDistributed Dense
        slot_output = layers.TimeDistributed(
            layers.Dense(self.num_slots, activation='softmax'),
            name='slot_output'
        )(lstm_out)
        
        # Intent classification: Max pooling + dense
        # Simple but effective for intent
        intent_pooled = layers.GlobalMaxPooling1D()(lstm_out)
        intent_dense = layers.Dense(32, activation='relu')(intent_pooled)
        intent_dense = layers.Dropout(self.dropout)(intent_dense)
        intent_output = layers.Dense(
            self.num_intents,
            activation='softmax',
            name='intent_output'
        )(intent_dense)
        
        # Build model
        self.model = Model(
            inputs=input_words,
            outputs=[slot_output, intent_output]
        )
        
        print("✓ Compact model built")
        return self.model
    
    def compile_model(self, learning_rate: float = 0.001):
        """Compile with optimized settings."""
        
        self.model.compile(
            optimizer=keras.optimizers.Adam(learning_rate),
            loss={
                'slot_output': 'sparse_categorical_crossentropy',
                'intent_output': 'sparse_categorical_crossentropy'
            },
            loss_weights={
                'slot_output': 1.0,
                'intent_output': 0.5  # Intent is secondary
            },
            metrics={
                'slot_output': 'accuracy',
                'intent_output': 'accuracy'
            }
        )
        
        print("✓ Model compiled")
    
    def train(
        self,
        X_train, y_slots_train, y_intent_train,
        X_val, y_slots_val, y_intent_val,
        epochs: int = 100,
        batch_size: int = 32,
        model_save_path: str = "models/nlu_compact.h5"
    ):
        """Train the compact model."""
        os.makedirs(os.path.dirname(model_save_path), exist_ok=True)
        
        # Callbacks
        callbacks = [
            EarlyStopping(
                monitor='val_intent_output_accuracy',  # Focus on intent
                patience=10,
                restore_best_weights=True,
                verbose=1
            ),
            ModelCheckpoint(
                model_save_path,
                monitor='val_loss',
                save_best_only=True,
                verbose=1
            ),
            ReduceLROnPlateau(
                monitor='val_loss',
                factor=0.5,
                patience=5,
                min_lr=0.00001,
                verbose=1
            )
        ]
        
        # Train
        history = self.model.fit(
            X_train,
            {
                'slot_output': y_slots_train,
                'intent_output': y_intent_train
            },
            validation_data=(
                X_val,
                {
                    'slot_output': y_slots_val,
                    'intent_output': y_intent_val
                }
            ),
            epochs=epochs,
            batch_size=batch_size,
            callbacks=callbacks,
            verbose=1
        )
        
        print(f"\n✓ Training complete. Best model saved to {model_save_path}")
        return history
    
    def summary(self):
        """Print model summary."""
        if self.model:
            self.model.summary()
            
            # Count parameters
            total_params = self.model.count_params()
            print(f"\n📊 Total parameters: {total_params:,}")
            print(f"   Target: <500,000")
            print(f"   Status: {'✅ PASS' if total_params < 500000 else '⚠️ OVER'}")


def train_compact_model():
    """Main training function for compact model."""
    
    print("=" * 70)
    print("ALFRED NLU - Compact Model Training")
    print("Target: <500K params, 95%+ intent, 93%+ slot F1")
    print("=" * 70)
    
    # Load SNIPS data
    print("\n1. Loading SNIPS data...")
    
    from training.prepare_snips import prepare_snips_data
    data = prepare_snips_data()
    
    X_train, y_slots_train, y_intent_train = data['train']
    X_test, y_slots_test, y_intent_test = data['test']
    vocab = data['vocab']
    embedding_matrix = data['embeddings']
    
    # Split train into train/val
    val_split = int(len(X_train) * 0.9)
    X_val = X_train[val_split:]
    y_slots_val = y_slots_train[val_split:]
    y_intent_val = y_intent_train[val_split:]
    
    X_train = X_train[:val_split]
    y_slots_train = y_slots_train[:val_split]
    y_intent_train = y_intent_train[:val_split]
    
    print(f"   Train: {len(X_train)} samples")
    print(f"   Val: {len(X_val)} samples")
    print(f"   Test: {len(X_test)} samples")
    
    # Build compact model
    print("\n2. Building compact model...")
    
    model = CompactNLUModel(
        vocab_size=len(vocab.word2idx),
        num_intents=len(vocab.intent2idx),
        num_slots=len(vocab.slot2idx),
        embedding_dim=50,   # Compact
        lstm_units=64,      # Small
        dropout=0.2         # Light
    )
    
    model.build_model(embedding_matrix=embedding_matrix, max_len=50)
    model.compile_model(learning_rate=0.001)
    model.summary()
    
    # Train
    print("\n3. Training compact model...")
    print("   This should take 15-30 minutes...")
    
    history = model.train(
        X_train, y_slots_train, y_intent_train,
        X_val, y_slots_val, y_intent_val,
        epochs=100,
        batch_size=32,
        model_save_path="models/nlu_compact.h5"
    )
    
    # Evaluate
    print("\n4. Evaluating on test set...")
    
    test_results = model.model.evaluate(
        X_test,
        {
            'slot_output': y_slots_test,
            'intent_output': y_intent_test
        },
        verbose=0
    )
    
    print(f"\n📊 Test Results:")
    print(f"   Slot Accuracy: {test_results[3]:.4f} (Target: 0.93)")
    print(f"   Intent Accuracy: {test_results[4]:.4f} (Target: 0.95)")
    
    # Check if targets met
    slot_ok = test_results[3] >= 0.93
    intent_ok = test_results[4] >= 0.95
    
    print(f"\n{'✅ SUCCESS!' if (slot_ok and intent_ok) else '⚠️ Below target, but may be acceptable'}")
    
    print("\n" + "=" * 70)
    print("Training Complete!")
    print("=" * 70)
    print(f"Model saved to: models/nlu_compact.h5")
    print(f"Vocabulary saved to: data/snips/vocab.pkl")
    print("\nNext: Integrate into core/nlu.py")


if __name__ == "__main__":
    train_compact_model()

"""
ALFRED NLU Model Training - BiLSTM-CRF
Train on ATIS dataset with pre-trained GloVe embeddings

Architecture:
1. Embedding Layer (initialized with GloVe)
2. Bidirectional LSTM
3. CRF Layer for slot filling
4. Dense Layer for intent classification

Run: python training/train_model.py
"""

import os
import sys
import numpy as np
import pickle

# Add ALFRED root to path
alfred_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, alfred_root)

try:
    import tensorflow as tf
    from tensorflow import keras
    from tensorflow.keras import layers, Model
    from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint
    print(f"✓ TensorFlow {tf.__version__}")
except ImportError:
    print("❌ TensorFlow not installed. Install with: pip install tensorflow")
    sys.exit(1)

# Use custom CRF implementation (no tensorflow-addons needed)
# NOTE: CRF disabled temporarily due to TensorFlow graph mode issues
# Using TimeDistributed Dense instead (~93% accuracy vs ~95% with CRF)
try:
    from training.crf_layer import CRF, crf_loss
    print("⚠️ CRF layer available but disabled (TF graph mode issues)")
    print("   Using TimeDistributed Dense instead")
    USE_CRF = False  # Disabled for now
except ImportError:
    print("⚠️ CRF layer not found, using TimeDistributed Dense")
    CRF = None
    USE_CRF = False


class BiLSTM_CRF_Model:
    """
    BiLSTM-CRF for Joint Intent Detection and Slot Filling.
    
    Architecture:
    - Embedding (GloVe initialized)
    - BiLSTM
    - CRF (slot filling)
    - Dense (intent classification)
    """
    
    def __init__(
        self,
        vocab_size: int,
        num_intents: int,
        num_slots: int,
        embedding_dim: int = 100,
        lstm_units: int = 128,
        dropout: float = 0.5
    ):
        self.vocab_size = vocab_size
        self.num_intents = num_intents
        self.num_slots = num_slots
        self.embedding_dim = embedding_dim
        self.lstm_units = lstm_units
        self.dropout = dropout
        self.model = None
    
    def build_model(self, embedding_matrix: np.ndarray = None, max_len: int = 50):
        """
        Build the BiLSTM-CRF model for joint slot filling and intent detection.
        
        Args:
            embedding_matrix: Pre-trained embeddings (GloVe)
            max_len: Maximum sequence length
        """
        # Input
        input_words = layers.Input(shape=(max_len,), dtype='int32', name='input_words')
        
        # Embedding layer
        if embedding_matrix is not None:
            embedding = layers.Embedding(
                input_dim=self.vocab_size,
                output_dim=self.embedding_dim,
                weights=[embedding_matrix],
                trainable=True,  # Fine-tune GloVe embeddings
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
        
        # Dropout
        embedding = layers.Dropout(self.dropout)(embedding)
        
        # Bidirectional LSTM
        lstm_out = layers.Bidirectional(
            layers.LSTM(
                self.lstm_units,
                return_sequences=True,
                dropout=self.dropout,
                recurrent_dropout=0.1
            ),
            name='bilstm'
        )(embedding)
        
        # Slot filling branch (sequence labeling)
        if USE_CRF and CRF is not None:
            # Use custom CRF layer
            print("   Using CRF layer for slot tagging")
            
            # Project LSTM output to number of slot tags
            slot_logits = layers.TimeDistributed(
                layers.Dense(self.num_slots),
                name='slot_logits'
            )(lstm_out)
            
            # Apply CRF layer
            crf_layer = CRF(self.num_slots, name='crf')
            slot_output = crf_layer(slot_logits)
        else:
            # Fallback to TimeDistributed Dense
            print("   Using TimeDistributed Dense for slot tagging")
            slot_output = layers.TimeDistributed(
                layers.Dense(self.num_slots, activation='softmax'),
                name='slot_output'
            )(lstm_out)
        
        # Intent classification branch
        # Take the last LSTM output
        intent_lstm = layers.Lambda(lambda x: x[:, -1, :])(lstm_out)
        intent_dense = layers.Dense(64, activation='relu')(intent_lstm)
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
        
        model_type = "BiLSTM-CRF" if USE_CRF else "BiLSTM with TimeDistributed Dense"
        print(f"✓ Model built ({model_type})")
        return self.model
    
    def compile_model(self, learning_rate: float = 0.001):
        """Compile the model with loss functions and optimizer."""
        
        # Determine output names and loss functions
        if USE_CRF and CRF is not None:
            slot_output_name = 'crf'
            
            # Get CRF layer from model
            crf_layer = None
            for layer in self.model.layers:
                if isinstance(layer, CRF):
                    crf_layer = layer
                    break
            
            if crf_layer is None:
                raise ValueError("CRF layer not found in model")
            
            # Create CRF loss function
            slot_loss = crf_loss(crf_layer)
        else:
            slot_output_name = 'slot_output'
            slot_loss = 'sparse_categorical_crossentropy'
        
        self.model.compile(
            optimizer=keras.optimizers.Adam(learning_rate),
            loss={
                slot_output_name: slot_loss,
                'intent_output': 'sparse_categorical_crossentropy'
            },
            loss_weights={
                slot_output_name: 1.0,
                'intent_output': 0.5  # Intent is secondary
            },
            metrics={
                slot_output_name: 'accuracy',
                'intent_output': 'accuracy'
            }
        )
        
        print("✓ Model compiled")
    
    def train(
        self,
        X_train, y_slots_train, y_intent_train,
        X_val, y_slots_val, y_intent_val,
        epochs: int = 50,
        batch_size: int = 32,
        model_save_path: str = "models/nlu_model.h5"
    ):
        """
        Train the model.
        
        Args:
            X_train, y_slots_train, y_intent_train: Training data
            X_val, y_slots_val, y_intent_val: Validation data
            epochs: Number of training epochs
            batch_size: Batch size
            model_save_path: Path to save best model
        """
        os.makedirs(os.path.dirname(model_save_path), exist_ok=True)
        
        # Callbacks
        callbacks = [
            EarlyStopping(
                monitor='val_loss',
                patience=15,  # Increased from 5 to allow more training
                restore_best_weights=True,
                verbose=1
            ),
            ModelCheckpoint(
                model_save_path,
                monitor='val_loss',
                save_best_only=True,
                verbose=1
            )
        ]
        
        # Determine output name
        slot_output_name = 'crf' if (USE_CRF and CRF is not None) else 'slot_output'
        
        # Train
        history = self.model.fit(
            X_train,
            {
                slot_output_name: y_slots_train,
                'intent_output': y_intent_train
            },
            validation_data=(
                X_val,
                {
                    slot_output_name: y_slots_val,
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


def train_nlu_model():
    """Main training function."""
    
    print("=" * 70)
    print("ALFRED NLU Model Training - BiLSTM-CRF")
    print("=" * 70)
    
    # Load prepared data
    print("\n1. Loading prepared data...")
    
    from training.prepare_data import prepare_training_data
    data = prepare_training_data()
    
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
    
    # Build model
    print("\n2. Building BiLSTM model with optimized hyperparameters...")
    print("   Target: 90%+ accuracy")
    
    model = BiLSTM_CRF_Model(
        vocab_size=len(vocab.word2idx),
        num_intents=len(vocab.intent2idx),
        num_slots=len(vocab.slot2idx),
        embedding_dim=100,
        lstm_units=256,      # Increased from 128 for more capacity
        dropout=0.3          # Reduced from 0.5 to prevent underfitting
    )
    
    model.build_model(embedding_matrix=embedding_matrix, max_len=50)
    model.compile_model(learning_rate=0.0001)  # Slower learning for better convergence
    model.summary()
    
    # Train
    print("\n3. Training model...")
    print("   Epochs: 150 (with early stopping)")
    print("   This will take 30-60 minutes...")
    print("   The model will stop early if it stops improving")
    
    history = model.train(
        X_train, y_slots_train, y_intent_train,
        X_val, y_slots_val, y_intent_val,
        epochs=150,          # Increased from 50
        batch_size=16,       # Reduced from 32 for better gradients
        model_save_path="models/nlu_bilstm_crf.h5"
    )
    
    # Evaluate on test set
    print("\n4. Evaluating on test set...")
    
    slot_output_name = 'crf' if (USE_CRF and CRF is not None) else 'slot_output'
    
    test_results = model.model.evaluate(
        X_test,
        {
            slot_output_name: y_slots_test,
            'intent_output': y_intent_test
        },
        verbose=0
    )
    
    print(f"\nTest Results:")
    print(f"   Slot Accuracy: {test_results[3]:.4f}")
    print(f"   Intent Accuracy: {test_results[4]:.4f}")
    
    print("\n" + "=" * 70)
    print("Training Complete!")
    print("=" * 70)
    print(f"Model saved to: models/nlu_bilstm_crf.h5")
    print(f"Vocabulary saved to: data/atis/vocab.pkl")
    print("\nNext step: Update core/nlu.py to use this trained model")


if __name__ == "__main__":
    train_nlu_model()

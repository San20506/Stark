"""
ALFRED NLU - Unified Model Training
Train on CLINC150 + SNIPS for comprehensive intent coverage.

Target: 95%+ intent accuracy, 93%+ slot accuracy
Same architecture as SNIPS model (proven to work)
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

from training.prepare_unified import prepare_unified_data


def train_unified_model():
    """Train unified model on CLINC150 + SNIPS."""
    
    print("=" * 70)
    print("ALFRED NLU - Unified Model Training")
    print("Target: 95%+ intent, 93%+ slot accuracy")
    print("=" * 70)
    
    # Load unified data
    print("\n1. Loading unified data (CLINC150 + SNIPS)...")
    
    data = prepare_unified_data()
    
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
    
    # Build model (same architecture as SNIPS)
    print("\n2. Building unified model...")
    print("   Architecture: 50d embeddings + 64-unit biLSTM")
    
    vocab_size = len(vocab.word2idx)
    num_intents = len(vocab.intent2idx)
    num_slots = len(vocab.slot2idx)
    
    # Input
    input_words = layers.Input(shape=(50,), dtype='int32', name='input_words')
    
    # Embedding (50d, compact)
    embedding = layers.Embedding(
        input_dim=vocab_size,
        output_dim=50,
        weights=[embedding_matrix],
        trainable=True,
        mask_zero=True,
        name='embedding'
    )(input_words)
    
    embedding = layers.Dropout(0.2)(embedding)
    
    # BiLSTM (64 units)
    lstm_out = layers.Bidirectional(
        layers.LSTM(
            64,
            return_sequences=True,
            dropout=0.2,
            recurrent_dropout=0.1
        ),
        name='bilstm'
    )(embedding)
    
    # Slot output
    slot_output = layers.TimeDistributed(
        layers.Dense(num_slots, activation='softmax'),
        name='slot_output'
    )(lstm_out)
    
    # Intent output
    intent_pooled = layers.GlobalMaxPooling1D()(lstm_out)
    intent_dense = layers.Dense(32, activation='relu')(intent_pooled)
    intent_dense = layers.Dropout(0.2)(intent_dense)
    intent_output = layers.Dense(
        num_intents,
        activation='softmax',
        name='intent_output'
    )(intent_dense)
    
    # Build model
    model = Model(
        inputs=input_words,
        outputs=[slot_output, intent_output]
    )
    
    # Compile
    model.compile(
        optimizer=keras.optimizers.Adam(0.001),
        loss={
            'slot_output': 'sparse_categorical_crossentropy',
            'intent_output': 'sparse_categorical_crossentropy'
        },
        loss_weights={
            'slot_output': 1.0,
            'intent_output': 0.5
        },
        metrics={
            'slot_output': 'accuracy',
            'intent_output': 'accuracy'
        }
    )
    
    print("✓ Model built and compiled")
    model.summary()
    
    total_params = model.count_params()
    print(f"\n📊 Total parameters: {total_params:,}")
    print(f"   Target: <500,000")
    print(f"   Status: {'✅ PASS' if total_params < 500000 else '⚠️ OVER'}")
    
    # Train
    print("\n3. Training unified model...")
    print("   This should take 20-40 minutes...")
    
    os.makedirs("models", exist_ok=True)
    
    callbacks = [
        EarlyStopping(
            monitor='val_intent_output_accuracy',
            patience=15,
            restore_best_weights=True,
            verbose=1
        ),
        ModelCheckpoint(
            "models/nlu_unified.h5",
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
    
    history = model.fit(
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
        epochs=100,
        batch_size=32,
        callbacks=callbacks,
        verbose=1
    )
    
    print(f"\n✓ Training complete. Best model saved to models/nlu_unified.h5")
    
    # Evaluate
    print("\n4. Evaluating on test set...")
    
    test_results = model.evaluate(
        X_test,
        {
            'slot_output': y_slots_test,
            'intent_output': y_intent_test
        },
        verbose=0
    )
    
    slot_acc = test_results[3]
    intent_acc = test_results[4]
    
    print(f"\n📊 Test Results:")
    print(f"   Slot Accuracy: {slot_acc:.4f} (Target: 0.93)")
    print(f"   Intent Accuracy: {intent_acc:.4f} (Target: 0.95)")
    
    # Check if targets met
    slot_ok = slot_acc >= 0.93
    intent_ok = intent_acc >= 0.95
    
    print(f"\n{'✅ SUCCESS!' if (slot_ok and intent_ok) else '⚠️ Close to target'}")
    
    # Test on ALFRED-specific queries
    print("\n5. Testing on ALFRED-specific queries...")
    
    test_queries = [
        "what time is it?",
        "what's the date today?",
        "calculate 5 times 7",
        "what's the weather in Tokyo?",
        "remind me to call mom",
        "set an alarm for 7 AM",
    ]
    
    for query in test_queries:
        tokens = query.lower().split()
        word_ids = [vocab.word2idx.get(w, 1) for w in tokens]
        
        # Pad
        if len(word_ids) < 50:
            word_ids += [0] * (50 - len(word_ids))
        else:
            word_ids = word_ids[:50]
        
        X = np.array([word_ids])
        slot_pred, intent_pred = model.predict(X, verbose=0)
        
        intent_id = np.argmax(intent_pred[0])
        intent = vocab.idx2intent[intent_id]
        confidence = float(intent_pred[0][intent_id])
        
        print(f"  '{query}'")
        print(f"    Intent: {intent} ({confidence:.0%})")
    
    print("\n" + "=" * 70)
    print("Training Complete!")
    print("=" * 70)
    print(f"Model saved to: models/nlu_unified.h5")
    print(f"Vocabulary saved to: data/unified/vocab.pkl")
    print("\nNext: Update core/nlu.py to use unified model")
    print("      Remove rule-based patterns (no longer needed!)")


if __name__ == "__main__":
    train_unified_model()

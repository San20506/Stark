"""
ALFRED NLU - JARVIS-Level Model Training
Train on ALL 150 CLINC150 + 7 SNIPS = 157 intents

Increased model capacity for comprehensive intent coverage.
Target: 90%+ intent accuracy, 94%+ slot accuracy
"""

import os
import sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import tensorflow as tf
    from tensorflow import keras
    from tensorflow.keras import layers, Model
    from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint, ReduceLROnPlateau
    print(f"✓ TensorFlow {tf.__version__}")
except ImportError:
    print("❌ TensorFlow not installed")
    sys.exit(1)

from training.prepare_jarvis import prepare_jarvis_data


def train_jarvis_model():
    """Train JARVIS-level model on 157 intents."""
    
    print("=" * 70)
    print("ALFRED NLU - JARVIS-Level Model Training")
    print("157 intents (150 CLINC + 7 SNIPS)")
    print("Target: 90%+ intent, 94%+ slot accuracy")
    print("=" * 70)
    
    # Load data
    print("\n1. Loading JARVIS-level data...")
    
    data = prepare_jarvis_data()
    
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
    
    # Build model with INCREASED capacity for 157 intents
    print("\n2. Building JARVIS-level model...")
    print("   Architecture: 50d embeddings + 128-unit biLSTM (increased capacity)")
    
    vocab_size = len(vocab.word2idx)
    num_intents = len(vocab.intent2idx)
    num_slots = len(vocab.slot2idx)
    
    print(f"   Vocab: {vocab_size}, Intents: {num_intents}, Slots: {num_slots}")
    
    # Input
    input_words = layers.Input(shape=(50,), dtype='int32', name='input_words')
    
    # Embedding (50d)
    embedding = layers.Embedding(
        input_dim=vocab_size,
        output_dim=50,
        weights=[embedding_matrix],
        trainable=True,
        mask_zero=True,
        name='embedding'
    )(input_words)
    
    embedding = layers.Dropout(0.3)(embedding)  # Increased dropout
    
    # BiLSTM (128 units - DOUBLED for 157 intents)
    lstm_out = layers.Bidirectional(
        layers.LSTM(
            128,  # Increased from 64
            return_sequences=True,
            dropout=0.3,
            recurrent_dropout=0.1
        ),
        name='bilstm'
    )(embedding)
    
    # Slot output
    slot_output = layers.TimeDistributed(
        layers.Dense(num_slots, activation='softmax'),
        name='slot_output'
    )(lstm_out)
    
    # Intent output (increased capacity)
    intent_pooled = layers.GlobalMaxPooling1D()(lstm_out)
    intent_dense = layers.Dense(64, activation='relu')(intent_pooled)  # Increased from 32
    intent_dense = layers.Dropout(0.3)(intent_dense)
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
    print(f"   Target: <1,000,000")
    print(f"   Status: {'✅ PASS' if total_params < 1000000 else '⚠️ OVER'}")
    
    # Train
    print("\n3. Training JARVIS-level model...")
    print("   This will take 30-60 minutes...")
    
    os.makedirs("models", exist_ok=True)
    
    callbacks = [
        EarlyStopping(
            monitor='val_intent_output_accuracy',
            patience=20,  # Increased patience
            restore_best_weights=True,
            verbose=1
        ),
        ModelCheckpoint(
            "models/nlu_jarvis.h5",
            monitor='val_loss',
            save_best_only=True,
            verbose=1
        ),
        ReduceLROnPlateau(
            monitor='val_loss',
            factor=0.5,
            patience=7,  # Increased patience
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
        epochs=150,  # Increased epochs
        batch_size=32,
        callbacks=callbacks,
        verbose=1
    )
    
    print(f"\n✓ Training complete. Best model saved to models/nlu_jarvis.h5")
    
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
    print(f"   Slot Accuracy: {slot_acc:.4f} (Target: 0.94)")
    print(f"   Intent Accuracy: {intent_acc:.4f} (Target: 0.90)")
    
    # Check if targets met
    slot_ok = slot_acc >= 0.94
    intent_ok = intent_acc >= 0.90
    
    if slot_ok and intent_ok:
        print(f"\n✅ SUCCESS! JARVIS-level accuracy achieved!")
    elif intent_acc >= 0.85:
        print(f"\n🟡 VERY GOOD! Close to JARVIS-level (85%+)")
    else:
        print(f"\n⚠️ Below target, but may still be usable")
    
    # Test on critical queries
    print("\n5. Testing on critical ALFRED queries...")
    
    test_queries = [
        "what time is it?",
        "what's the date?",
        "calculate 5 times 7",
        "weather in Tokyo",
        "remind me to call mom",
        "set alarm for 7 AM",
        "hello",
        "thank you",
    ]
    
    for query in test_queries:
        tokens = query.lower().split()
        word_ids = [vocab.word2idx.get(w, 1) for w in tokens]
        
        if len(word_ids) < 50:
            word_ids += [0] * (50 - len(word_ids))
        else:
            word_ids = word_ids[:50]
        
        X = np.array([word_ids])
        slot_pred, intent_pred = model.predict(X, verbose=0)
        
        intent_id = np.argmax(intent_pred[0])
        intent = vocab.idx2intent[intent_id]
        confidence = float(intent_pred[0][intent_id])
        
        status = "✅" if confidence >= 0.90 else "🟡" if confidence >= 0.70 else "🔴"
        print(f"  {status} '{query}' → {intent} ({confidence:.0%})")
    
    print("\n" + "=" * 70)
    print("JARVIS-Level Training Complete!")
    print("=" * 70)
    print(f"Model saved to: models/nlu_jarvis.h5")
    print(f"Vocabulary saved to: data/jarvis/vocab.pkl")
    print(f"\nIntents: {num_intents}")
    print(f"Parameters: {total_params:,}")
    print(f"Intent Accuracy: {intent_acc:.2%}")
    print(f"Slot Accuracy: {slot_acc:.2%}")
    print("\nThis model is JARVIS-ready and future-proof!")


if __name__ == "__main__":
    train_jarvis_model()

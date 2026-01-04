# ALFRED NLU Model Training

## Overview

Train a BiLSTM-CRF model for intent detection and slot filling using:
- **Dataset**: ATIS from JointSLU
- **Embeddings**: GloVe 6B (pre-trained, 100d)
- **Architecture**: Bidirectional LSTM + CRF

## Prerequisites

```bash
pip install tensorflow tensorflow-addons requests numpy
```

## Training Steps

### 1. Prepare Data

Downloads ATIS dataset and GloVe embeddings:

```bash
cd d:\ALFRED
python training/prepare_data.py
```

This will:
- Download ATIS train/test data from JointSLU
- Download GloVe 6B embeddings (~862MB)
- Build vocabulary
- Create embedding matrix
- Save to `data/atis/` and `data/glove/`

### 2. Train Model

```bash
python training/train_model.py
```

This will:
- Load ATIS data
- Initialize embeddings with GloVe (not training them, just using pre-trained)
- Build BiLSTM-CRF model
- Train for up to 50 epochs (early stopping enabled)
- Save best model to `models/nlu_bilstm_crf.h5`

**Training time**: 10-30 minutes (depending on hardware)

### 3. Update NLU Module

After training, update `core/nlu.py` to load the trained model:

```python
def load_model(self, model_path: str = "models/nlu_bilstm_crf.h5"):
    """Load trained BiLSTM-CRF model."""
    import tensorflow as tf
    self.model = tf.keras.models.load_model(model_path)
    
    # Load vocabulary
    with open("data/atis/vocab.pkl", "rb") as f:
        vocab = pickle.load(f)
        self.word2idx = vocab['word2idx']
        self.intent2idx = vocab['intent2idx']
        self.slot2idx = vocab['slot2idx']
```

## Model Architecture

```
Input (word IDs)
    ↓
Embedding Layer (GloVe 100d, fine-tuned)
    ↓
Dropout (0.5)
    ↓
Bidirectional LSTM (128 units)
    ↓
    ├─→ CRF Layer → Slot Tags (sequence)
    └─→ Dense → Intent (single label)
```

## Dataset Details

### ATIS (Airline Travel Information System)

- **Train**: ~4,400 samples
- **Test**: ~900 samples
- **Intents**: 21 classes (e.g., `atis_flight`, `atis_airfare`)
- **Slots**: 120+ slot types (e.g., `B-fromloc.city_name`, `I-depart_date`)

### GloVe Embeddings

- **Vocabulary**: 400k words
- **Dimension**: 100d (using glove.6B.100d.txt)
- **Coverage**: ~85% of ATIS vocabulary

## Expected Performance

Based on JointSLU paper:

- **Slot F1**: ~95%
- **Intent Accuracy**: ~98%

## Files Created

```
training/
├── prepare_data.py      # Data preparation script
├── train_model.py       # Model training script
└── README.md           # This file

data/
├── atis/
│   ├── atis.train.w-intent.iob
│   ├── atis.test.w-intent.iob
│   └── vocab.pkl
└── glove/
    ├── glove.6B.50d.txt
    ├── glove.6B.100d.txt
    ├── glove.6B.200d.txt
    └── glove.6B.300d.txt

models/
└── nlu_bilstm_crf.h5   # Trained model
```

## Troubleshooting

### TensorFlow not installed
```bash
pip install tensorflow
```

### TensorFlow Addons not available
```bash
pip install tensorflow-addons
```

If TensorFlow Addons fails, the script will use Dense layer instead of CRF (slightly lower performance but still works).

### Out of memory
Reduce batch size in `train_model.py`:
```python
batch_size=16  # Instead of 32
```

### Slow training
- Use GPU if available
- Reduce LSTM units: `lstm_units=64`
- Reduce epochs: `epochs=20`

## Next Steps

After training:

1. Test the model:
```bash
python -c "from core.nlu import IntentDetector; detector = IntentDetector(); detector.load_model(); print(detector.detect('show me flights to boston'))"
```

2. Integrate into MCP (already done in `agents/mcp.py`)

3. Run benchmarks to validate performance

## References

- JointSLU: https://github.com/yvchen/JointSLU
- GloVe: https://nlp.stanford.edu/projects/glove/
- Paper: "Multi-Domain Joint Semantic Frame Parsing using Bi-directional RNN-LSTM" (Hakkani-Tur et al., 2016)

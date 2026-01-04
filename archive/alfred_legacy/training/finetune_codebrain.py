"""
ALFRED Code Brain - LoRA Fine-tuning Script
Fine-tune DeepSeek models on custom documentation using LoRA.

Requirements:
    pip install peft transformers datasets accelerate bitsandbytes

Usage:
    python training/finetune_codebrain.py --dataset data/training/pytorch_training.jsonl
"""

import os
import sys
import argparse
import logging
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logger = logging.getLogger("FineTune")

# Model configuration - Nemotron 3 Nano (30B with 3B active, optimized for 24GB VRAM)
MODEL_CONFIGS = {
    "nemotron-nano": {
        "model_id": "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16",
        "target_modules": ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        "lora_r": 16,
        "lora_alpha": 32,
        "lora_dropout": 0.05,
    },
}


def load_dataset(filepath: str):
    """Load JSONL dataset."""
    from datasets import load_dataset
    
    dataset = load_dataset("json", data_files=filepath, split="train")
    logger.info(f"Loaded {len(dataset)} examples from {filepath}")
    return dataset


def format_prompt(example: dict) -> str:
    """Format example as instruction prompt."""
    return f"""### Instruction:
{example['instruction']}

### Response:
{example['output']}"""


def train(
    dataset_path: str,
    model_name: str = "deepseek-coder-1.3b",
    output_dir: str = "models/codebrain_lora",
    epochs: int = 3,
    batch_size: int = 4,
    learning_rate: float = 2e-4,
    max_length: int = 1024,
):
    """
    Fine-tune model using LoRA.
    
    Args:
        dataset_path: Path to JSONL training data
        model_name: Model to fine-tune
        output_dir: Where to save LoRA weights
        epochs: Training epochs
        batch_size: Batch size (reduce if OOM)
        learning_rate: Learning rate
        max_length: Maximum sequence length
    """
    import torch
    from transformers import (
        AutoTokenizer,
        AutoModelForCausalLM,
        TrainingArguments,
        Trainer,
        DataCollatorForSeq2Seq,
        BitsAndBytesConfig,
    )
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
    
    config = MODEL_CONFIGS.get(model_name, MODEL_CONFIGS["nemotron-nano"])
    model_id = config["model_id"]
    
    logger.info(f"🧠 Loading model: {model_id}")
    
    # Load tokenizer
    tokenizer = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    
    # Load model with 4-bit quantization
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_use_double_quant=True,
    )
    
    model = AutoModelForCausalLM.from_pretrained(
        model_id,
        quantization_config=bnb_config,
        device_map="auto",
        trust_remote_code=True,
    )
    
    # Prepare for LoRA training
    model = prepare_model_for_kbit_training(model)
    
    # Configure LoRA
    lora_config = LoraConfig(
        r=config["lora_r"],
        lora_alpha=config["lora_alpha"],
        target_modules=config["target_modules"],
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
    )
    
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()
    
    # Load and tokenize dataset
    logger.info(f"📚 Loading dataset: {dataset_path}")
    dataset = load_dataset(dataset_path)
    
    def tokenize(example):
        text = format_prompt(example)
        result = tokenizer(
            text,
            truncation=True,
            max_length=max_length,
            padding="max_length",
        )
        result["labels"] = result["input_ids"].copy()
        return result
    
    tokenized_dataset = dataset.map(tokenize, remove_columns=dataset.column_names)
    
    # Training arguments
    training_args = TrainingArguments(
        output_dir=output_dir,
        num_train_epochs=epochs,
        per_device_train_batch_size=batch_size,
        gradient_accumulation_steps=4,
        learning_rate=learning_rate,
        weight_decay=0.01,
        warmup_ratio=0.1,
        logging_steps=10,
        save_strategy="epoch",
        fp16=True,
        optim="paged_adamw_8bit",
        report_to="none",
    )
    
    # Data collator
    data_collator = DataCollatorForSeq2Seq(
        tokenizer=tokenizer,
        model=model,
        padding=True,
    )
    
    # Trainer
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized_dataset,
        data_collator=data_collator,
    )
    
    # Train
    logger.info("🚀 Starting training...")
    trainer.train()
    
    # Save LoRA weights
    logger.info(f"💾 Saving LoRA weights to {output_dir}")
    model.save_pretrained(output_dir)
    tokenizer.save_pretrained(output_dir)
    
    logger.info("✅ Training complete!")
    return output_dir


def main():
    parser = argparse.ArgumentParser(description="Fine-tune Code Brain on documentation")
    parser.add_argument("--dataset", required=True, help="Path to JSONL training data")
    parser.add_argument("--model", default="deepseek-coder-1.3b", choices=list(MODEL_CONFIGS.keys()))
    parser.add_argument("--output", default="models/codebrain_lora")
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--lr", type=float, default=2e-4)
    
    args = parser.parse_args()
    
    logging.basicConfig(level=logging.INFO)
    
    print("=" * 60)
    print("   ALFRED Code Brain - LoRA Fine-tuning")
    print("=" * 60)
    
    train(
        dataset_path=args.dataset,
        model_name=args.model,
        output_dir=args.output,
        epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.lr,
    )


if __name__ == "__main__":
    main()

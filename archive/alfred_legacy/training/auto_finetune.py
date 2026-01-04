"""
ALFRED Code Brain - Auto Fine-tuning Service
Automatically fine-tunes the model when training data changes.

Features:
- Watches training data directory for changes
- Triggers LoRA fine-tuning on new/updated data
- Incremental training (resumes from last checkpoint)
- Scheduled consolidation of multiple updates
"""

import os
import sys
import time
import json
import hashlib
import logging
import threading
from datetime import datetime
from typing import Optional, Dict
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logger = logging.getLogger("AutoFineTune")


class TrainingDataWatcher(FileSystemEventHandler):
    """Watch training data for changes and trigger fine-tuning."""
    
    def __init__(self, auto_trainer: 'AutoFineTuner'):
        self.trainer = auto_trainer
        self.pending_files = set()
        self.last_event_time = 0
        self.debounce_seconds = 30  # Wait 30s after last change before training
    
    def on_created(self, event: FileSystemEvent):
        if event.src_path.endswith('.jsonl'):
            logger.info(f"📄 New training data: {event.src_path}")
            self._queue_training(event.src_path)
    
    def on_modified(self, event: FileSystemEvent):
        if event.src_path.endswith('.jsonl'):
            logger.info(f"✏️ Training data updated: {event.src_path}")
            self._queue_training(event.src_path)
    
    def _queue_training(self, filepath: str):
        """Queue file for training with debounce."""
        self.pending_files.add(filepath)
        self.last_event_time = time.time()
        
        # Schedule check after debounce period
        threading.Timer(
            self.debounce_seconds + 1,
            self._check_and_train
        ).start()
    
    def _check_and_train(self):
        """Check if debounce period passed and trigger training."""
        if time.time() - self.last_event_time >= self.debounce_seconds:
            if self.pending_files:
                files = list(self.pending_files)
                self.pending_files.clear()
                self.trainer.train_on_files(files)


class AutoFineTuner:
    """
    Automatic fine-tuning service.
    
    Usage:
        tuner = AutoFineTuner()
        tuner.start()  # Starts watching and auto-training
        
        # Later...
        tuner.stop()
    """
    
    DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "training")
    STATE_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "training_state.json")
    MODEL_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models", "codebrain_lora")
    
    def __init__(self, model_name: str = "nemotron-nano"):
        self.model_name = model_name
        self.observer = None
        self.running = False
        self.training_lock = threading.Lock()
        self.state = self._load_state()
    
    def _load_state(self) -> Dict:
        """Load training state (file hashes, last train time)."""
        if os.path.exists(self.STATE_FILE):
            try:
                with open(self.STATE_FILE, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {"file_hashes": {}, "last_train": None, "train_count": 0}
    
    def _save_state(self):
        """Save training state."""
        os.makedirs(os.path.dirname(self.STATE_FILE), exist_ok=True)
        with open(self.STATE_FILE, 'w') as f:
            json.dump(self.state, f, indent=2)
    
    def _get_file_hash(self, filepath: str) -> str:
        """Get MD5 hash of file content."""
        with open(filepath, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()
    
    def _has_file_changed(self, filepath: str) -> bool:
        """Check if file has changed since last training."""
        if not os.path.exists(filepath):
            return False
        
        current_hash = self._get_file_hash(filepath)
        stored_hash = self.state["file_hashes"].get(filepath)
        
        return current_hash != stored_hash
    
    def start(self):
        """Start the auto fine-tuning service."""
        if self.running:
            return
        
        os.makedirs(self.DATA_DIR, exist_ok=True)
        
        # Check for existing files that need training
        self._initial_check()
        
        # Start file watcher
        self.observer = Observer()
        handler = TrainingDataWatcher(self)
        self.observer.schedule(handler, self.DATA_DIR, recursive=False)
        self.observer.start()
        
        self.running = True
        logger.info(f"🔄 Auto fine-tuning service started")
        logger.info(f"   Watching: {self.DATA_DIR}")
        logger.info(f"   Model: {self.model_name}")
    
    def stop(self):
        """Stop the service."""
        self.running = False
        if self.observer:
            self.observer.stop()
            self.observer.join()
        logger.info("🛑 Auto fine-tuning service stopped")
    
    def _initial_check(self):
        """Check existing files for changes."""
        changed_files = []
        
        for filename in os.listdir(self.DATA_DIR):
            if filename.endswith('.jsonl'):
                filepath = os.path.join(self.DATA_DIR, filename)
                if self._has_file_changed(filepath):
                    changed_files.append(filepath)
        
        if changed_files:
            logger.info(f"📋 Found {len(changed_files)} files with changes")
            self.train_on_files(changed_files)
    
    def train_on_files(self, filepaths: list):
        """Trigger fine-tuning on specific files."""
        if not self.training_lock.acquire(blocking=False):
            logger.warning("⚠️ Training already in progress, skipping")
            return
        
        try:
            logger.info(f"🚀 Starting fine-tuning on {len(filepaths)} files")
            
            # Merge all training files
            all_examples = []
            for filepath in filepaths:
                with open(filepath, 'r', encoding='utf-8') as f:
                    for line in f:
                        all_examples.append(json.loads(line))
            
            if not all_examples:
                logger.warning("No training examples found")
                return
            
            # Save merged dataset
            merged_path = os.path.join(self.DATA_DIR, "_merged_training.jsonl")
            with open(merged_path, 'w', encoding='utf-8') as f:
                for ex in all_examples:
                    f.write(json.dumps(ex, ensure_ascii=False) + '\n')
            
            logger.info(f"📊 Merged {len(all_examples)} examples")
            
            # Run fine-tuning
            self._run_training(merged_path)
            
            # Update state with new hashes
            for filepath in filepaths:
                self.state["file_hashes"][filepath] = self._get_file_hash(filepath)
            self.state["last_train"] = datetime.now().isoformat()
            self.state["train_count"] = self.state.get("train_count", 0) + 1
            self._save_state()
            
            logger.info("✅ Fine-tuning complete!")
            
        except Exception as e:
            logger.error(f"❌ Fine-tuning failed: {e}")
        finally:
            self.training_lock.release()
    
    def _run_training(self, dataset_path: str):
        """Execute the fine-tuning process."""
        from training.finetune_codebrain import train
        
        # Use incremental training (fewer epochs for updates)
        epochs = 1 if self.state.get("train_count", 0) > 0 else 3
        
        train(
            dataset_path=dataset_path,
            model_name=self.model_name,
            output_dir=self.MODEL_DIR,
            epochs=epochs,
            batch_size=2,  # Lower batch for stability
        )
    
    def get_status(self) -> Dict:
        """Get service status."""
        return {
            "running": self.running,
            "model": self.model_name,
            "data_dir": self.DATA_DIR,
            "model_dir": self.MODEL_DIR,
            "last_train": self.state.get("last_train"),
            "train_count": self.state.get("train_count", 0),
            "tracked_files": len(self.state.get("file_hashes", {}))
        }


# Singleton
_auto_tuner = None

def get_auto_finetuner(model_name: str = "nemotron-nano") -> AutoFineTuner:
    global _auto_tuner
    if _auto_tuner is None:
        _auto_tuner = AutoFineTuner(model_name)
    return _auto_tuner


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(message)s'
    )
    
    print("=" * 60)
    print("   ALFRED Auto Fine-tuning Service")
    print("=" * 60)
    
    tuner = get_auto_finetuner()
    
    print(f"\n📂 Data directory: {tuner.DATA_DIR}")
    print(f"🧠 Model: {tuner.model_name}")
    print(f"\nAdd/update .jsonl files in data/training/ to trigger training")
    print("Press Ctrl+C to stop\n")
    
    tuner.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n🛑 Stopping...")
        tuner.stop()
        print("✅ Done")

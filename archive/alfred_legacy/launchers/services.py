"""
ALFRED Services - Background services for Code Brain auto-training
"""

import os
import sys
import logging
import threading

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logger = logging.getLogger("AlfredServices")


class ALFREDServices:
    """
    Manages background services for ALFRED.
    
    Services:
    - Auto Fine-tuning: Watches for new training data
    - Doc Scraping: On-demand documentation fetching
    """
    
    def __init__(self):
        self.auto_tuner = None
        self.running = False
    
    def start_all(self):
        """Start all background services."""
        self.running = True
        
        # Start auto fine-tuning service
        try:
            from training.auto_finetune import get_auto_finetuner
            self.auto_tuner = get_auto_finetuner()
            self.auto_tuner.start()
            logger.info("✅ Auto fine-tuning service started")
        except Exception as e:
            logger.error(f"Failed to start auto fine-tuner: {e}")
        
        logger.info("✅ All ALFRED services started")
    
    def stop_all(self):
        """Stop all background services."""
        if self.auto_tuner:
            self.auto_tuner.stop()
        
        self.running = False
        logger.info("🛑 All ALFRED services stopped")
    
    def get_status(self) -> dict:
        """Get status of all services."""
        return {
            "running": self.running,
            "auto_finetune": self.auto_tuner.get_status() if self.auto_tuner else None
        }


# Integration with scheduler
def setup_training_watcher(scheduler):
    """
    Set up training data watcher with scheduler.
    
    This creates a scheduled task to periodically check
    for training data updates.
    """
    from training.auto_finetune import get_auto_finetuner
    
    tuner = get_auto_finetuner()
    
    # Add interval task to check for updates every hour
    scheduler.add_interval_task(
        task_id="code_brain_check",
        action="Check for new training data",
        hours=1
    )
    
    return tuner


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(message)s'
    )
    
    print("=" * 60)
    print("   ALFRED Background Services")
    print("=" * 60)
    
    services = ALFREDServices()
    services.start_all()
    
    print("\n📋 Services Status:")
    status = services.get_status()
    for key, val in status.items():
        print(f"   {key}: {val}")
    
    print("\nPress Ctrl+C to stop")
    
    import time
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n🛑 Stopping...")
        services.stop_all()
        print("✅ Done")

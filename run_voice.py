#!/usr/bin/env python3
"""
STARK Voice Mode Launcher
==========================
Start STARK in voice interaction mode.

Usage:
    python run_voice.py              # With wake word ("Hey STARK")
    python run_voice.py --no-wake    # Continuous listening
    python run_voice.py --text       # Text-only mode (no voice)
"""

import argparse
import logging
import sys

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger("STARK")


def main():
    parser = argparse.ArgumentParser(
        description="STARK Voice Mode Launcher",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_voice.py              # Voice mode with wake word
  python run_voice.py --no-wake    # Continuous voice (no wake word)
  python run_voice.py --text       # Text input mode
  python run_voice.py --query "What is Python?"  # Single query
        """,
    )
    
    parser.add_argument(
        "--no-wake",
        action="store_true",
        help="Disable wake word, use continuous listening",
    )
    parser.add_argument(
        "--text",
        action="store_true",
        help="Text-only mode (no voice input/output)",
    )
    parser.add_argument(
        "--query", "-q",
        type=str,
        help="Run a single query and exit",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress info messages",
    )
    
    args = parser.parse_args()
    
    if args.quiet:
        logging.getLogger().setLevel(logging.WARNING)
    
    # Import STARK
    try:
        from core.main import get_stark
    except ImportError as e:
        logger.error(f"Failed to import STARK: {e}")
        logger.error("Make sure you're running from the project root directory.")
        sys.exit(1)
    
    # Get STARK instance
    stark = get_stark()
    stark.start()
    
    try:
        if args.query:
            # Single query mode
            logger.info(f"Query: {args.query}")
            result = stark.predict(args.query)
            print(f"\n[{result.task}] {result.response}\n")
            
            if not args.text:
                stark.speak(result.response)
        
        elif args.text:
            # Text REPL mode
            print("\n" + "=" * 50)
            print("STARK Text Mode")
            print("Type your queries. Press Ctrl+C to exit.")
            print("=" * 50 + "\n")
            
            while True:
                try:
                    query = input("You: ").strip()
                    if not query:
                        continue
                    
                    result = stark.predict(query)
                    print(f"STARK [{result.task}]: {result.response}\n")
                    
                except KeyboardInterrupt:
                    print("\n")
                    break
        
        else:
            # Voice mode
            print("\n" + "=" * 50)
            print("STARK Voice Mode")
            if args.no_wake:
                print("Continuous listening enabled (no wake word)")
            else:
                print("Say 'Hey STARK' to activate")
            print("Press Ctrl+C to exit.")
            print("=" * 50 + "\n")
            
            stark.run_voice_mode(wake_word_enabled=not args.no_wake)
    
    except KeyboardInterrupt:
        pass
    finally:
        stark.stop()
        logger.info("STARK shutdown complete")


if __name__ == "__main__":
    main()

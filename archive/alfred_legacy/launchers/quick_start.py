#!/usr/bin/env python3
"""
Quick Start Guide for ALFRED
Run this to get started quickly!
"""

print("=" * 60)
print("🤖 ALFRED - Quick Start Guide")
print("=" * 60)

print("\n📋 What can ALFRED do?\n")
print("  ✅ 8 Native Tools (time, calc, memory, files, etc.)")
print("  ✅ 4 Generated Skills (weather, converter, etc.)")
print("  ✅ Learn new skills from the internet")
print("  ✅ Hybrid CLI + Voice input")
print()

print("🚀 Quick Start Options:\n")
print("  1. Hybrid Mode (Recommended)")
print("     python alfred_hybrid.py")
print()
print("  2. Voice Mode")
print("     python main.py")
print()
print("  3. Test Mode")
print("     python test_full_integration.py")
print()

print("💡 Example Commands:\n")
print("  - 'What time is it?'")
print("  - 'Calculate 50 times 2'")
print("  - 'What's the weather in Mumbai?'")
print("  - 'Convert 100 km to miles'")
print("  - 'Send an email' (will ask to learn)")
print()

print("📝 CLI Commands:\n")
print("  /tools   - List available tools")
print("  /skills  - List generated skills")
print("  /status  - Show system status")
print("  /help    - Show help")
print("  /quit    - Exit")
print()

print("=" * 60)
choice = input("Which mode do you want to run? (1/2/3): ").strip()

if choice == "1":
    print("\n🚀 Starting Hybrid Mode...")
    import subprocess
    subprocess.run([".venv/Scripts/python", "alfred_hybrid.py"])
elif choice == "2":
    print("\n🚀 Starting Voice Mode...")
    import subprocess
    subprocess.run([".venv/Scripts/python", "main.py"])
elif choice == "3":
    print("\n🚀 Running Tests...")
    import subprocess
    subprocess.run([".venv/Scripts/python", "test_full_integration.py"])
else:
    print("\n❌ Invalid choice. Run this script again.")

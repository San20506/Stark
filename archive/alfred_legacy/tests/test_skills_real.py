#!/usr/bin/env python3
"""
Test generated skills with ACTUAL results
"""

print("=" * 70)
print("ALFRED Generated Skills - REAL EXECUTION TEST")
print("=" * 70)

from skill_loader import skill_loader

# Reload all skills
print("\n🔄 Loading skills...")
skills = skill_loader.load_all_skills()
print(f"   Loaded: {skills}")

# ============================================================================
# Test 1: Weather
# ============================================================================
print("\n" + "=" * 70)
print("[1/3] WEATHER SKILL")
print("=" * 70)

weather = skill_loader.loaded_skills.get("get_weather")
if weather and hasattr(weather, "run"):
    print("\n📍 Mumbai:")
    result = weather.run(city="Mumbai")
    print(f"   {result}")
    
    print("\n📍 London:")
    result = weather.run(city="London")
    print(f"   {result}")
    
    print("\n📍 New York:")
    result = weather.run(city="New York")
    print(f"   {result}")
else:
    print("❌ Weather skill not loaded")

# ============================================================================
# Test 2: Unit Converter
# ============================================================================
print("\n" + "=" * 70)
print("[2/3] UNIT CONVERTER SKILL")
print("=" * 70)

converter = skill_loader.loaded_skills.get("unit_converter")
if converter and hasattr(converter, "run"):
    print("\n🔢 Conversions:")
    
    # Kilometers to Miles
    result = converter.run(value=100, from_unit="km", to_unit="miles")
    print(f"   {result}")
    
    # Celsius to Fahrenheit
    result = converter.run(value=30, from_unit="c", to_unit="f")
    print(f"   {result}")
    
    # Kilograms to Pounds
    result = converter.run(value=70, from_unit="kg", to_unit="lbs")
    print(f"   {result}")
    
    # Meters to Feet
    result = converter.run(value=10, from_unit="m", to_unit="ft")
    print(f"   {result}")
else:
    print("❌ Unit converter skill not loaded")

# ============================================================================
# Test 3: Translator
# ============================================================================
print("\n" + "=" * 70)
print("[3/3] TEXT TRANSLATOR SKILL")
print("=" * 70)

translator = skill_loader.loaded_skills.get("text_translator")
if translator and hasattr(translator, "run"):
    print("\n🌐 Translations:")
    
    result = translator.run(text="Hello, how are you?", to_lang="hi")
    print(f"   EN→HI: {result}")
    
    result = translator.run(text="Good morning", to_lang="es")
    print(f"   EN→ES: {result}")
else:
    print("❌ Translator skill not loaded")

# ============================================================================
# Summary
# ============================================================================
print("\n" + "=" * 70)
print("TEST COMPLETE")
print("=" * 70)
print(f"\n✅ Tested {len(skills)} skills with real execution")

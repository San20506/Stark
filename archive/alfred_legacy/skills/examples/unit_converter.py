"""
Skill: unit_converter
Converts between different units
"""

from typing import Any

SKILL_META = {
    "name": "unit_converter",
    "triggers": ["convert", "units", "kilometers", "miles", "celsius", "fahrenheit"],
    "requires": [],
    "description": "Convert between different units"
}

# Conversion factors
CONVERSIONS = {
    "km_to_miles": 0.621371,
    "miles_to_km": 1.60934,
    "c_to_f": lambda c: (c * 9/5) + 32,
    "f_to_c": lambda f: (f - 32) * 5/9,
    "kg_to_lbs": 2.20462,
    "lbs_to_kg": 0.453592,
    "m_to_ft": 3.28084,
    "ft_to_m": 0.3048,
    "l_to_gal": 0.264172,
    "gal_to_l": 3.78541,
}

def run(**kwargs) -> Any:
    """
    Convert between units.
    
    Args:
        value: Number to convert
        from_unit: Source unit (km, miles, c, f, kg, lbs, m, ft, l, gal)
        to_unit: Target unit
    
    Returns:
        Converted value string
    """
    value = kwargs.get("value")
    from_unit = kwargs.get("from_unit", "").lower()
    to_unit = kwargs.get("to_unit", "").lower()
    
    if not value:
        return "Usage: value=10, from_unit=km, to_unit=miles"
    
    try:
        value = float(value)
    except:
        return f"Invalid number: {value}"
    
    # Build conversion key
    key = f"{from_unit}_to_{to_unit}"
    
    if key not in CONVERSIONS:
        available = list(CONVERSIONS.keys())
        return f"Unknown conversion. Available: {available}"
    
    conversion = CONVERSIONS[key]
    
    if callable(conversion):
        result = conversion(value)
    else:
        result = value * conversion
    
    return f"{value} {from_unit} = {result:.2f} {to_unit}"

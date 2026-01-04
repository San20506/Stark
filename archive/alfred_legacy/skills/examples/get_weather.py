"""
Skill: get_weather
Gets weather using wttr.in (no API key needed)
"""

from typing import Any
import requests

SKILL_META = {
    "name": "get_weather",
    "triggers": ["weather", "temperature", "forecast", "climate"],
    "requires": ["requests"],
    "description": "Get current weather for a city"
}

def run(**kwargs) -> Any:
    """
    Get current weather for a city.
    
    Args:
        city: City name (default: Mumbai)
    
    Returns:
        Weather information string
    """
    city = kwargs.get("city", "Mumbai")
    
    try:
        # Use wttr.in - free, no API key needed
        url = f"https://wttr.in/{city}?format=%l:+%c+%t+%h+%w"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            return response.text.strip()
        else:
            return f"Could not get weather for {city}"
            
    except Exception as e:
        return f"Weather error: {e}"

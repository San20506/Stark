"""
Skill: text_translator
Translates text using free translation API
"""

from typing import Any
import requests

SKILL_META = {
    "name": "text_translator",
    "triggers": ["translate", "translation", "language"],
    "requires": ["requests"],
    "description": "Translate text between languages"
}

def run(**kwargs) -> Any:
    """
    Translate text between languages.
    
    Args:
        text: Text to translate
        to_lang: Target language code (en, hi, es, fr, de, etc.)
        from_lang: Source language (auto-detect if not specified)
    
    Returns:
        Translated text
    """
    text = kwargs.get("text", "")
    to_lang = kwargs.get("to_lang", "en")
    from_lang = kwargs.get("from_lang", "auto")
    
    if not text:
        return "Usage: text='Hello', to_lang='hi'"
    
    try:
        # Use LibreTranslate API (free)
        url = "https://libretranslate.com/translate"
        
        payload = {
            "q": text,
            "source": from_lang,
            "target": to_lang,
            "format": "text"
        }
        
        response = requests.post(url, json=payload, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            return result.get("translatedText", text)
        else:
            # Fallback: just return the text with note
            return f"[{to_lang}] {text} (translation API unavailable)"
            
    except Exception as e:
        return f"Translation error: {e}. Original: {text}"

#!/usr/bin/env python3
"""
PersonalityAdapter - Adaptive personality system for ALFRED

Learns user communication preferences from conversation patterns and
dynamically adjusts Alfred's personality to match user's style.
"""

import logging
import re
from typing import Dict, Optional
from datetime import datetime

logger = logging.getLogger("PersonalityAdapter")


class PersonalityAdapter:
    """
    Adaptive personality system that learns from user interactions.
    
    Tracks:
    - Formality level (casual vs. formal)
    - Verbosity preference (brief vs. detailed)
    - Humor level (serious vs. playful)
    - Favorite topics
    """
    
    # Default preferences (neutral starting point)
    DEFAULT_FORMALITY = 0.5  # 0=casual, 1=formal
    DEFAULT_VERBOSITY = 0.4  # 0=brief, 1=detailed
    DEFAULT_HUMOR = 0.6  # 0=serious, 1=humorous
    
    # Learning rate (how fast to adapt)
    LEARNING_RATE = 0.15  # Gradual adaptation
    
    def __init__(self, db):
        """
        Initialize personality adapter.
        
        Args:
            db: ConversationDatabase instance for preference storage
        """
        self.db = db
        self.preferences = self._load_preferences()
        self.interaction_count = int(self.preferences.get('interaction_count', '0'))
        
        logger.info(f"🎭 PersonalityAdapter initialized")
        logger.info(f"   Formality: {self.preferences.get('formality', self.DEFAULT_FORMALITY)}")
        logger.info(f"   Verbosity: {self.preferences.get('verbosity', self.DEFAULT_VERBOSITY)}")
        logger.info(f"   Humor: {self.preferences.get('humor', self.DEFAULT_HUMOR)}")
    
    def _load_preferences(self) -> Dict[str, float]:
        """Load preferences from database."""
        prefs = self.db.get_all_preferences()
        
        return {
            'formality': float(prefs.get('formality', self.DEFAULT_FORMALITY)),
            'verbosity': float(prefs.get('verbosity', self.DEFAULT_VERBOSITY)),
            'humor': float(prefs.get('humor', self.DEFAULT_HUMOR)),
            'interaction_count': prefs.get('interaction_count', '0'),
            'favorite_topics': prefs.get('favorite_topics', '')
        }
    
    def _save_preferences(self):
        """Save current preferences to database."""
        for key, value in self.preferences.items():
            self.db.save_preference(key, str(value))
    
    def analyze_interaction(self, user_msg: str, assistant_msg: str):
        """
        Analyze interaction and update preferences.
        
        Args:
            user_msg: User's message
            assistant_msg: Assistant's response
        """
        self.interaction_count += 1
        self.preferences['interaction_count'] = str(self.interaction_count)
        
        # Analyze formality
        user_formality = self._detect_formality(user_msg)
        self.preferences['formality'] = self._weighted_update(
            self.preferences['formality'],
            user_formality
        )
        
        # Analyze verbosity preference
        user_verbosity = self._detect_verbosity_preference(user_msg)
        self.preferences['verbosity'] = self._weighted_update(
            self.preferences['verbosity'],
            user_verbosity
        )
        
        # Analyze humor preference (based on positive/enthusiastic responses)
        humor_signal = self._detect_humor_affinity(user_msg)
        if humor_signal is not None:
            self.preferences['humor'] = self._weighted_update(
                self.preferences['humor'],
                humor_signal
            )
        
        # Extract topics
        topics = self._extract_topics(user_msg)
        if topics:
            self._update_favorite_topics(topics)
        
        # Save every 5 interactions to reduce DB writes
        if self.interaction_count % 5 == 0:
            self._save_preferences()
            logger.debug(f"📊 Preferences updated (interaction #{self.interaction_count})")
    
    def _weighted_update(self, current: float, new_signal: float) -> float:
        """Update preference with weighted average."""
        return current * (1 - self.LEARNING_RATE) + new_signal * self.LEARNING_RATE
    
    def _detect_formality(self, text: str) -> float:
        """
        Detect formality level of text.
        
        Returns:
            0.0 (very casual) to 1.0 (very formal)
        """
        text_lower = text.lower()
        words = text.split()
        
        if not words:
            return 0.5
        
        # Casual indicators
        casual_patterns = [
            r'\b(yeah|yep|yup|nah|nope|gonna|wanna|gotta|kinda|sorta)\b',
            r'\b(hey|heyy|sup|yo)\b',
            r'[!]{2,}',  # Multiple exclamation marks
            r'[\w]+ing\b',  # Lots of -ing words
        ]
        
        # Formal indicators
        formal_patterns = [
            r'\b(indeed|certainly|furthermore|however|therefore|moreover)\b',
            r'\b(could you|would you|may I|might I)\b',
            r'\b(please|kindly|appreciate)\b',
        ]
        
        casual_count = sum(len(re.findall(p, text_lower)) for p in casual_patterns)
        formal_count = sum(len(re.findall(p, text_lower)) for p in formal_patterns)
        
        # Check for complete sentences (formality indicator)
        has_proper_punctuation = text.strip().endswith(('.', '!', '?'))
        if has_proper_punctuation:
            formal_count += 1
        
        # Calculate formality score
        total_indicators = casual_count + formal_count
        if total_indicators == 0:
            return 0.5  # Neutral
        
        formality_score = formal_count / total_indicators
        return max(0.0, min(1.0, formality_score))
    
    def _detect_verbosity_preference(self, text: str) -> float:
        """
        Infer verbosity preference from message style.
        
        Longer, detailed questions → user prefers detailed responses
        Short questions → user prefers brief responses
        
        Returns:
            0.0 (prefers brief) to 1.0 (prefers detailed)
        """
        words = text.split()
        word_count = len(words)
        
        # Check for detail-seeking keywords
        detail_keywords = ['why', 'how', 'explain', 'detail', 'more', 'elaborate', 'specifically']
        detail_count = sum(1 for kw in detail_keywords if kw in text.lower())
        
        # Short questions (< 5 words) suggest brief preference
        if word_count < 5:
            return 0.2
        
        # Long questions (> 15 words) suggest detail preference
        if word_count > 15:
            return 0.8
        
        # Questions with detail keywords
        if detail_count > 0:
            return 0.9
        
        # Medium length → neutral
        return 0.5
    
    def _detect_humor_affinity(self, text: str) -> Optional[float]:
        """
        Detect if user enjoys humor.
        
        Returns:
            1.0 if positive/laughing, 0.0 if negative, None if neutral
        """
        text_lower = text.lower()
        
        # Positive humor indicators
        positive_patterns = ['lol', 'haha', 'lmao', '😂', '😄', '😆', 'funny', 'hilarious', 'that\'s great']
        if any(p in text_lower for p in positive_patterns):
            return 1.0
        
        # Negative humor indicators
        negative_patterns = ['not funny', 'serious', 'stop joking', 'be serious']
        if any(p in text_lower for p in negative_patterns):
            return 0.0
        
        return None  # No clear signal
    
    def _extract_topics(self, text: str) -> list:
        """Extract potential topics from text (simple keyword extraction)."""
        # This is a simplified version - could use NLP for better results
        text_lower = text.lower()
        
        topic_keywords = {
            'technology': ['computer', 'software', 'coding', 'programming', 'tech', 'ai'],
            'music': ['song', 'music', 'band', 'play', 'listen', 'genre'],
            'sports': ['game', 'play', 'team', 'sport', 'match', 'tennis', 'football'],
            'food': ['eat', 'food', 'restaurant', 'cook', 'recipe', 'meal'],
            'work': ['work', 'job', 'office', 'meeting', 'project', 'deadline'],
            'family': ['family', 'parent', 'kid', 'sibling', 'relative'],
        }
        
        found_topics = []
        for topic, keywords in topic_keywords.items():
            if any(kw in text_lower for kw in keywords):
                found_topics.append(topic)
        
        return found_topics
    
    def _update_favorite_topics(self, topics: list):
        """Update favorite topics list."""
        current_topics = self.preferences.get('favorite_topics', '').split(',')
        current_topics = [t.strip() for t in current_topics if t.strip()]
        
        for topic in topics:
            if topic not in current_topics:
                current_topics.append(topic)
        
        # Keep only the 5 most recent topics
        self.preferences['favorite_topics'] = ','.join(current_topics[-5:])
    
    def generate_adaptive_prompt(self, base_prompt: str) -> str:
        """
        Generate personalized system prompt based on learned preferences.
        
        Args:
            base_prompt: Original system prompt
            
        Returns:
            Adapted system prompt
        """
        formality = self.preferences['formality']
        verbosity = self.preferences['verbosity']
        humor = self.preferences['humor']
        
        # Build adaptive instructions
        adaptations = []
        
        # Formality adaptation
        if formality < 0.3:
            adaptations.append("Use casual, friendly language. Contractions are fine. Keep it relaxed.")
        elif formality > 0.7:
            adaptations.append("Maintain a professional, formal tone. Use complete sentences and proper grammar.")
        
        # Verbosity adaptation        if verbosity < 0.3:
            adaptations.append("Be extremely concise. One-sentence answers when possible.")
        elif verbosity > 0.7:
            adaptations.append("Provide detailed, comprehensive explanations. Include context and examples.")
        
        # Humor adaptation
        if humor < 0.3:
            adaptations.append("Keep responses serious and straightforward. Minimal humor.")
        elif humor > 0.7:
            adaptations.append("Feel free to be witty and add tasteful humor when appropriate.")
        
        # Combine base prompt with adaptations
        if adaptations:
            adapted_prompt = base_prompt + "\n\nUser Communication Style Preferences:\n- " + "\n- ".join(adaptations)
            return adapted_prompt
        
        return base_prompt
    
    def get_stats(self) -> Dict:
        """Get current personality adaptation statistics."""
        return {
            'interaction_count': self.interaction_count,
            'formality': round(self.preferences['formality'], 2),
            'verbosity': round(self.preferences['verbosity'], 2),
            'humor': round(self.preferences['humor'], 2),
            'favorite_topics': self.preferences.get('favorite_topics', 'none')
        }


# Future enhancements:
# - Add sentiment analysis for mood matching
# - Time-based personality (more energetic in morning)
# - Context-aware adaptation (formal for work questions, casual for personal)
# - User feedback mechanism ("too formal" → adjust immediately)

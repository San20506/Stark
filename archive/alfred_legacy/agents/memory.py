"""
ALFRED MEMORY SYSTEM
Tier 1: Contextual Persistence
Tier 6: Self-Directed Skill Expansion (Knowledge Base)
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
import time

logger = logging.getLogger("Alfred.Memory")

class MemorySystem:
    def __init__(self):
        self.base_dir = Path.home() / ".alfred"
        self.base_dir.mkdir(exist_ok=True)
        
        self.profile_path = self.base_dir / "user_profile.json"
        self.history_path = self.base_dir / "conversation_history.json"
    
        self.profile = self._load_profile()
        self.short_term: List[Dict] = []
        
        # Try loading semantic memory (Tier 1 advanced)
        self.semantic = None
        try:
            from chromadb import PersistentClient
            self.chroma = PersistentClient(path=str(self.base_dir / "chroma_db"))
            self.semantic = self.chroma.get_or_create_collection(name="long_term_memory")
            logger.info("✅ Semantic Memory (ChromaDB) initialized")
        except ImportError:
            logger.warning("⚠️ ChromaDB not installed. Semantic memory disabled.")
            
    def _load_profile(self) -> Dict:
        if self.profile_path.exists():
            try:
                return json.loads(self.profile_path.read_text())
            except:
                pass
        return {"name": "User", "preferences": {}}

    def save_profile(self):
        self.profile_path.write_text(json.dumps(self.profile, indent=2))

    def update_preference(self, key: str, value: str):
        """Store long-term user preference."""
        self.profile["preferences"][key] = value
        self.save_profile()
        logger.info(f"📝 Preference updated: {key} = {value}")

    def add_interaction(self, role: str, content: str):
        """Add to short term (RAM) and semantic (Vector) memory."""
        # 1. RAM
        entry = {"role": role, "content": content, "timestamp": time.time()}
        self.short_term.append(entry)
        
        # Keep RAM small
        if len(self.short_term) > 20:
            self.short_term.pop(0)
            
        # 2. Vector DB (Background knowledge)
        if self.semantic and role == "user": # Index user queries for retrieval
            self.semantic.add(
                documents=[content],
                metadatas=[{"timestamp": time.time(), "role": role}],
                ids=[f"{time.time()}-{role}"]
            )

    def retrieve_context(self, query: str) -> str:
        """Get relevant context for answering a query."""
        context = []
        
        # 1. Profile Context
        if self.profile["preferences"]:
            context.append(f"User Preferences: {self.profile['preferences']}")
            
        # 2. Semantic Search (if available)
        if self.semantic:
            results = self.semantic.query(query_texts=[query], n_results=2)
            if results and results['documents']:
                context.append(f"Relevant Past Info: {results['documents'][0]}")
                
        return "\n".join(context)

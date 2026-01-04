"""
ALFRED Distributed Neuromorphic Memory System v2.0
Enhanced with JARVIS-level features:

1. HOT CACHE (Redis/Dict): Sub-millisecond in-memory access
2. WARM STORAGE (SQLite): Fast episodic retrieval
3. COLD STORAGE (Parquet): Compressed long-term archival
4. VECTOR STORE (ChromaDB): Semantic similarity search

Memory Tiering:
  HOT (0-5 min) → WARM (5 min - 7 days) → COLD (7+ days)
"""

import os
import json
import time
import uuid
import sqlite3
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from collections import OrderedDict

logger = logging.getLogger("NeuromorphicMemory")

# Optional imports (graceful degradation)
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.info("Redis not available, using in-memory LRU cache")

try:
    import pyarrow as pa
    import pyarrow.parquet as pq
    import pandas as pd
    PARQUET_AVAILABLE = True
except ImportError:
    PARQUET_AVAILABLE = False
    logger.info("Parquet not available, cold storage disabled")

try:
    from memory.semantic_memory import SemanticMemory
    SEMANTIC_AVAILABLE = True
except ImportError:
    SEMANTIC_AVAILABLE = False


@dataclass
class MemoryEngram:
    """A single unit of memory (engram)."""
    id: str
    content: str
    type: str  # "episodic", "semantic", "procedural"
    timestamp: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    strength: float = 1.0  # Synaptic weight (0.0 - 10.0)
    access_count: int = 0  # Track access frequency
    last_accessed: float = 0.0  # Last access time


class LRUCache(OrderedDict):
    """Simple LRU cache for hot memory when Redis unavailable."""
    def __init__(self, maxsize=1000):
        super().__init__()
        self.maxsize = maxsize
        
    def get(self, key, default=None):
        if key in self:
            self.move_to_end(key)
            return self[key]
        return default
    
    def set(self, key, value):
        if key in self:
            self.move_to_end(key)
        self[key] = value
        if len(self) > self.maxsize:
            self.popitem(last=False)


class HotCache:
    """
    HOT MEMORY LAYER: Sub-millisecond access.
    Uses Redis if available, falls back to LRU dict.
    """
    def __init__(self, redis_url: str = "redis://localhost:6379", ttl: int = 300):
        self.ttl = ttl  # 5 minutes default
        self.redis_client = None
        self.local_cache = LRUCache(maxsize=1000)
        
        if REDIS_AVAILABLE:
            try:
                self.redis_client = redis.from_url(redis_url, decode_responses=True)
                self.redis_client.ping()
                logger.info("✅ Redis hot cache connected")
            except Exception as e:
                logger.warning(f"Redis unavailable: {e}, using local LRU cache")
                self.redis_client = None
    
    def get(self, key: str) -> Optional[str]:
        """Get from hot cache (sub-ms)."""
        if self.redis_client:
            try:
                return self.redis_client.get(f"alfred:hot:{key}")
            except:
                pass
        return self.local_cache.get(key)
    
    def set(self, key: str, value: str):
        """Set in hot cache with TTL."""
        if self.redis_client:
            try:
                self.redis_client.setex(f"alfred:hot:{key}", self.ttl, value)
                return
            except:
                pass
        self.local_cache.set(key, value)
    
    def get_recent_context(self, limit: int = 10) -> List[str]:
        """Get most recent items from cache."""
        if self.redis_client:
            try:
                keys = self.redis_client.keys("alfred:hot:msg:*")
                values = []
                for key in sorted(keys, reverse=True)[:limit]:
                    val = self.redis_client.get(key)
                    if val:
                        values.append(val)
                return values
            except:
                pass
        return list(self.local_cache.values())[-limit:]


class WarmStorage:
    """
    WARM MEMORY LAYER: SQLite for fast episodic retrieval.
    Stores recent interactions (last 7 days).
    """
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS episodes (
            id TEXT PRIMARY KEY,
            content TEXT,
            timestamp REAL,
            metadata TEXT,
            strength REAL,
            access_count INTEGER DEFAULT 0,
            last_accessed REAL
        )''')
        c.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON episodes(timestamp)')
        conn.commit()
        conn.close()
    
    def add(self, engram: MemoryEngram):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("""INSERT OR REPLACE INTO episodes 
                     (id, content, timestamp, metadata, strength, access_count, last_accessed)
                     VALUES (?, ?, ?, ?, ?, ?, ?)""",
                  (engram.id, engram.content, engram.timestamp,
                   json.dumps(engram.metadata), engram.strength,
                   engram.access_count, engram.last_accessed))
        conn.commit()
        conn.close()
    
    def get_recent(self, limit: int = 10) -> List[MemoryEngram]:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT * FROM episodes ORDER BY timestamp DESC LIMIT ?", (limit,))
        rows = c.fetchall()
        conn.close()
        return [self._row_to_engram(row) for row in rows]
    
    def get_by_timerange(self, start_ts: float, end_ts: float) -> List[MemoryEngram]:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT * FROM episodes WHERE timestamp BETWEEN ? AND ? ORDER BY timestamp",
                  (start_ts, end_ts))
        rows = c.fetchall()
        conn.close()
        return [self._row_to_engram(row) for row in rows]
    
    def get_old_records(self, days: int = 7) -> List[MemoryEngram]:
        """Get records older than N days for archival."""
        cutoff = time.time() - (days * 86400)
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT * FROM episodes WHERE timestamp < ? ORDER BY timestamp", (cutoff,))
        rows = c.fetchall()
        conn.close()
        return [self._row_to_engram(row) for row in rows]
    
    def delete_old_records(self, days: int = 7) -> int:
        """Delete records older than N days (after archival)."""
        cutoff = time.time() - (days * 86400)
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("DELETE FROM episodes WHERE timestamp < ?", (cutoff,))
        deleted = c.rowcount
        conn.commit()
        conn.close()
        return deleted
    
    def count(self) -> int:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM episodes")
        count = c.fetchone()[0]
        conn.close()
        return count
    
    def _row_to_engram(self, row) -> MemoryEngram:
        return MemoryEngram(
            id=row[0],
            content=row[1],
            type="episodic",
            timestamp=row[2],
            metadata=json.loads(row[3]),
            strength=row[4],
            access_count=row[5] if len(row) > 5 else 0,
            last_accessed=row[6] if len(row) > 6 else 0
        )


class ColdStorage:
    """
    COLD MEMORY LAYER: Parquet for compressed long-term archival.
    Stores data older than 7 days with high compression ratio.
    """
    def __init__(self, archive_dir: str):
        self.archive_dir = archive_dir
        os.makedirs(archive_dir, exist_ok=True)
        self.available = PARQUET_AVAILABLE
    
    def archive_batch(self, engrams: List[MemoryEngram]) -> str:
        """Archive a batch of engrams to Parquet file."""
        if not self.available or not engrams:
            return None
        
        # Convert to DataFrame
        data = []
        for e in engrams:
            data.append({
                'id': e.id,
                'content': e.content,
                'timestamp': e.timestamp,
                'metadata': json.dumps(e.metadata),
                'strength': e.strength,
                'access_count': e.access_count
            })
        
        df = pd.DataFrame(data)
        
        # Generate filename with date range
        min_ts = min(e.timestamp for e in engrams)
        max_ts = max(e.timestamp for e in engrams)
        start_date = datetime.fromtimestamp(min_ts).strftime('%Y%m%d')
        end_date = datetime.fromtimestamp(max_ts).strftime('%Y%m%d')
        
        filename = f"archive_{start_date}_to_{end_date}_{int(time.time())}.parquet"
        filepath = os.path.join(self.archive_dir, filename)
        
        # Write with compression
        table = pa.Table.from_pandas(df)
        pq.write_table(table, filepath, compression='snappy')
        
        logger.info(f"📦 Archived {len(engrams)} records to {filename}")
        return filepath
    
    def search_archives(self, query: str, limit: int = 10) -> List[Dict]:
        """Search through archived Parquet files."""
        if not self.available:
            return []
        
        results = []
        query_lower = query.lower()
        
        for filename in os.listdir(self.archive_dir):
            if filename.endswith('.parquet'):
                filepath = os.path.join(self.archive_dir, filename)
                df = pq.read_table(filepath).to_pandas()
                
                # Simple text search (semantic search would be better)
                matches = df[df['content'].str.lower().str.contains(query_lower, na=False)]
                for _, row in matches.head(limit).iterrows():
                    results.append({
                        'content': row['content'],
                        'timestamp': row['timestamp'],
                        'source': filename
                    })
                
                if len(results) >= limit:
                    break
        
        return results[:limit]
    
    def list_archives(self) -> List[Dict]:
        """List all archive files with metadata."""
        archives = []
        for filename in os.listdir(self.archive_dir):
            if filename.endswith('.parquet'):
                filepath = os.path.join(self.archive_dir, filename)
                size = os.path.getsize(filepath)
                archives.append({
                    'filename': filename,
                    'size_kb': size / 1024,
                    'path': filepath
                })
        return archives


class ProceduralMemory:
    """Procedural memory for learned skills and workflows."""
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.skills = {}
        self.load()
    
    def load(self):
        if os.path.exists(self.file_path):
            with open(self.file_path, 'r') as f:
                self.skills = json.load(f)
    
    def save(self):
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
        with open(self.file_path, 'w') as f:
            json.dump(self.skills, f, indent=2)
    
    def add_skill(self, name: str, steps: List[str]):
        self.skills[name] = {'steps': steps, 'created': time.time()}
        self.save()
    
    def get_skill(self, name: str) -> Optional[Dict]:
        return self.skills.get(name)


class NeuromorphicMemoryV2:
    """
    Enhanced Neuromorphic Memory with 3-tier architecture.
    
    HOT (Redis/LRU) → WARM (SQLite) → COLD (Parquet)
    
    Features:
    - Sub-ms hot cache for recent context
    - Fast warm storage for episodic memory
    - Compressed cold storage for archival
    - Automatic tiering based on age/access
    """
    
    def __init__(self, data_dir: str = None):
        if data_dir is None:
            data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "memory")
        
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
        
        # Initialize memory tiers
        self.hot = HotCache()
        self.warm = WarmStorage(os.path.join(data_dir, "episodic.db"))
        self.cold = ColdStorage(os.path.join(data_dir, "archives"))
        self.procedural = ProceduralMemory(os.path.join(data_dir, "procedural.json"))
        
        # Semantic memory (vector store)
        self.semantic = None
        self.semantic_available = False
        if SEMANTIC_AVAILABLE:
            try:
                self.semantic = SemanticMemory(persist_directory=os.path.join(data_dir, "semantic_chroma"))
                self.semantic_available = True
            except Exception as e:
                logger.warning(f"Semantic memory unavailable: {e}")
        
        logger.info(f"🧠 NeuromorphicMemory v2.0 initialized")
        logger.info(f"   HOT:  {'Redis' if self.hot.redis_client else 'LRU Cache'}")
        logger.info(f"   WARM: SQLite ({self.warm.count()} records)")
        logger.info(f"   COLD: Parquet ({'enabled' if self.cold.available else 'disabled'})")
        logger.info(f"   VECTOR: {'ChromaDB' if self.semantic_available else 'disabled'}")
    
    def store_interaction(self, user_query: str, ai_response: str, metadata: Dict = None):
        """Store interaction across all memory tiers."""
        timestamp = time.time()
        msg_id = str(uuid.uuid4())
        
        # Create engrams
        user_engram = MemoryEngram(
            id=f"user_{msg_id}",
            content=user_query,
            type="episodic",
            timestamp=timestamp,
            metadata={"role": "user", **(metadata or {})},
            last_accessed=timestamp
        )
        
        ai_engram = MemoryEngram(
            id=f"ai_{msg_id}",
            content=ai_response,
            type="episodic",
            timestamp=timestamp,
            metadata={"role": "assistant", **(metadata or {})},
            last_accessed=timestamp
        )
        
        # 1. HOT: Immediate cache
        self.hot.set(f"msg:{timestamp}:user", user_query)
        self.hot.set(f"msg:{timestamp}:ai", ai_response)
        
        # 2. WARM: Episodic storage
        self.warm.add(user_engram)
        self.warm.add(ai_engram)
        
        # 3. VECTOR: Semantic indexing
        if self.semantic_available:
            self.semantic.add_exchange(user_query, ai_response, metadata)
    
    def recall(self, query: str, top_k: int = 3) -> Dict[str, Any]:
        """Unified recall across all memory tiers."""
        results = {
            "hot_context": self.hot.get_recent_context(5),
            "warm_recent": [e.content for e in self.warm.get_recent(3)],
            "semantic_related": [],
            "cold_matches": []
        }
        
        # Semantic search
        if self.semantic_available:
            results["semantic_related"] = self.semantic.search_similar(query, top_k=top_k)
        
        # Cold archive search (if query seems historical)
        if any(word in query.lower() for word in ['history', 'archive', 'old', 'past', 'remember when']):
            results["cold_matches"] = self.cold.search_archives(query, limit=3)
        
        return results
    
    def consolidate(self) -> Dict[str, int]:
        """
        Run memory consolidation process.
        Moves old data from WARM → COLD storage.
        """
        stats = {"archived": 0, "deleted": 0}
        
        # Get records older than 7 days
        old_records = self.warm.get_old_records(days=7)
        
        if old_records and self.cold.available:
            # Archive to Parquet
            self.cold.archive_batch(old_records)
            stats["archived"] = len(old_records)
            
            # Delete from warm storage
            deleted = self.warm.delete_old_records(days=7)
            stats["deleted"] = deleted
            
            logger.info(f"🔄 Consolidation: {stats['archived']} archived, {stats['deleted']} removed from warm")
        
        return stats
    
    def get_stats(self) -> Dict:
        """Get memory system statistics."""
        return {
            "hot_type": "Redis" if self.hot.redis_client else "LRU",
            "warm_count": self.warm.count(),
            "cold_archives": len(self.cold.list_archives()),
            "cold_available": self.cold.available,
            "semantic_available": self.semantic_available,
            "procedural_skills": len(self.procedural.skills),
            "data_dir": self.data_dir
        }


# Singleton
_memory_v2 = None

def get_neuromorphic_memory() -> NeuromorphicMemoryV2:
    """Get or create singleton memory instance."""
    global _memory_v2
    if _memory_v2 is None:
        _memory_v2 = NeuromorphicMemoryV2()
    return _memory_v2


# Backward compatibility alias
NeuromorphicMemory = NeuromorphicMemoryV2

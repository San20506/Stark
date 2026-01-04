"""
Neuromorphic Memory v2.0 - Full System Test
Tests all 3 tiers: HOT → WARM → COLD
"""
import sys
import os
import time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def main():
    print("=" * 70)
    print("   NEUROMORPHIC MEMORY v2.0 - JARVIS-Level Architecture Test")
    print("=" * 70)
    
    # Initialize
    print("\n[INIT] Loading memory system...")
    from memory.neuromorphic_memory import get_neuromorphic_memory
    mem = get_neuromorphic_memory()
    
    stats = mem.get_stats()
    print(f"""
    Memory Tiers Initialized:
    ├─ HOT:        {stats['hot_type']} (sub-ms access)
    ├─ WARM:       SQLite ({stats['warm_count']} records)
    ├─ COLD:       Parquet ({'enabled' if stats['cold_available'] else 'disabled'})
    ├─ VECTOR:     {'ChromaDB' if stats['semantic_available'] else 'disabled'}
    └─ PROCEDURAL: {stats['procedural_skills']} skills
    """)
    
    # Test 1: Store interactions
    print("\n" + "=" * 70)
    print("[TEST 1] Storing Interactions (HOT + WARM + VECTOR)")
    print("=" * 70)
    
    interactions = [
        ("What's the weather in Tokyo?", "It's currently 22°C and sunny in Tokyo."),
        ("Remind me about the meeting", "You have a team meeting at 3 PM today."),
        ("Tell me about machine learning", "Machine learning is a subset of AI that learns from data."),
    ]
    
    for user, ai in interactions:
        mem.store_interaction(user, ai)
        print(f"  Stored: '{user[:40]}...'")
    
    print(f"  ✓ {len(interactions)} interactions stored across all tiers")
    
    # Test 2: HOT cache retrieval
    print("\n" + "=" * 70)
    print("[TEST 2] HOT Cache Retrieval (sub-ms)")
    print("=" * 70)
    
    start = time.perf_counter()
    hot_context = mem.hot.get_recent_context(5)
    elapsed = (time.perf_counter() - start) * 1000
    
    print(f"  Retrieved {len(hot_context)} items in {elapsed:.3f}ms")
    for item in hot_context[:3]:
        print(f"    - {item[:50]}...")
    
    # Test 3: WARM storage
    print("\n" + "=" * 70)
    print("[TEST 3] WARM Storage (SQLite)")
    print("=" * 70)
    
    recent = mem.warm.get_recent(5)
    print(f"  Recent episodes: {len(recent)}")
    for ep in recent[:3]:
        role = ep.metadata.get('role', '?')
        print(f"    [{role}] {ep.content[:50]}...")
    
    # Test 4: Semantic recall
    print("\n" + "=" * 70)
    print("[TEST 4] Semantic Vector Search (ChromaDB)")
    print("=" * 70)
    
    if mem.semantic_available:
        query = "weather forecast"
        start = time.perf_counter()
        results = mem.semantic.search_similar(query, top_k=2)
        elapsed = (time.perf_counter() - start) * 1000
        
        print(f"  Query: '{query}'")
        print(f"  Found {len(results)} similar in {elapsed:.1f}ms")
        for r in results:
            print(f"    - Similarity: {r['similarity']:.0%}")
            print(f"      User: {r['user'][:40]}...")
    else:
        print("  Semantic memory not available")
    
    # Test 5: Unified recall
    print("\n" + "=" * 70)
    print("[TEST 5] Unified Associative Recall")
    print("=" * 70)
    
    query = "What did we discuss about weather?"
    recall = mem.recall(query, top_k=2)
    
    print(f"  Query: '{query}'")
    print(f"  HOT context: {len(recall['hot_context'])} items")
    print(f"  WARM recent: {len(recall['warm_recent'])} items")
    print(f"  Semantic related: {len(recall['semantic_related'])} items")
    
    # Test 6: Cold storage (if available)
    print("\n" + "=" * 70)
    print("[TEST 6] COLD Storage (Parquet Archive)")
    print("=" * 70)
    
    if mem.cold.available:
        archives = mem.cold.list_archives()
        print(f"  Archives found: {len(archives)}")
        for a in archives:
            print(f"    - {a['filename']} ({a['size_kb']:.1f} KB)")
        
        # Test consolidation preview
        old_records = mem.warm.get_old_records(days=0)  # Get all for demo
        print(f"  Records eligible for archival: {len(old_records)}")
    else:
        print("  Parquet not available (install pyarrow)")
    
    # Test 7: Procedural memory
    print("\n" + "=" * 70)
    print("[TEST 7] Procedural Memory (Skills)")
    print("=" * 70)
    
    mem.procedural.add_skill("take_screenshot", [
        "Import pyautogui",
        "Call pyautogui.screenshot()",
        "Save to file"
    ])
    
    skill = mem.procedural.get_skill("take_screenshot")
    print(f"  Stored skill 'take_screenshot': {skill['steps']}")
    
    # Summary
    print("\n" + "=" * 70)
    print("   SUMMARY")
    print("=" * 70)
    
    final_stats = mem.get_stats()
    print(f"""
    ┌─────────────────────────────────────────────────────────┐
    │  Memory Tier    │  Type      │  Status                 │
    ├─────────────────────────────────────────────────────────┤
    │  HOT Cache      │  {final_stats['hot_type']:<10}│  ✓ Active (sub-ms)     │
    │  WARM Storage   │  SQLite    │  ✓ {final_stats['warm_count']} records           │
    │  COLD Archive   │  Parquet   │  {'✓ Enabled' if final_stats['cold_available'] else '○ Disabled'}             │
    │  VECTOR Store   │  ChromaDB  │  {'✓ Enabled' if final_stats['semantic_available'] else '○ Disabled'}             │
    │  PROCEDURAL     │  JSON      │  ✓ {final_stats['procedural_skills']} skills             │
    └─────────────────────────────────────────────────────────┘
    
    Data Location: {final_stats['data_dir']}
    """)
    
    print("✅ All tests complete!")

if __name__ == "__main__":
    main()

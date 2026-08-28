import json
from pathlib import Path

ep_path = Path(r"D:\Eris_Source\memory\episodic.json")
if ep_path.exists():
    episodes = json.loads(ep_path.read_text(encoding="utf-8"))
    print(f"Episodios totales: {len(episodes)}")
    print()

    # Show last 5 episodes
    print("=== ULTIMOS 5 EPISODIOS ===")
    for ep in episodes[-5:]:
        learning = ep.get("learning", "")
        event = ep.get("event", "")
        emotion = ep.get("emotion", "?")
        ts = ep.get("timestamp", "?")
        print(f"  Emotion: {emotion}")
        print(f"  Learning: '{learning[:100]}' ({len(learning)} chars)")
        print(f"  Event: '{event[:100]}' ({len(event)} chars)")
        print(f"  Timestamp: {ts}")
        print()

    # Count how many have real learning
    with_learning = sum(1 for ep in episodes if ep.get("learning") and len(ep.get("learning", "")) > 10)
    print(f"Con learning real (>10 chars): {with_learning}/{len(episodes)}")
else:
    print("episodic.json not found")

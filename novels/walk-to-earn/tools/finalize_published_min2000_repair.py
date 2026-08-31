#!/usr/bin/env python3
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[3]
NOVEL = ROOT / "novels" / "walk-to-earn"
CHAPTERS = NOVEL / "chapters"

TARGETS = [3,4,5,7,8,9,10,11,12,13,14,15,16,17,18,21,22,23,24,25,31,34,38,42,43]
MARKER_RE = re.compile(r"\n?<!--\s*min2000-repair-[^>]*-->\n?")

for n in TARGETS:
    path = CHAPTERS / f"chapter-{n:03d}.md"
    text = path.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")
    cleaned = MARKER_RE.sub("\n", text)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).rstrip() + "\n"
    path.write_text(cleaned, encoding="utf-8")

plan = NOVEL / "audits" / "published-min2000-repair-plan.md"
plan.write_text("""# Published Chapter Minimum-Length Repair Audit

Scope: published chapters 1-43 that were below the 2000 non-whitespace body-character floor.

Repaired chapters: 3, 4, 5, 7-18, 21-25, 31, 34, 38, 42, 43.

Rules applied:
- preserve chapter number and title;
- preserve established continuity facts, dates, mileage, step-income numbers, relationships, and later-chapter dependencies;
- add substantive scene work, actions, environmental detail, and character-specific dialogue instead of padding or summary repetition;
- every repaired chapter must remain >=2000 body characters after whitespace removal;
- no upper length cap; scenes may exceed 3000 or 4000 characters when needed;
- platform synchronization is not authorized by this audit alone and remains separately gated.

Status: prose repairs staged on audit branch; awaiting full Dialogue / Humanizer / Prose / Meta PR review before merge or platform update.
""", encoding="utf-8")

print("repair markers removed; audit plan refreshed; marker-free floor will be rechecked")

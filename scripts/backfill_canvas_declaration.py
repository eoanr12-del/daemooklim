"""Backfill [CANVAS]/[캔버스] declaration into all existing prompts.json thumbnails."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "channels"

KO_LINE = "[캔버스] 16:9 비율, 1280x720 픽셀 정확히. 가로형 유튜브 썸네일 규격."
EN_LINE = "[CANVAS] 16:9 aspect ratio, exactly 1280x720 pixels, horizontal YouTube thumbnail format."

KO_MARKERS = ("[캔버스]",)
EN_MARKERS = ("[CANVAS]",)


def has_marker(text: str, markers) -> bool:
    if not isinstance(text, str):
        return False
    return any(m in text for m in markers)


def prepend(text: str, line: str) -> str:
    text = (text or "").lstrip()
    return f"{line} {text}".rstrip()


def process_file(path: Path) -> tuple[bool, int, int]:
    """Returns (changed, ko_added, en_added)."""
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    thumbs = data.get("thumbnails", [])
    if not thumbs:
        return False, 0, 0

    ko_added = 0
    en_added = 0
    for t in thumbs:
        if "concept_ko" in t and not has_marker(t["concept_ko"], KO_MARKERS):
            t["concept_ko"] = prepend(t["concept_ko"], KO_LINE)
            ko_added += 1
        if "prompt_en" in t and not has_marker(t["prompt_en"], EN_MARKERS):
            t["prompt_en"] = prepend(t["prompt_en"], EN_LINE)
            en_added += 1

    if ko_added == 0 and en_added == 0:
        return False, 0, 0

    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
    return True, ko_added, en_added


def main():
    files = sorted(ROOT.glob("*/projects/*/output/thumbnails/prompts.json"))
    if not files:
        print("No prompts.json files found.")
        return

    total_changed = 0
    total_ko = 0
    total_en = 0
    skipped = []
    for path in files:
        rel = path.relative_to(ROOT)
        try:
            changed, ko, en = process_file(path)
        except Exception as e:
            print(f"  ! ERROR {rel}: {e}")
            continue
        if changed:
            total_changed += 1
            total_ko += ko
            total_en += en
            print(f"  + {rel}  (ko+{ko}, en+{en})")
        else:
            skipped.append(rel)

    print()
    print(f"Updated: {total_changed} files | concept_ko +{total_ko}, prompt_en +{total_en}")
    print(f"Skipped (already had marker): {len(skipped)}")
    for s in skipped:
        print(f"  - {s}")


if __name__ == "__main__":
    main()

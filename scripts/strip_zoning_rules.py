"""Strip upper/lower zoning rules from all existing prompts.json files.

Removes:
1. Whole bracket sections: [구도], [COMPOSITION], [LAYOUT], [레이아웃]
2. Sentences containing zoning phrases (Korean and English)

Preserves:
- [캔버스]/[CANVAS] declarations
- All other content
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "channels"

# Bracket sections to remove entirely
BRACKET_HEADERS = ["[구도]", "[COMPOSITION]", "[LAYOUT]", "[레이아웃]"]

# Phrases that, when found in a sentence, mark the whole sentence for removal
KO_PHRASES = [
    "상단 2/3", "상단 1/2", "상단 절반",
    "하단 2/3", "하단 1/3", "하단 1/2", "하단 절반",
    "자막 영역", "자막 자리", "자막 후편집", "자막을 후편집",
    "후편집으로 얹", "후편집에서 자유롭게",
    "텍스트 자리", "텍스트 공간", "텍스트는 후편집",
    "대략 1280x480", "대략 1280x240",
    "어두운 배경(텍스트", "비어있는 어두운 배경",
    "placeholder 텍스트", "어깨선·옷의 톤",
    # Round 2 — zoning remnants
    "상단 이미지는 경계선",
    "경계선에서 잘리지 않도록",
    "강제로 비워두는",
    "끊김 없이 채워져야",
    "화면 하단으로",
    "화면 아래로 자연",
    "차분한 베이스",
]

EN_PHRASES = [
    "upper two-thirds", "upper two thirds", "top two-thirds",
    "bottom one-third", "bottom one third", "lower one-third",
    "upper half", "lower half", "bottom half",
    "subtitle zone", "subtitle area",
    "reserved for text", "reserved for subtitles",
    "added later in post-production", "added later by the user",
    "post-production by the user",
    "the bottom dark area", "bottom dark area",
    "empty for post-production",
    "negative space",
    # Round 2 — zoning remnants
    "no forcibly empty",
    "lower portion of the frame",
    "natural visual extension",
    "calm tonal base",
    "as one continuous natural image",
    "extends naturally into the lower",
    "fades naturally downward",
    "must be filled as one continuous",
    "entire canvas must be filled",
]


def strip_bracket_sections(text: str) -> str:
    """Remove [HEADER]...up to next [bracket] or end."""
    for header in BRACKET_HEADERS:
        # Match header through (lazy) any chars up to next [ or end of string
        pattern = re.escape(header) + r"[^\[]*"
        text = re.sub(pattern, "", text)
    return text


def split_sentences_ko(text: str) -> list[str]:
    """Split Korean text on sentence boundaries (period/exclaim/question + space or end)."""
    parts = re.split(r"(?<=[\.!?])\s+", text)
    return [p for p in parts if p]


def split_sentences_en(text: str) -> list[str]:
    return re.split(r"(?<=[\.!?])\s+", text)


def strip_phrase_sentences(text: str, phrases: list[str]) -> str:
    """Remove sentences containing any of the target phrases (case-insensitive)."""
    if not text:
        return text
    sentences = re.split(r"(?<=[\.!?])\s+", text)
    lower_phrases = [p.lower() for p in phrases]
    kept = []
    for s in sentences:
        s_lower = s.lower()
        if any(p in s_lower for p in lower_phrases):
            continue
        kept.append(s)
    return " ".join(kept)


def cleanup_whitespace(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    # Remove orphan periods/spaces at start
    text = re.sub(r"^[\.\s]+", "", text)
    return text


def clean_concept_ko(text: str) -> tuple[str, int]:
    if not isinstance(text, str):
        return text, 0
    before = text
    text = strip_bracket_sections(text)
    text = strip_phrase_sentences(text, KO_PHRASES)
    text = cleanup_whitespace(text)
    return text, 0 if text == before else 1


def clean_prompt_en(text: str) -> tuple[str, int]:
    if not isinstance(text, str):
        return text, 0
    before = text
    text = strip_bracket_sections(text)
    text = strip_phrase_sentences(text, EN_PHRASES)
    text = cleanup_whitespace(text)
    return text, 0 if text == before else 1


def process_file(path: Path) -> tuple[bool, int, int]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    thumbs = data.get("thumbnails", [])
    if not thumbs:
        return False, 0, 0
    ko_changed = en_changed = 0
    for t in thumbs:
        if "concept_ko" in t:
            new_text, c = clean_concept_ko(t["concept_ko"])
            if c:
                t["concept_ko"] = new_text
                ko_changed += 1
        if "prompt_en" in t:
            new_text, c = clean_prompt_en(t["prompt_en"])
            if c:
                t["prompt_en"] = new_text
                en_changed += 1
    if ko_changed == 0 and en_changed == 0:
        return False, 0, 0
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
    return True, ko_changed, en_changed


def main():
    files = sorted(ROOT.glob("*/projects/*/output/thumbnails/prompts.json"))
    if not files:
        print("No prompts.json files found.")
        return
    total_files = 0
    total_ko = 0
    total_en = 0
    skipped = 0
    for path in files:
        rel = path.relative_to(ROOT)
        try:
            changed, ko, en = process_file(path)
        except Exception as e:
            print(f"  ! ERROR {rel}: {e}")
            continue
        if changed:
            total_files += 1
            total_ko += ko
            total_en += en
            print(f"  + {rel}  (ko-{ko}, en-{en})")
        else:
            skipped += 1
    print()
    print(f"Updated: {total_files} files | concept_ko -{total_ko}, prompt_en -{total_en}")
    print(f"Skipped (no zoning text found): {skipped}")


if __name__ == "__main__":
    main()

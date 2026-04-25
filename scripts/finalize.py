"""draft.md → script.txt 변환 + output/ 산출물 배치

1. draft.md에서 마크다운 메타(헤더, 구분선, 주석, 블록인용, 볼드 마커)를
   제거하고 순수 대본 텍스트만 한 줄로 이어붙여 _script/script.txt 생성
2. script.txt를 output/script.txt 로 복사
3. output/youtube.md 템플릿 생성 (없을 때만 — concept.md 기반)
"""

import argparse
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
from project_resolver import resolve_project_dir


_ANY_HEADER_RE = re.compile(r"^#{1,6}\s+")  # h1~h6 → script.txt에서 제외
_HTML_COMMENT_RE = re.compile(r"<!--.*?-->", flags=re.DOTALL)
_HR_RE = re.compile(r"^-{3,}$")
_BLOCKQUOTE_RE = re.compile(r"^>.*$")


def convert(draft_path: Path) -> str:
    """draft.md를 파싱하여 순수 대본 텍스트를 반환."""
    raw = draft_path.read_text(encoding="utf-8")

    # HTML 주석 제거
    raw = _HTML_COMMENT_RE.sub("", raw)

    body_lines: list[str] = []

    for line in raw.splitlines():
        # 구분선 제거
        if _HR_RE.match(line.strip()):
            continue
        # 블록인용 제거
        if _BLOCKQUOTE_RE.match(line.strip()):
            continue

        # 모든 헤더(#~######) → script.txt에서 제외
        if _ANY_HEADER_RE.match(line.strip()):
            continue

        # 빈 줄이 아닌 본문만 수집
        stripped = line.strip()
        if stripped:
            # 볼드 마커 제거 (TTS가 별표를 읽지 않도록)
            stripped = stripped.replace("**", "")
            body_lines.append(stripped)

    script_text = " ".join(body_lines)

    return script_text


def _extract_section(raw: str, name: str) -> str:
    """concept.md에서 '## {name}' 섹션 본문 추출."""
    pattern = rf"^##\s*{re.escape(name)}\s*\n(.*?)(?=^##\s|\Z)"
    m = re.search(pattern, raw, re.MULTILINE | re.DOTALL)
    return m.group(1).strip() if m else ""


def _extract_numbered(section: str) -> list[str]:
    """섹션 본문에서 '1. ...' 번호 리스트 항목만 추출."""
    return re.findall(r"^\s*\d+\.\s*(.+?)\s*$", section, re.MULTILINE)


def parse_concept(concept_path: Path) -> dict:
    """concept.md에서 제목·썸네일 텍스트 후보 추출."""
    if not concept_path.exists():
        return {}
    raw = concept_path.read_text(encoding="utf-8")
    return {
        "confirmed_title": _extract_section(raw, "확정 제목").splitlines()[0].strip() if _extract_section(raw, "확정 제목") else "",
        "title_candidates": _extract_numbered(_extract_section(raw, "제목 후보")),
        "thumbnail_texts": _extract_numbered(_extract_section(raw, "썸네일 텍스트 후보")),
    }


def write_youtube_template(output_dir: Path, concept: dict) -> bool:
    """output/youtube.md 템플릿 생성. 이미 존재하면 덮어쓰지 않는다."""
    dst = output_dir / "youtube.md"
    if dst.exists():
        return False

    title = concept.get("confirmed_title") or "(concept.md 확정 제목 미입력)"
    titles = concept.get("title_candidates") or []
    thumbs = concept.get("thumbnail_texts") or []

    titles_md = "\n".join(f"{i+1}. {t}" for i, t in enumerate(titles)) or "1. (concept.md 제목 후보 미발견)"
    thumbs_md = "\n".join(f"{i+1}. {t}" for i, t in enumerate(thumbs)) or "1. (concept.md 썸네일 텍스트 미발견)"

    content = (
        "# YouTube 업로드 정보\n\n"
        "## 제목\n"
        f"{title}\n\n"
        "## 제목 후보\n"
        f"{titles_md}\n\n"
        "## 설명\n"
        "<!-- TODO: 해시태그 + 본문 설명 + 타임스탬프 + 채널 소개 작성 -->\n\n"
        "## 썸네일 텍스트 후보\n"
        f"{thumbs_md}\n\n"
        "## 고정댓글\n"
        "<!-- TODO: 고정댓글 작성 -->\n\n"
        "## 태그\n"
        "<!-- TODO: 콤마 구분 태그 작성 -->\n"
    )
    dst.write_text(content, encoding="utf-8")
    return True


def main():
    parser = argparse.ArgumentParser(description="draft.md → script.txt + output 배치")
    parser.add_argument("--project", required=True, help="프로젝트 폴더명")
    parser.add_argument("--channel", default=None, help="채널명 (미지정시 자동 탐색)")
    args = parser.parse_args()

    base = resolve_project_dir(args.project, args.channel)
    script_dir = base / "_script"
    script_dir.mkdir(parents=True, exist_ok=True)
    draft = script_dir / "draft.md"

    if not draft.exists():
        print(f"draft.md가 없습니다: {draft}")
        return

    script_text = convert(draft)

    # 1. _script/script.txt 저장
    script_out = script_dir / "script.txt"
    script_out.write_text(script_text, encoding="utf-8")
    char_count = len(script_text)
    print(f"script.txt 생성 완료 ({char_count}자, ~{char_count // 500}분)")

    # 2. output/script.txt 복사
    output_dir = base / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(script_out, output_dir / "script.txt")
    print(f"output/script.txt 복사 완료")

    # 3. output/youtube.md 템플릿 생성 (없을 때만)
    concept = parse_concept(script_dir / "concept.md")
    if write_youtube_template(output_dir, concept):
        print("output/youtube.md 템플릿 생성 완료 (설명/고정댓글/태그 TODO)")
    else:
        print("output/youtube.md 이미 존재 - 건너뜀")


if __name__ == "__main__":
    main()

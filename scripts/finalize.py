"""draft.md → script.txt 변환

마크다운 메타(헤더, 구분선, 주석, 블록인용 마커)를 제거하고
순수 대본 텍스트만 한 줄로 이어붙인다.
"""

import argparse
import re
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
            body_lines.append(stripped)

    script_text = " ".join(body_lines)

    return script_text


def main():
    parser = argparse.ArgumentParser(description="draft.md → script.txt")
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

    # script.txt 저장
    out = script_dir / "script.txt"
    out.write_text(script_text, encoding="utf-8")
    char_count = len(script_text)
    print(f"script.txt 생성 완료 ({char_count}자, ~{char_count // 500}분)")


if __name__ == "__main__":
    main()

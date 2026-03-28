"""프로젝트 디렉토리 해석 모듈.

모든 Python 스크립트가 공유하는 프로젝트 경로 해석 함수.

해석 우선순위:
1. --channel 명시 → ROOT/channels/{channel}/projects/{project}
2. 미명시 → channels/*/projects/ 전체 스캔하여 매칭
3. 폴백 → 레거시 ROOT/projects/{project}
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def resolve_project_dir(project: str, channel: str | None = None) -> Path:
    """프로젝트 디렉토리 경로를 해석한다.

    Args:
        project: 프로젝트 폴더명
        channel: 채널명 (None이면 자동 스캔)

    Returns:
        프로젝트 디렉토리 Path

    Raises:
        FileNotFoundError: 프로젝트를 찾을 수 없을 때
    """
    # 1. 채널 명시
    if channel:
        return ROOT / "channels" / channel / "projects" / project

    # 2. channels/*/projects/ 스캔
    channels_dir = ROOT / "channels"
    if channels_dir.exists():
        matches = list(channels_dir.glob(f"*/projects/{project}"))
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            channels = [m.parent.parent.name for m in matches]
            raise FileNotFoundError(
                f"프로젝트 '{project}'가 여러 채널에 존재합니다: {channels}. "
                f"--channel로 채널을 명시하세요."
            )

    # 3. 레거시 폴백
    legacy = ROOT / "projects" / project
    if legacy.exists():
        return legacy

    raise FileNotFoundError(
        f"프로젝트 '{project}'를 찾을 수 없습니다. "
        f"channels/*/projects/ 및 projects/ 모두 확인했습니다."
    )

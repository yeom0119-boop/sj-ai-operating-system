"""
SJ AI Operating System
modules/obsidian.py

역할
- Obsidian Vault 안에 종목별 Markdown 파일을 생성한다.
- 기존 종목 파일이 있으면 새로운 분석 기록을 이어서 추가한다.
- 저장된 종목 노트를 읽고 목록을 조회한다.

TODO
- 날짜별 분석 검색 기능
- AI 분석 결과 자동 저장
"""

from datetime import datetime
from pathlib import Path

# Windows에서 파일 이름에 사용할 수 없는 문자
_INVALID_FILENAME_CHARS = '<>:"/\\|?*'


def _get_stocks_folder() -> Path:
    """vault/Stocks 폴더 경로를 반환한다."""
    project_root = Path(__file__).resolve().parent.parent
    return project_root / "vault" / "Stocks"


def sanitize_stock_name(stock: str) -> str:
    """
    종목명을 파일 이름으로 안전하게 사용할 수 있도록 정리한다.

    입력:
        stock: 원본 종목명 또는 티커

    출력:
        정리된 종목명

    예외:
        ValueError: 정리 후 이름이 비어 있을 때
    """

    cleaned = stock.strip()

    # 영문 티커는 대문자로 통일한다.
    cleaned = cleaned.upper()

    for char in _INVALID_FILENAME_CHARS:
        cleaned = cleaned.replace(char, "")

    cleaned = cleaned.strip()

    if not cleaned:
        raise ValueError("종목명이 비어 있거나 파일 이름으로 사용할 수 없습니다.")

    return cleaned


def list_stock_notes() -> list[str]:
    """
    저장된 모든 종목 Markdown 노트 이름을 반환한다.

    출력:
        .md 확장자를 제외한 종목명 목록 (알파벳 순)
    """

    stocks_folder = _get_stocks_folder()

    if not stocks_folder.exists():
        return []

    names = [
        path.stem
        for path in stocks_folder.glob("*.md")
        if path.is_file()
    ]

    return sorted(names)


def read_stock_note(stock: str) -> str:
    """
    종목 Markdown 노트 전체 내용을 읽는다.

    입력:
        stock: 종목명 또는 티커

    출력:
        노트가 있으면 전체 UTF-8 Markdown 텍스트, 없으면 빈 문자열
    """

    clean_stock = sanitize_stock_name(stock)
    file_path = _get_stocks_folder() / f"{clean_stock}.md"

    if not file_path.exists():
        return ""

    return file_path.read_text(encoding="utf-8")


def save_stock_note(stock: str, content: str) -> tuple[Path, str]:
    """
    종목 분석 내용을 Markdown 파일에 저장한다.

    입력:
        stock: 종목명 또는 티커
        content: 저장할 분석 내용

    출력:
        생성 또는 수정된 파일 경로
        작업 결과(create 또는 append)
    """

    stocks_folder = _get_stocks_folder()

    # 저장 폴더가 없으면 자동 생성한다.
    stocks_folder.mkdir(parents=True, exist_ok=True)

    clean_stock = sanitize_stock_name(stock)
    file_path = stocks_folder / f"{clean_stock}.md"
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    new_entry = f"""
---

## 분석 기록 — {created_at}

{content}
"""

    if file_path.exists():
        # 과거 기록을 보존하고 새로운 분석만 파일 아래에 추가한다.
        with file_path.open("a", encoding="utf-8") as file:
            file.write(new_entry)

        return file_path, "append"

    markdown = f"""# {clean_stock}

## 기본 정보

- 종목: {clean_stock}
- 최초 작성 시간: {created_at}
- 프로젝트: SJ AI Operating System

## 분석 기록 — {created_at}

{content}
"""

    file_path.write_text(markdown, encoding="utf-8")

    return file_path, "create"

"""
SJ AI Operating System
main.py

프로젝트의 시작점

역할
- 사용자에게 종목과 분석 내용을 입력받는다.
- 종목별 Markdown 노트를 생성하거나 기존 노트에 기록을 추가한다.
- 저장된 종목 노트를 읽고 목록을 조회한다.

TODO
- 여러 줄 분석 입력
- 종목 노트 검색 기능
- AI 자동 분석 연결
"""

import sys

from modules.obsidian import list_stock_notes, read_stock_note, save_stock_note


def _configure_stdout() -> None:
    """Windows 콘솔에서 UTF-8 Markdown 출력을 지원한다."""

    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except (AttributeError, OSError, ValueError):
            pass


def print_menu() -> None:
    """반복 메뉴를 출력한다."""

    print()
    print("메뉴를 선택하세요:")
    print("  1. Save stock analysis")
    print("  2. Read existing stock note")
    print("  3. List saved stock notes")
    print("  4. Exit")
    print()


def handle_save_analysis() -> None:
    """종목 분석을 새로 저장하거나 기존 노트에 추가한다."""

    stock = input("저장할 종목명을 입력하세요: ").strip()
    content = input("분석 내용을 입력하세요: ").strip()

    if not content:
        print("오류: 분석 내용을 입력해야 합니다.")
        return

    try:
        saved_path, action = save_stock_note(stock, content)
    except ValueError as error:
        print(f"오류: {error}")
        return

    print()

    if action == "create":
        print("새 Markdown 노트 생성 완료!")
    else:
        print("기존 Markdown 노트에 분석 기록 추가 완료!")

    print(f"저장 위치: {saved_path}")


def handle_read_note() -> None:
    """저장된 종목 Markdown 노트를 출력한다."""

    stock = input("조회할 종목명을 입력하세요: ").strip()

    try:
        note_text = read_stock_note(stock)
    except ValueError as error:
        print(f"오류: {error}")
        return

    print()

    if not note_text:
        print("해당 종목의 저장된 노트가 없습니다.")
        return

    print(note_text)


def handle_list_notes() -> None:
    """저장된 모든 종목 이름을 출력한다."""

    notes = list_stock_notes()

    print()

    if not notes:
        print("저장된 종목 노트가 없습니다.")
        return

    print("저장된 종목 목록:")
    for name in notes:
        print(f"  - {name}")


def main() -> None:
    """SJ AI Operating System v0.3를 실행한다."""

    _configure_stdout()

    print("=" * 50)
    print("SJ AI Operating System")
    print("MVP Version 0.3")
    print("=" * 50)

    while True:
        print_menu()
        choice = input("선택 (1-4): ").strip()

        if choice == "1":
            handle_save_analysis()
        elif choice == "2":
            handle_read_note()
        elif choice == "3":
            handle_list_notes()
        elif choice == "4":
            print()
            print("프로그램을 종료합니다.")
            break
        else:
            print()
            print("오류: 1부터 4까지의 숫자를 입력하세요.")


if __name__ == "__main__":
    main()

"""
watch_progress.py — 파일 변경 감시 + Mac 알림
PROGRESS.md 변경 시 Mac 데스크탑 알림 발송
"""
import subprocess
import sys
import time
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


class ProgressWatcher(FileSystemEventHandler):
    """PROGRESS.md 파일 변경 감시"""

    def __init__(self, watch_path: str):
        """
        Args:
            watch_path: 감시할 파일 경로
        """
        self.watch_path = Path(watch_path).resolve()
        self.last_modified = 0

    def on_modified(self, event):
        """파일 수정 이벤트 처리"""
        if Path(event.src_path).resolve() == self.watch_path:
            current_time = time.time()
            # 중복 이벤트 방지 (1초 내 재발생 무시)
            if current_time - self.last_modified > 1:
                self.last_modified = current_time
                self._send_notification()

    def _send_notification(self):
        """Mac 데스크탑 알림 발송"""
        try:
            # PROGRESS.md에서 최신 완료 항목 읽기
            content = self.watch_path.read_text(encoding='utf-8')
            completed = [
                line.strip()
                for line in content.split('\n')
                if '✅' in line
            ]
            latest = completed[-1] if completed else "진행 중..."

            # osascript로 Mac 알림 발송
            script = f'''
            display notification "{latest}" ¬
                with title "TradingAgents 진행상황" ¬
                subtitle "PROGRESS.md 업데이트" ¬
                sound name "Glass"
            '''
            subprocess.run(
                ['osascript', '-e', script],
                capture_output=True,
                text=True
            )
            print(f"[알림] {latest}")
        except Exception as e:
            print(f"알림 발송 실패: {e}")


def main():
    """메인 실행"""
    project_root = Path(__file__).parent
    progress_file = project_root / 'PROGRESS.md'

    # PROGRESS.md가 없으면 생성
    if not progress_file.exists():
        progress_file.write_text(
            "# PROGRESS.md\n\n## Phase 진행상황\n\n",
            encoding='utf-8'
        )

    print(f"감시 시작: {progress_file}")
    print("PROGRESS.md 변경 시 Mac 알림이 발송됩니다.")
    print("종료: Ctrl+C")

    event_handler = ProgressWatcher(str(progress_file))
    observer = Observer()
    observer.schedule(event_handler, str(project_root), recursive=False)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


if __name__ == '__main__':
    main()

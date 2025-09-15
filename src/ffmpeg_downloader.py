# src/ffmpeg_downloader.py
import requests
import zipfile
import tempfile
import os
from pathlib import Path
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QProgressBar, QMessageBox
from PyQt6.QtCore import QThread, pyqtSignal

FFMPEG_API_URL = "https://api.github.com/repos/BtbN/FFmpeg-Builds/releases/latest"
DOWNLOAD_ASSET_NAME = "ffmpeg-master-latest-win64-gpl.zip"

class DownloadWorker(QThread):
    status_changed = pyqtSignal(str)
    progress_updated = pyqtSignal(int)
    finished = pyqtSignal(bool, str)

    def __init__(self, target_dir):
        super().__init__()
        self.target_dir = Path(target_dir)

    def run(self):
        try:
            self.status_changed.emit("최신 FFmpeg 버전 정보 확인 중...")
            self.target_dir.mkdir(parents=True, exist_ok=True)
            
            response = requests.get(FFMPEG_API_URL, timeout=10)
            response.raise_for_status()
            assets = response.json().get("assets", [])
            download_url = next((asset["browser_download_url"] for asset in assets if asset["name"] == DOWNLOAD_ASSET_NAME), None)

            if not download_url:
                self.finished.emit(False, f"다운로드할 FFmpeg 에셋({DOWNLOAD_ASSET_NAME})을 찾을 수 없습니다.")
                return

            self.status_changed.emit("FFmpeg 다운로드 중...")
            with requests.get(download_url, stream=True) as r:
                r.raise_for_status()
                total_size = int(r.headers.get('content-length', 0))
                downloaded_size = 0
                
                with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
                    for chunk in r.iter_content(chunk_size=8192):
                        tmp_file.write(chunk)
                        downloaded_size += len(chunk)
                        if total_size > 0:
                            progress = int((downloaded_size / total_size) * 100)
                            self.progress_updated.emit(progress)
                    temp_zip_path = tmp_file.name

            self.status_changed.emit("압축 해제 중...")
            self.progress_updated.emit(0)
            with zipfile.ZipFile(temp_zip_path) as zf:
                for member in zf.infolist():
                    if member.filename.endswith('ffmpeg.exe'):
                        member.filename = 'ffmpeg.exe'
                        zf.extract(member, self.target_dir)
                    elif member.filename.endswith('ffprobe.exe'):
                        member.filename = 'ffprobe.exe'
                        zf.extract(member, self.target_dir)
            
            os.remove(temp_zip_path)
            self.status_changed.emit("설치 완료!")
            self.finished.emit(True, "FFmpeg이 성공적으로 설치되었습니다.")

        except requests.RequestException as e:
            self.finished.emit(False, f"네트워크 오류: {e}")
        except Exception as e:
            self.finished.emit(False, f"처리 중 오류 발생: {e}")

class FFmpegDownloaderDialog(QDialog):
    def __init__(self, target_dir, parent=None):
        super().__init__(parent)
        self.setWindowTitle("FFmpeg 자동 설치")
        self.setModal(True)
        self.setFixedSize(400, 120)

        layout = QVBoxLayout(self)
        self.status_label = QLabel("준비 중...")
        self.progress_bar = QProgressBar()
        layout.addWidget(self.status_label)
        layout.addWidget(self.progress_bar)

        self.worker = DownloadWorker(target_dir)
        self.worker.status_changed.connect(self.status_label.setText)
        self.worker.progress_updated.connect(self.progress_bar.setValue)
        self.worker.finished.connect(self.on_finished)
        self.worker.start()

    def on_finished(self, success, message):
        """작업 완료 시 호출되는 슬롯"""
        if success:
            # --- 성공 메시지 박스를 호출하지 않고 바로 다이얼로그를 닫습니다 ---
            self.accept()
        else:
            # 실패 시에는 사용자에게 원인을 알려주어야 하므로 메시지 박스를 유지합니다.
            QMessageBox.critical(self, "오류", message)
            self.reject()
import sys
import os
import subprocess
import threading
import requests
import json
import zipfile
import shutil
import re
import time
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QPlainTextEdit
from PyQt6.QtCore import QObject, pyqtSignal, QRunnable, QThreadPool

import undetected_chromedriver as uc

STYLE_SHEET = """
QWidget { background-color: #f0f0f0; color: #212121; font-family: 'Malgun Gothic', '맑은 고딕', sans-serif; }
QLineEdit, QPlainTextEdit { background-color: #ffffff; color: #212121; border: 1px solid #dcdcdc; border-radius: 5px; font-size: 11pt; padding: 5px; }
QPushButton { background-color: #0078d7; color: white; font-size: 11pt; font-weight: bold; border: none; border-radius: 5px; padding: 8px 16px; }
QPushButton#continueButton { background-color: #28a745; }
QPushButton#continueButton:hover { background-color: #218838; }
QPushButton:hover { background-color: #005a9e; }
QPushButton:disabled { background-color: #a0a0a0; }
QLabel { color: #333333; font-size: 10pt; padding-left: 2px; }
"""

class HybridDownloaderApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Hybrid HLS Downloader v5.2 (Encoding Fixed)")
        self.setGeometry(100, 100, 680, 260)
        self.setStyleSheet(STYLE_SHEET)
        
        self.main_layout = QVBoxLayout(self)
        self.input_layout = QHBoxLayout()
        self.url_label = QLabel("페이지 또는 HLS URL:")
        self.url_entry = QLineEdit()
        self.download_button = QPushButton("다운로드")
        self.log_widget = QPlainTextEdit()
        self.log_widget.setReadOnly(True)
        self.log_widget.setFixedHeight(100)
        self.continue_button = QPushButton("분석 계속")
        self.continue_button.setObjectName("continueButton")
        self.continue_button.hide()
        self.input_layout.addWidget(self.url_label)
        self.input_layout.addWidget(self.url_entry)
        self.input_layout.addWidget(self.download_button)
        self.main_layout.addLayout(self.input_layout)
        self.main_layout.addWidget(self.log_widget)
        self.main_layout.addWidget(self.continue_button)

        self.threadpool = QThreadPool()
        self.continue_event = threading.Event()
        self.download_button.clicked.connect(self.start_download)
        self.continue_button.clicked.connect(self.on_continue_clicked)
        self.initial_setup()

    def update_log(self, message): self.log_widget.appendPlainText(message)
    def clear_log(self): self.log_widget.clear()
    def set_ui_enabled(self, enabled):
        self.url_entry.setEnabled(enabled)
        self.download_button.setEnabled(enabled)
    def show_continue_button(self, show):
        if show: self.continue_button.show()
        else: self.continue_button.hide()
    def on_continue_clicked(self):
        self.continue_event.set()
    def initial_setup(self):
        self.set_ui_enabled(False)
        worker = Worker(self.run_initial_setup)
        worker.signals.log.connect(self.update_log); worker.signals.clear_log.connect(self.clear_log)
        worker.signals.set_ui_enabled.connect(self.set_ui_enabled)
        self.threadpool.start(worker)

    def start_download(self):
        self.continue_event.clear()
        worker = Worker(self.run_download_process)
        worker.signals.log.connect(self.update_log); worker.signals.clear_log.connect(self.clear_log)
        worker.signals.set_ui_enabled.connect(self.set_ui_enabled)
        worker.signals.show_continue.connect(self.show_continue_button)
        self.threadpool.start(worker)

    def run_initial_setup(self, signals):
        signals.log.emit("프로그램 초기화 시작...")
        ytdlp_ready = self.check_ytdlp_version(signals)
        ffmpeg_ready = self.check_ffmpeg_existence(signals)
        if ytdlp_ready and ffmpeg_ready:
            signals.clear_log.emit(); signals.log.emit(">>> 준비 완료. 다운로드할 URL을 입력하세요. <<<")
            signals.set_ui_enabled.emit(True)
        else:
            signals.log.emit("\n>>> 초기화 실패. 로그를 확인하고 프로그램을 다시 시작해주세요. <<<")

    def run_download_process(self, signals):
        signals.set_ui_enabled.emit(False)
        try:
            signals.clear_log.emit()
            url_input = self.url_entry.text()
            hls_url, filename = None, None
            if ".shtml" in url_input or ".m3u8" in url_input:
                signals.log.emit("HLS 직접 주소 감지됨. 바로 다운로드를 시작합니다.")
                hls_url = url_input
            elif "yasyadong.cc" in url_input and "items_id" in url_input:
                signals.log.emit("페이지 주소 감지됨. 자동 분석을 시작합니다...")
                page_data = self.parse_page_with_uc(url_input, signals)
                if page_data:
                    hls_url, filename = page_data['hls_url'], page_data['filename']
            else:
                signals.log.emit("오류: 유효한 페이지 또는 HLS URL이 아닙니다."); return
            if not hls_url:
                signals.log.emit("오류: 다운로드할 HLS 주소를 확보하지 못했습니다."); return
            command = ["yt-dlp.exe"]
            if filename:
                safe_filename = re.sub(r'[\\/*?:"<>|]', "", filename)
                signals.log.emit(f"파일명 '{safe_filename}.mp4'으로 저장합니다.")
                command.extend(["-o", f"{safe_filename}.mp4"])
            command.append(hls_url)
            signals.log.emit(f"다운로드 대상: {hls_url}")
            
            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
            # ===> 수정된 부분: encoding을 'utf-8'에서 'cp949'로 변경 <===
            process = subprocess.Popen(
                command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, 
                encoding='cp949', errors='replace', startupinfo=startupinfo
            )
            for line in iter(process.stdout.readline, ''):
                signals.log.emit(line.strip())
            
            return_code = process.wait()
            if return_code == 0:
                signals.log.emit("\n다운로드가 성공적으로 완료되었습니다.")
            else:
                signals.log.emit(f"\n다운로드 중 오류 발생 (종료 코드: {return_code}).")
        except Exception as e:
            signals.log.emit(f"치명적인 오류 발생: {e}")
        finally:
            signals.set_ui_enabled.emit(True)
    
    def parse_page_with_uc(self, page_url, signals):
        driver = None
        try:
            signals.log.emit("자동 분석을 위해 브라우저를 시작합니다...")
            options = uc.ChromeOptions(); options.add_argument('--log-level=3')
            driver = uc.Chrome(options=options, use_subprocess=True)
            driver.get(page_url)
            
            signals.log.emit("\n!!! 사용자 인증 필요 !!!")
            signals.log.emit("1. 화면에 나타난 크롬 브라우저에서 로봇이 아님을 증명하세요 (체크박스 클릭 등).")
            signals.log.emit("2. 실제 영상 페이지가 나타나면, 이 프로그램으로 돌아와 아래 '분석 계속' 버튼을 누르세요.")
            signals.show_continue.emit(True)
            
            self.continue_event.wait()
            
            signals.show_continue.emit(False)
            signals.log.emit("\n사용자 인증 확인. 페이지 분석을 계속합니다...")
            
            html_source = driver.page_source
            hls_match = re.search(r'<source[^>]+src="([^"]+\.shtml)"[^>]+type="application/x-mpegURL"', html_source)
            hls_url = hls_match.group(1) if hls_match else None
            title_match = re.search(r'<title>(.*?)</title>', html_source)
            filename = None
            if title_match:
                full_title = title_match.group(1).strip()
                prefix_to_remove = "야동 최신 | 야스닷컴 추천 사이트 | 인기 성인영상 - "
                if full_title.startswith(prefix_to_remove):
                    filename = full_title[len(prefix_to_remove):].strip()
                else:
                    filename = full_title
            
            if hls_url and filename:
                signals.log.emit("성공: 페이지 제목과 HLS 주소를 찾았습니다.")
                return {'hls_url': hls_url, 'filename': filename}
            else:
                signals.log.emit("오류: 인증 후 페이지 소스에서 필요한 정보(제목/HLS 주소)를 파싱하지 못했습니다."); return None
        except Exception as e:
            signals.log.emit(f"페이지 자동 분석 중 오류 발생: {e}"); return None
        finally:
            if driver: driver.quit()

    def check_ytdlp_version(self, signals):
        signals.log.emit("\n[STEP 1] yt-dlp 최신 버전 확인 중...")
        try:
            api_url = "https://api.github.com/repos/yt-dlp/yt-dlp/releases/latest"
            response = requests.get(api_url, timeout=15); response.raise_for_status()
            latest_version = response.json()['tag_name']
            local_version = None
            if os.path.exists("yt-dlp.exe"):
                result = subprocess.run(["yt-dlp.exe", "--version"], capture_output=True, text=True, check=True)
                local_version = result.stdout.strip()
            signals.log.emit(f"최신 버전: {latest_version}"); signals.log.emit(f"로컬 버전: {local_version or '없음'}")
            if local_version == latest_version:
                signals.log.emit("성공: 이미 최신 버전의 yt-dlp가 있습니다."); return True
            else:
                signals.log.emit("업데이트 필요: 최신 버전의 yt-dlp를 다운로드합니다...")
                return self.download_dependency("yt-dlp.exe", self.download_ytdlp, signals)
        except Exception:
            signals.log.emit("yt-dlp 버전 확인 실패. 다운로드를 시도합니다...")
            return self.download_dependency("yt-dlp.exe", self.download_ytdlp, signals)

    def check_ffmpeg_existence(self, signals):
        signals.log.emit("\n[STEP 2] ffmpeg 존재 여부 확인 중...")
        if os.path.exists("ffmpeg.exe"):
            signals.log.emit("성공: ffmpeg.exe를 찾았습니다."); return True
        else:
            signals.log.emit("ffmpeg.exe를 찾을 수 없습니다. 다운로드를 시작합니다...")
            return self.download_dependency("ffmpeg.exe", self.download_ffmpeg, signals)

    def download_dependency(self, filename, download_func, signals):
        try: return download_func(filename, signals)
        except Exception as e:
            signals.log.emit(f"'{filename}' 다운로드 중 심각한 오류 발생: {e}"); return False

    def download_ytdlp(self, filename, signals):
        api_url = "https://api.github.com/repos/yt-dlp/yt-dlp/releases/latest"
        response = requests.get(api_url, timeout=15); response.raise_for_status()
        release_info = response.json()
        download_url = next((a['browser_download_url'] for a in release_info['assets'] if a['name'] == filename), None)
        if not download_url:
            signals.log.emit("오류: yt-dlp 릴리즈 정보를 찾을 수 없습니다."); return False
        with requests.get(download_url, stream=True) as r:
            r.raise_for_status();
            with open(filename, 'wb') as f: shutil.copyfileobj(r.raw, f)
        signals.log.emit("성공: yt-dlp 다운로드 완료."); return True

    def download_ffmpeg(self, filename, signals):
        api_url = "https://api.github.com/repos/BtbN/FFmpeg-Builds/releases/latest"
        response = requests.get(api_url, timeout=15); response.raise_for_status()
        release_info = response.json()
        download_url = next((a['browser_download_url'] for a in release_info['assets'] if 'win64-gpl' in a['name'] and a['name'].endswith('.zip') and 'shared' not in a['name']), None)
        if not download_url:
            signals.log.emit("오류: ffmpeg 릴리즈 정보를 찾을 수 없습니다."); return False
        zip_filename = "ffmpeg_download.zip"
        signals.log.emit(f"ffmpeg 다운로드 시작 (용량이 큽니다): {download_url}")
        with requests.get(download_url, stream=True) as r:
            r.raise_for_status();
            with open(zip_filename, 'wb') as f: shutil.copyfileobj(r.raw, f)
        signals.log.emit("성공: ffmpeg zip 파일 다운로드 완료.")
        signals.log.emit("ffmpeg.exe 압축 해제 중...")
        with zipfile.ZipFile(zip_filename, 'r') as z:
            ffmpeg_path = next((f for f in z.namelist() if f.endswith('/bin/ffmpeg.exe')), None)
            if not ffmpeg_path:
                signals.log.emit("오류: zip 파일에서 ffmpeg.exe를 찾지 못했습니다."); os.remove(zip_filename); return False
            with z.open(ffmpeg_path) as source, open(filename, 'wb') as target: shutil.copyfileobj(source, target)
        os.remove(zip_filename)
        signals.log.emit("성공: ffmpeg.exe 압축 해제 완료."); return True

class WorkerSignals(QObject):
    log = pyqtSignal(str); clear_log = pyqtSignal(); set_ui_enabled = pyqtSignal(bool); finished = pyqtSignal()
    show_continue = pyqtSignal(bool)
class Worker(QRunnable):
    def __init__(self, fn, *args, **kwargs):
        super().__init__(); self.fn, self.args, self.kwargs, self.signals = fn, args, kwargs, WorkerSignals()
    def run(self):
        try:
            self.fn(*self.args, **self.kwargs, signals=self.signals)
        except Exception as e:
            self.signals.log.emit(f"스레드 오류: {e}")
        finally:
            self.signals.finished.emit()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = HybridDownloaderApp()
    window.show()
    sys.exit(app.exec())
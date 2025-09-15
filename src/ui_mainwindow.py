# src/ui_mainwindow.py
import sys, logging, os, base64
from pathlib import Path
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QLineEdit, 
                             QFileDialog, QComboBox, QGroupBox, QProgressBar, QTextEdit, QMessageBox, QStatusBar,
                             QDialog, QSpinBox, QFormLayout, QToolButton, QStyle)
from PyQt6.QtGui import QIcon, QAction, QDesktopServices, QPixmap
from PyQt6.QtCore import QUrl, QTimer, QThreadPool

from .settings import SettingsManager
from .worker import FileConversionTask, WorkerSignals, get_ffmpeg_path, get_video_codec
from .update_checker import UpdateCheckWorker
from .ffmpeg_downloader import FFmpegDownloaderDialog
from .icon import ICON_B64

APP_VERSION = "v1.7.2" # 안정성 패치

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.is_initialized = False; self.thread_pool = QThreadPool(); self.active_tasks = []
        logging.info(f"사용 가능한 최대 스레드 수: {self.thread_pool.maxThreadCount()}")
        if self.check_and_prepare_ffmpeg():
            self.settings_manager = SettingsManager(); self.initUI(); self.apply_stylesheet()
            self.load_app_settings(); self.check_for_updates(); self.is_initialized = True
        else:
            QTimer.singleShot(0, self.close)

    def initUI(self):
        self.setWindowTitle(f"VideoBatchConverter {APP_VERSION}"); 
        try:
            icon_bytes = base64.b64decode(ICON_B64); pixmap = QPixmap(); pixmap.loadFromData(icon_bytes); icon = QIcon(pixmap); self.setWindowIcon(icon)
        except Exception as e:
            logging.error(f"Base64 아이콘 로드 실패: {e}")
        self.setGeometry(100, 100, 700, 750); self.worker = None
        self.create_menu_bar(); self.setStatusBar(QStatusBar(self)); self.controls = []
        central_widget = QWidget(); self.setCentralWidget(central_widget); main_layout = QVBoxLayout(central_widget)
        path_group = QGroupBox("변환 대상 폴더"); path_layout = QVBoxLayout()
        input_layout = QHBoxLayout(); self.input_path_edit = QLineEdit(); self.input_path_edit.setReadOnly(True); input_browse_btn = QPushButton("찾아보기..."); input_browse_btn.clicked.connect(self.browse_input_folder); input_layout.addWidget(QLabel("대상 폴더:")); input_layout.addWidget(self.input_path_edit); input_layout.addWidget(input_browse_btn); path_layout.addLayout(input_layout)
        path_group.setLayout(path_layout); main_layout.addWidget(path_group); self.controls.extend([self.input_path_edit, input_browse_btn])
        
        settings_group = QGroupBox("변환 설정")
        main_settings_layout = QHBoxLayout(settings_group)
        
        self.left_form_layout = QFormLayout()
        self.left_form_layout.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapAllRows)
        
        codec_items = ['H.265 (HEVC) - GPU', 'AV1 - GPU', 'AVC (H.264) - GPU', 'H.265 (HEVC) - CPU', 'AV1 - CPU', 'VP9 - CPU', 'AVC (H.264) - CPU']; self.codec_combo = QComboBox(); self.codec_combo.addItems(codec_items)
        self.codec_combo.currentTextChanged.connect(self.update_suffix)
        self.codec_combo.currentTextChanged.connect(self.update_encoder_options)
        self.left_form_layout.addRow(self.create_help_label("비디오 코덱", HELP_TEXTS["codec"]), self.codec_combo)
        
        self.resolution_combo = QComboBox(); self.resolution_combo.addItems(['원본 유지', '1080p', '720p', '480p'])
        self.left_form_layout.addRow(self.create_help_label("해상도", HELP_TEXTS["resolution"]), self.resolution_combo)

        preset_items = ['p1 (빠름, 낮은 품질)', 'p2', 'p3', 'p4 (중간)', 'p5', 'p6', 'p7 (느림, 고품질)']; self.preset_combo = QComboBox(); self.preset_combo.addItems(preset_items); self.preset_combo.setCurrentText('p5')
        self.left_form_layout.addRow(self.create_help_label("GPU 프리셋", HELP_TEXTS["preset"]), self.preset_combo)
        
        self.rate_control_combo = QComboBox(); self.rate_control_combo.currentTextChanged.connect(self.update_quality_label)
        self.left_form_layout.addRow(self.create_help_label("압축 방식", HELP_TEXTS["rate_control"]), self.rate_control_combo)
        
        self.quality_edit = QLineEdit()
        self.left_form_layout.addRow(self.create_help_label("품질/비트레이트", HELP_TEXTS["quality_value"]), self.quality_edit)
        
        self.right_form_layout = QFormLayout()
        self.right_form_layout.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapAllRows)
        
        self.suffix_edit = QLineEdit()
        self.right_form_layout.addRow(self.create_help_label("파일 접미사", HELP_TEXTS["suffix"]), self.suffix_edit)
        audio_options = ["원본 유지 (Passthrough)", "AAC 128kbps", "AAC 192kbps", "AAC 256kbps"]; self.audio_option_combo = QComboBox(); self.audio_option_combo.addItems(audio_options)
        self.right_form_layout.addRow(self.create_help_label("오디오 옵션", HELP_TEXTS["audio_option"]), self.audio_option_combo)
        self.output_format_combo = QComboBox(); self.output_format_combo.addItems(['mp4', 'mkv'])
        self.right_form_layout.addRow(self.create_help_label("출력 포맷", HELP_TEXTS["output_format"]), self.output_format_combo)
        self.parallel_jobs_spinbox = QSpinBox(); self.parallel_jobs_spinbox.setMinimum(1); self.parallel_jobs_spinbox.setMaximum(self.thread_pool.maxThreadCount()); self.parallel_jobs_spinbox.setValue(2)
        self.right_form_layout.addRow(self.create_help_label("동시 작업 수", HELP_TEXTS["parallel_jobs"]), self.parallel_jobs_spinbox)

        main_settings_layout.addLayout(self.left_form_layout); main_settings_layout.addLayout(self.right_form_layout)
        main_layout.addWidget(settings_group)
        self.controls.extend([self.codec_combo, self.resolution_combo, self.preset_combo, self.rate_control_combo, self.quality_edit, self.suffix_edit, self.audio_option_combo, self.output_format_combo, self.parallel_jobs_spinbox])
        
        progress_group = QGroupBox("진행 상황"); progress_layout = QVBoxLayout()
        progress_layout.addWidget(QLabel("전체 진행률 (완료된 파일 수)")); self.overall_progress_bar = QProgressBar(); self.overall_progress_bar.setTextVisible(True); self.overall_progress_bar.setFormat("%v / %m"); progress_layout.addWidget(self.overall_progress_bar)
        self.log_edit = QTextEdit(); self.log_edit.setReadOnly(True); progress_layout.addWidget(self.log_edit); progress_group.setLayout(progress_layout); main_layout.addWidget(progress_group)
        self.start_button = QPushButton("변환 시작"); self.start_button.clicked.connect(self.start_conversion); self.stop_button = QPushButton("중지"); self.stop_button.clicked.connect(self.stop_conversion); self.stop_button.setEnabled(False); button_layout = QHBoxLayout(); button_layout.addWidget(self.start_button); button_layout.addWidget(self.stop_button); main_layout.addLayout(button_layout); self.controls.append(self.start_button)
    
    def create_help_label(self, label_text, help_text):
        widget = QWidget(); layout = QHBoxLayout(widget); layout.setContentsMargins(0, 0, 0, 0); label = QLabel(f"{label_text}:")
        button = QToolButton(); button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MessageBoxQuestion)); button.setStyleSheet("QToolButton { border: none; padding: 0px; }")
        button.clicked.connect(lambda: QMessageBox.information(self, f"{label_text} 도움말", help_text))
        layout.addWidget(label); layout.addWidget(button); layout.addStretch(); return widget

    def update_encoder_options(self):
        is_gpu = "GPU" in self.codec_combo.currentText()
        preset_label_container = self.left_form_layout.labelForField(self.preset_combo)
        if preset_label_container:
            preset_label_container.setEnabled(is_gpu)
        self.preset_combo.setEnabled(is_gpu)
        self.rate_control_combo.clear()
        if is_gpu: self.rate_control_combo.addItems(['CQP', 'CBR', 'VBR'])
        else: self.rate_control_combo.addItems(['CRF', 'CBR', 'VBR'])

    # --- AttributeError를 해결하기 위해 수정된 메소드 ---
    def update_quality_label(self):
        rc_text = self.rate_control_combo.currentText()
        # 라벨을 포함하는 컨테이너 위젯을 먼저 찾습니다.
        container_widget = self.left_form_layout.labelForField(self.quality_edit)
        if container_widget:
            # 컨테이너 안에서 실제 QLabel 위젯을 찾습니다.
            label_widget = container_widget.findChild(QLabel)
            if label_widget:
                # 찾은 QLabel의 텍스트를 변경합니다.
                if rc_text == "CRF": label_widget.setText("CRF 값 (0-51):"); self.quality_edit.setText("23")
                elif rc_text == "CQP": label_widget.setText("CQP 값 (0-51):"); self.quality_edit.setText("28")
                else: label_widget.setText("비트레이트 (e.g. 4M):"); self.quality_edit.setText("4M")
        
    def browse_input_folder(self):
        start_path = self.input_path_edit.text()
        if not start_path: start_path = os.path.expanduser("~")
        folder = QFileDialog.getExistingDirectory(self, "대상 폴더 선택", start_path)
        if folder: self.input_path_edit.setText(folder)

    def update_suffix(self, codec_text):
        if "H.265" in codec_text or "HEVC" in codec_text: self.suffix_edit.setText("_h265")
        elif "AV1" in codec_text: self.suffix_edit.setText("_av1")
        elif "VP9" in codec_text: self.suffix_edit.setText("_vp9")
        elif "H.264" in codec_text or "AVC" in codec_text: self.suffix_edit.setText("_avc")
        else: self.suffix_edit.setText("_converted")

    def start_conversion(self):
        if not self.input_path_edit.text(): QMessageBox.warning(self, "경고", "대상 폴더를 선택해야 합니다."); return
        self.set_controls_enabled(False); self.stop_button.setEnabled(True); self.statusBar().showMessage("변환할 파일 검색 중..."); self.log_edit.clear(); self.overall_progress_bar.setValue(0)
        settings = self.get_current_settings(); self.thread_pool.setMaxThreadCount(settings["parallel_jobs"])
        video_extensions = ['.mp4', '.mkv', '.avi', '.mov', '.flv', '.wmv']; all_files = [Path(root) / file for root, _, files in os.walk(self.input_path_edit.text()) for file in files if Path(file).suffix.lower() in video_extensions]
        files_to_process = [file for file in all_files if get_video_codec(file) == 'h264']
        if not files_to_process: self.conversion_finished(False, "변환할 H.264 비디오 파일이 없습니다."); return
        self.total_files_count = len(files_to_process); self.completed_files_count = 0; self.overall_progress_bar.setMaximum(self.total_files_count); self.active_tasks = []
        self.log_edit.append(f"총 {self.total_files_count}개의 파일을 변환합니다. (동시 작업 수: {settings['parallel_jobs']})")
        for file in files_to_process:
            signals = WorkerSignals(); signals.log.connect(self.append_log); signals.progress.connect(self.update_progress_log); signals.finished.connect(self.on_task_finished)
            task = FileConversionTask(file, settings, signals); self.active_tasks.append(task); self.thread_pool.start(task)

    def on_task_finished(self, task, success):
        if task in self.active_tasks: self.active_tasks.remove(task)
        self.completed_files_count += 1; self.overall_progress_bar.setValue(self.completed_files_count)
        if self.completed_files_count >= self.total_files_count: self.conversion_finished(True, "모든 작업이 완료되었습니다.")

    def update_progress_log(self, filename, percentage):
        self.statusBar().showMessage(f"'{os.path.basename(filename)}' 변환 중... {percentage}%")
    def load_app_settings(self):
        settings = self.settings_manager.load_settings()
        if settings["geometry"]: self.restoreGeometry(settings["geometry"])
        if settings["windowState"]: self.restoreState(settings["windowState"])
        self.input_path_edit.setText(settings["input_folder"]); self.suffix_edit.setText(settings["suffix"]); self.codec_combo.setCurrentText(settings["codec"]); self.resolution_combo.setCurrentText(settings["resolution"]); self.preset_combo.setCurrentText(settings["preset"]); self.update_encoder_options(); self.rate_control_combo.setCurrentText(settings["rate_control"]); self.quality_edit.setText(settings["quality_value"]); self.audio_option_combo.setCurrentText(settings["audio_option"]); self.output_format_combo.setCurrentText(settings["output_format"]); self.parallel_jobs_spinbox.setValue(settings["parallel_jobs"])
    def get_current_settings(self):
        return {'input_folder': self.input_path_edit.text(),'suffix': self.suffix_edit.text(), 'codec': self.codec_combo.currentText(),'resolution': self.resolution_combo.currentText(), 'preset': self.preset_combo.currentText(),'rate_control': self.rate_control_combo.currentText(), 'quality_value': self.quality_edit.text(), 'audio_option': self.audio_option_combo.currentText(), 'output_format': self.output_format_combo.currentText(), 'parallel_jobs': self.parallel_jobs_spinbox.value()}
    def save_app_settings(self): settings = self.get_current_settings(); settings["geometry"] = self.saveGeometry(); settings["windowState"] = self.saveState(); self.settings_manager.save_settings(settings)
    def check_and_prepare_ffmpeg(self):
        ffmpeg_path = get_ffmpeg_path('ffmpeg'); ffprobe_path = get_ffmpeg_path('ffprobe')
        if ffmpeg_path and ffprobe_path: return True
        logging.info("FFmpeg이 없어 자동 다운로드를 시작합니다.")
        if getattr(sys, 'frozen', False): target_dir = Path(sys.executable).parent / 'assets' / 'ffmpeg'
        else: target_dir = Path(__file__).parent.parent / 'assets' / 'ffmpeg'
        downloader = FFmpegDownloaderDialog(str(target_dir)); result = downloader.exec()
        if result == QDialog.DialogCode.Accepted: return get_ffmpeg_path('ffmpeg') and get_ffmpeg_path('ffprobe')
        else: logging.error("FFmpeg 다운로드 실패 또는 취소됨."); QMessageBox.critical(None, "오류", "FFmpeg 다운로드가 취소되었거나 실패했습니다.\n프로그램을 종료합니다."); return False
    def closeEvent(self, event):
        if self.is_initialized: self.save_app_settings()
        if self.thread_pool.activeThreadCount() > 0:
            reply = QMessageBox.question(self, '종료 확인', "변환 작업이 진행 중입니다. 정말로 종료하시겠습니까?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes: self.stop_conversion(); self.thread_pool.waitForDone(); event.accept()
            else: event.ignore()
        else: event.accept()
    def apply_stylesheet(self): self.setStyleSheet("""QWidget { background-color: #f0f0f0; color: #333333; font-family: 'Malgun Gothic', 'Segoe UI', sans-serif; font-size: 10pt; } QGroupBox { background-color: #ffffff; border: 1px solid #cccccc; border-radius: 5px; margin-top: 10px; } QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; padding: 0 5px; background-color: #ffffff; color: #333333; } QLabel { color: #333333; background-color: transparent; } QLineEdit, QComboBox, QTextEdit, QSpinBox { background-color: #ffffff; color: #333333; border: 1px solid #cccccc; border-radius: 4px; padding: 5px; } QComboBox::drop-down { border: none; } QComboBox::down-arrow { image: url(none); } QPushButton { background-color: #0078d7; color: white; border: none; padding: 8px 16px; border-radius: 4px; } QPushButton:hover { background-color: #005a9e; } QPushButton:disabled { background-color: #a0a0a0; color: #e0e0e0; } QProgressBar { text-align: center; border: 1px solid #cccccc; border-radius: 4px; padding: 1px; background-color: #e0e0e0; color: #333333; } QProgressBar::chunk { background-color: #0078d7; border-radius: 4px; } QMenuBar { background-color: #e8e8e8; color: #333333; } QMenuBar::item:selected { background-color: #d0d0d0; } QMenu { background-color: #f8f8f8; border: 1px solid #cccccc; } QMenu::item:selected { background-color: #0078d7; color: white; } QStatusBar { background-color: #e8e8e8; color: #333333; font-size: 9pt; }""")
    def create_menu_bar(self): menu_bar = self.menuBar(); file_menu = menu_bar.addMenu("&파일"); exit_action = QAction("종료", self); exit_action.triggered.connect(self.close); file_menu.addAction(exit_action); help_menu = menu_bar.addMenu("&도움말"); about_action = QAction("정보", self); about_action.triggered.connect(self.show_about_dialog); help_menu.addAction(about_action)
    def show_about_dialog(self): QMessageBox.about(self, "About VideoBatchConverter", f"<h2>VideoBatchConverter {APP_VERSION}</h2><p>이 프로그램은 H.264 코덱의 비디오를 고효율 코덱으로 일괄 변환합니다.</p><p>FFmpeg을 기반으로 제작되었습니다. FFmpeg is a trademark of Fabrice Bellard.</p>")
    def set_controls_enabled(self, enabled):
        for control in self.controls: control.setEnabled(enabled)
    def conversion_finished(self, success, message):
        self.set_controls_enabled(True); self.stop_button.setEnabled(False); self.statusBar().showMessage("준비 완료", 5000)
        if success: self.overall_progress_bar.setFormat("완료"); QMessageBox.information(self, "완료", message)
        else: self.overall_progress_bar.setFormat("오류 또는 중단"); 
    def stop_conversion(self):
        logging.info("모든 변환 작업을 중단합니다."); self.thread_pool.clear()
        for task in self.active_tasks: task.stop()
        self.append_log("사용자가 변환 중단을 요청했습니다. 실행 중인 작업이 종료되고 대기 작업이 취소됩니다.")
    def append_log(self, message): self.log_edit.append(message)
    def check_for_updates(self):
        self.statusBar().showMessage("최신 버전을 확인 중입니다..."); self.update_worker = UpdateCheckWorker(APP_VERSION); self.update_worker.finished.connect(self.on_update_check_finished); self.update_worker.start()
    def on_update_check_finished(self, result):
        if result.get("update"):
            self.statusBar().showMessage(f"새 버전 발견: {result.get('version')}"); msg_box = QMessageBox(self); msg_box.setIcon(QMessageBox.Icon.Information); msg_box.setText(f"새로운 버전 ({result.get('version')})이 있습니다.\n다운로드 페이지로 이동하시겠습니까?"); msg_box.setWindowTitle("업데이트 알림"); msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if msg_box.exec() == QMessageBox.StandardButton.Yes: QDesktopServices.openUrl(QUrl(result.get("url")))
        else: self.statusBar().showMessage("준비 완료", 3000)

# --- 도움말 텍스트 정의 ---
HELP_TEXTS = {
    "codec": "비디오를 압축하는 방식(알고리즘)을 선택합니다.\n\n- GPU: 그래픽카드를 사용해 매우 빠르게 변환합니다.\n- CPU: 처리 속도는 느리지만, 일부 고급 옵션 사용이 가능합니다.\n\nH.265와 AV1이 H.264보다 압축 효율이 높습니다.",
    "resolution": "동영상의 해상도(가로x세로 크기)를 설정합니다.\n\n- 원본 유지: 원본 동영상의 해상도를 그대로 사용합니다.\n- 1080p / 720p: 세로 크기를 해당 값으로 맞추고 가로 크기는 비율에 맞게 조절합니다.",
    "preset": "GPU 인코딩의 속도와 품질 간의 균형을 설정합니다.\n\n- p1: 가장 빠르지만 압축 효율은 가장 낮습니다.\n- p7: 가장 느리지만 동일 용량 대비 화질이 가장 좋습니다.\n- p4~p5가 일반적인 균형점입니다.",
    "rate_control": "화질 또는 비트레이트를 제어하는 방식을 선택합니다.\n\n- CQP/CRF: 지정된 화질 수준(숫자)을 목표로 용량이 조절됩니다. (권장)\n- CBR: 지정된 비트레이트(용량)를 계속 유지하려고 시도합니다. (스트리밍용)",
    "quality_value": "압축 품질을 설정합니다.\n\n- CQP/CRF의 경우 숫자가 낮을수록 고품질/고용량입니다. (추천: 24-28)\n- CBR의 경우 목표 비트레이트를 의미합니다. (예: 4M은 4Mbps)",
    "suffix": "변환된 파일의 원본 이름 뒤에 붙을 텍스트입니다.\n\n예: MyMovie.mp4 -> MyMovie_h265.mp4",
    "audio_option": "오디오 트랙의 처리 방식을 선택합니다.\n\n- 원본 유지 (Passthrough): 원본 오디오를 그대로 복사합니다. 가장 빠르고 음질 손실이 없습니다. (권장)\n- AAC ...kbps: 오디오를 지정된 비트레이트의 AAC 코덱으로 다시 인코딩합니다.",
    "output_format": "영상을 담을 파일 형식(컨테이너)을 선택합니다.\n\n- mp4: 가장 범용적이고 호환성이 높은 형식입니다.\n- mkv: 여러 개의 오디오/자막 트랙을 담을 수 있는 유연한 형식입니다.",
    "parallel_jobs": "동시에 몇 개의 파일을 변환할지 설정합니다.\n\n사용 중인 그래픽카드의 NVENC 엔진 수(하이엔드 모델은 2개)에 맞추는 것이 가장 효율적입니다."
}
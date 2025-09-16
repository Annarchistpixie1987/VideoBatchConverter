# src/ui_mainwindow.py
# v2.0.0 (최종 통합 안정화)
import sys, logging, os, base64
from pathlib import Path
from functools import partial
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QLineEdit, 
                             QFileDialog, QComboBox, QGroupBox, QProgressBar, QTextEdit, QMessageBox, QStatusBar,
                             QDialog, QSpinBox, QFormLayout, QToolButton, QStyle, QSplitter, QListWidget, 
                             QListWidgetItem, QToolBar, QApplication, QAbstractItemView)
from PyQt6.QtGui import QIcon, QAction, QDesktopServices, QPixmap, QActionGroup
from PyQt6.QtCore import QUrl, QTimer, QThreadPool, QMutex, Qt

from .settings import SettingsManager
from .worker import FileConversionTask, WorkerSignals, get_ffmpeg_path, get_video_codec, get_media_info
from .update_checker import UpdateCheckWorker
from .ffmpeg_downloader import FFmpegDownloaderDialog
from .about_dialog import AboutDialog
from . import icon

APP_VERSION = "v2.0.0"

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.is_initialized = False; self._is_applying_preset = False; self.thread_pool = QThreadPool(); 
        self.active_tasks = []; self.task_mutex = QMutex(); self.stop_requested = False
        logging.info(f"사용 가능한 최대 스레드 수: {self.thread_pool.maxThreadCount()}")

        if self.check_and_prepare_ffmpeg():
            self.settings_manager = SettingsManager()
            self.initUI()
            self.apply_stylesheet()
            self.load_app_settings()
            self.check_for_updates()
            self.is_initialized = True
        else:
            QTimer.singleShot(0, self.close)

    def initUI(self):
        self.setWindowTitle(f"VideoBatchConverter {APP_VERSION}")
        try:
            self.setWindowIcon(self.get_icon_from_base64(icon.MAIN_ICON))
        except Exception as e: 
            logging.error(f"메인 아이콘 로드 실패: {e}")
            self.setWindowIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon))

        self.setGeometry(100, 100, 900, 700)
        self.create_menu_bar(); self.setStatusBar(QStatusBar(self))
        
        self.create_toolbar()

        central_widget = QWidget(); self.setCentralWidget(central_widget); self.setAcceptDrops(True)
        main_layout = QVBoxLayout(central_widget)

        path_group = QGroupBox("변환 대상 폴더")
        path_layout = QHBoxLayout(path_group)
        self.input_path_edit = QLineEdit(); self.input_path_edit.setReadOnly(True)
        self.input_browse_btn = QPushButton("폴더 선택..."); self.input_browse_btn.clicked.connect(self.add_folder)
        path_layout.addWidget(QLabel("대상 폴더:")); path_layout.addWidget(self.input_path_edit); path_layout.addWidget(self.input_browse_btn)
        main_layout.addWidget(path_group)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter, 1)

        left_panel = QWidget(); left_layout = QVBoxLayout(left_panel)
        queue_group = QGroupBox("변환 목록"); queue_layout = QVBoxLayout(queue_group)
        self.file_list_widget = QListWidget(); self.file_list_widget.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection); self.file_list_widget.currentItemChanged.connect(self.update_file_info_panel)
        queue_layout.addWidget(self.file_list_widget)
        queue_button_layout = QHBoxLayout(); add_file_btn = QPushButton("파일 추가"); add_file_btn.clicked.connect(self.add_files); add_folder_btn = QPushButton("폴더 추가"); add_folder_btn.clicked.connect(self.add_folder); remove_btn = QPushButton("선택 삭제"); remove_btn.clicked.connect(self.remove_selected_files); clear_btn = QPushButton("목록 비우기"); clear_btn.clicked.connect(self.file_list_widget.clear)
        queue_button_layout.addWidget(add_file_btn); queue_button_layout.addWidget(add_folder_btn); queue_button_layout.addWidget(remove_btn); queue_button_layout.addWidget(clear_btn)
        queue_layout.addLayout(queue_button_layout)
        left_layout.addWidget(queue_group); splitter.addWidget(left_panel)

        right_panel = QWidget(); right_layout = QVBoxLayout(right_panel)
        self.init_settings_widgets(right_layout)
        self.init_info_widgets(right_layout)
        self.init_progress_widgets(right_layout)
        splitter.addWidget(right_panel); splitter.setSizes([350, 550])

        self.start_button = QPushButton("변환 시작"); self.start_button.clicked.connect(self.start_conversion)
        self.stop_button = QPushButton("중지"); self.stop_button.clicked.connect(self.stop_conversion); self.stop_button.setEnabled(False)
        button_layout = QHBoxLayout(); button_layout.addWidget(self.start_button); button_layout.addWidget(self.stop_button)
        main_layout.addLayout(button_layout)
        
        self.controls = [self.input_browse_btn, self.start_button, self.toolbar, add_file_btn, add_folder_btn, remove_btn, clear_btn] + self.detail_controls

    def get_icon_from_base64(self, b64_data):
        if not b64_data: return self.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon)
        pixmap = QPixmap(); pixmap.loadFromData(base64.b64decode(b64_data)); return QIcon(pixmap)

    def create_toolbar(self):
        self.toolbar = self.addToolBar("프리셋"); self.preset_action_group = QActionGroup(self); self.preset_action_group.setExclusive(True)
        preset_icons = {
            "일반용 / 아카이빙 (균형)": icon.ARCHIVE_ICON, "Apple 기기 호환 (AV1)": icon.APPLE_ICON,
            "Android 기기 호환 (VP9)": icon.ANDROID_ICON, "YouTube 업로드 (1080p)": icon.YOUTUBE_ICON,
            "YouTube 업로드 (720p)": icon.YOUTUBE_ICON
        }
        for name in PRESETS.keys():
            action_icon = self.get_icon_from_base64(preset_icons.get(name, icon.MAIN_ICON))
            action = QAction(action_icon, name, self); action.setCheckable(True)
            action.triggered.connect(partial(self.apply_preset, name)); self.toolbar.addAction(action); self.preset_action_group.addAction(action)
    
    def show_about_dialog(self):
        dialog = AboutDialog(APP_VERSION, self)
        dialog.exec()
        
    def init_settings_widgets(self, parent_layout):
        settings_group = QGroupBox("세부 설정"); main_settings_layout = QHBoxLayout(settings_group); self.left_form_layout = QFormLayout(); self.left_form_layout.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapAllRows); self.detail_controls = []
        codec_items = ['H.265 (HEVC) - GPU', 'AV1 - GPU', 'AVC (H.264) - GPU', 'H.265 (HEVC) - CPU', 'AV1 - CPU', 'VP9 - CPU']; self.codec_combo = QComboBox(); self.codec_combo.addItems(codec_items); self.left_form_layout.addRow(self.create_help_label("비디오 코덱", HELP_TEXTS["codec"]), self.codec_combo); self.detail_controls.append(self.codec_combo)
        self.resolution_combo = QComboBox(); self.resolution_combo.addItems(['원본 유지', '1080p', '720p']); self.left_form_layout.addRow(self.create_help_label("해상도", HELP_TEXTS["resolution"]), self.resolution_combo); self.detail_controls.append(self.resolution_combo)
        preset_items = ['p1 (빠름, 낮은 품질)', 'p2', 'p3', 'p4 (중간)', 'p5', 'p6', 'p7 (느림, 고품질)']; self.preset_option_combo = QComboBox(); self.preset_option_combo.addItems(preset_items); self.left_form_layout.addRow(self.create_help_label("GPU 프리셋", HELP_TEXTS["preset"]), self.preset_option_combo); self.detail_controls.append(self.preset_option_combo)
        self.rate_control_combo = QComboBox(); self.left_form_layout.addRow(self.create_help_label("압축 방식", HELP_TEXTS["rate_control"]), self.rate_control_combo); self.detail_controls.append(self.rate_control_combo)
        self.quality_edit = QLineEdit(); self.left_form_layout.addRow(self.create_help_label("품질/비트레이트", HELP_TEXTS["quality_value"]), self.quality_edit); self.detail_controls.append(self.quality_edit)
        self.right_form_layout = QFormLayout(); self.right_form_layout.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapAllRows)
        self.suffix_edit = QLineEdit(); self.right_form_layout.addRow(self.create_help_label("파일 접미사", HELP_TEXTS["suffix"]), self.suffix_edit); self.detail_controls.append(self.suffix_edit)
        audio_options = ["원본 유지 (Passthrough)", "AAC 128kbps", "AAC 192kbps", "AAC 256kbps"]; self.audio_option_combo = QComboBox(); self.audio_option_combo.addItems(audio_options); self.right_form_layout.addRow(self.create_help_label("오디오 옵션", HELP_TEXTS["audio_option"]), self.audio_option_combo); self.detail_controls.append(self.audio_option_combo)
        self.output_format_combo = QComboBox(); self.output_format_combo.addItems(['mp4', 'mkv']); self.right_form_layout.addRow(self.create_help_label("출력 포맷", HELP_TEXTS["output_format"]), self.output_format_combo); self.detail_controls.append(self.output_format_combo)
        self.parallel_jobs_spinbox = QSpinBox(); self.parallel_jobs_spinbox.setMinimum(1); self.parallel_jobs_spinbox.setMaximum(self.thread_pool.maxThreadCount()); self.right_form_layout.addRow(self.create_help_label("동시 작업 수", HELP_TEXTS["parallel_jobs"]), self.parallel_jobs_spinbox); self.detail_controls.append(self.parallel_jobs_spinbox)
        main_settings_layout.addLayout(self.left_form_layout); main_settings_layout.addLayout(self.right_form_layout); parent_layout.addWidget(settings_group)
        for control in self.detail_controls:
            if isinstance(control, (QComboBox, QSpinBox)): (control.currentTextChanged if isinstance(control, QComboBox) else control.valueChanged).connect(self.on_setting_changed)
            elif isinstance(control, QLineEdit): control.textChanged.connect(self.on_setting_changed)
        self.codec_combo.currentTextChanged.connect(self.update_suffix); self.codec_combo.currentTextChanged.connect(self.update_encoder_options); self.rate_control_combo.currentTextChanged.connect(self.update_quality_label)

    def init_info_widgets(self, parent_layout):
        info_group = QGroupBox("파일 정보"); info_layout = QFormLayout(info_group)
        self.info_filename_label = QLabel("-"); self.info_filename_label.setWordWrap(True); self.info_size_label = QLabel("-"); self.info_resolution_label = QLabel("-"); self.info_video_codec_label = QLabel("-"); self.info_audio_codec_label = QLabel("-")
        info_layout.addRow("파일명:", self.info_filename_label); info_layout.addRow("크기 / 길이:", self.info_size_label); info_layout.addRow("해상도:", self.info_resolution_label); info_layout.addRow("비디오 정보:", self.info_video_codec_label); info_layout.addRow("오디오 정보:", self.info_audio_codec_label); parent_layout.addWidget(info_group)

    def init_progress_widgets(self, parent_layout):
        progress_group = QGroupBox("진행 상황"); progress_layout = QVBoxLayout(progress_group)
        progress_layout.addWidget(QLabel("전체 진행률 (완료된 파일 수)")); self.overall_progress_bar = QProgressBar(); self.overall_progress_bar.setTextVisible(True); self.overall_progress_bar.setFormat("%v / %m"); progress_layout.addWidget(self.overall_progress_bar); self.log_edit = QTextEdit(); self.log_edit.setReadOnly(True); progress_layout.addWidget(self.log_edit)
        parent_layout.addWidget(progress_group)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls(): event.acceptProposedAction()

    def dropEvent(self, event):
        paths = [url.toLocalFile() for url in event.mimeData().urls()]; self.add_paths_to_queue(paths)

    def add_paths_to_queue(self, paths):
        files_to_add = []; folders_to_scan = []
        for path in paths:
            if os.path.isdir(path): folders_to_scan.append(Path(path))
            elif os.path.isfile(path): files_to_add.append(Path(path))
        if folders_to_scan: self.populate_file_list_from_folders(folders_to_scan, clear_list=False)
        for file in files_to_add: self.add_single_file_to_list(file)

    def add_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "비디오 파일 선택", "", "Video Files (*.mp4 *.mkv *.avi *.mov *.flv *.wmv)");
        if files: self.add_paths_to_queue(files)

    def add_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "대상 폴더 선택", self.input_path_edit.text() or os.path.expanduser("~"));
        if folder: self.input_path_edit.setText(folder); self.populate_file_list_from_folders([folder], clear_list=True)

    def remove_selected_files(self):
        selected_items = self.file_list_widget.selectedItems()
        if not selected_items: return
        for item in selected_items: self.file_list_widget.takeItem(self.file_list_widget.row(item))

    def add_single_file_to_list(self, file_path):
        current_paths = [self.file_list_widget.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.file_list_widget.count())]
        if str(file_path) not in current_paths:
            if get_video_codec(file_path) == 'h264':
                item = QListWidgetItem(file_path.name); item.setData(Qt.ItemDataRole.UserRole, str(file_path)); self.file_list_widget.addItem(item); self.log_edit.append(f"추가됨: {file_path.name}")
            else: self.log_edit.append(f"H.264가 아니므로 건너뜀: {file_path.name}")
        else: self.log_edit.append(f"이미 목록에 존재함: {file_path.name}")

    def populate_file_list_from_folders(self, folder_paths, clear_list=True):
        if clear_list: self.file_list_widget.clear()
        self.log_edit.setText("폴더에서 H.264 파일을 검색합니다..."); QApplication.processEvents()
        video_extensions = ['.mp4', '.mkv', '.avi', '.mov', '.flv', '.wmv']; h264_files_found = 0
        for folder_path in folder_paths:
            files_to_check = [Path(root) / file for root, _, files in os.walk(folder_path) for file in files if Path(file).suffix.lower() in video_extensions]
            for file in files_to_check:
                if get_video_codec(file) == 'h264':
                    current_paths = [self.file_list_widget.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.file_list_widget.count())]
                    if str(file) not in current_paths:
                        item = QListWidgetItem(file.name); item.setData(Qt.ItemDataRole.UserRole, str(file)); self.file_list_widget.addItem(item); h264_files_found += 1
        self.log_edit.append(f"총 {h264_files_found}개의 새 파일을 목록에 추가했습니다.")

    def update_file_info_panel(self, item):
        if not item: self.info_filename_label.setText("-"); self.info_size_label.setText("-"); self.info_resolution_label.setText("-"); self.info_video_codec_label.setText("-"); self.info_audio_codec_label.setText("-"); return
        file_path = item.data(Qt.ItemDataRole.UserRole); info = get_media_info(file_path);
        if not info: return
        try:
            video_stream = next((s for s in info['streams'] if s['codec_type'] == 'video'), None); audio_stream = next((s for s in info['streams'] if s['codec_type'] == 'audio'), None)
            self.info_filename_label.setText(os.path.basename(file_path)); size_mb = float(info['format'].get('size', 0)) / (1024*1024); duration_sec = float(info['format'].get('duration', 0))
            self.info_size_label.setText(f"{size_mb:.1f} MB / {int(duration_sec // 60)}분 {int(duration_sec % 60)}초")
            if video_stream: self.info_resolution_label.setText(f"{video_stream.get('width')} x {video_stream.get('height')}"); bitrate_kbps = int(video_stream.get('bit_rate', '0')) // 1000; self.info_video_codec_label.setText(f"{video_stream.get('codec_name', '-')} ({bitrate_kbps} kbps)")
            if audio_stream: bitrate_kbps = int(audio_stream.get('bit_rate', '0')) // 1000; self.info_audio_codec_label.setText(f"{audio_stream.get('codec_name', '-')} ({bitrate_kbps} kbps, {audio_stream.get('channels', 0)} ch)")
        except Exception as e: logging.error(f"미디어 정보 파싱 오류: {e}")

    def browse_input_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "대상 폴더 선택", self.input_path_edit.text() or os.path.expanduser("~"))
        if folder: self.input_path_edit.setText(folder); self.populate_file_list_from_folders([folder], clear_list=True)

    def apply_preset(self, preset_name):
        action_to_check = next((a for a in self.preset_action_group.actions() if a.text() == preset_name), None);
        if action_to_check and not action_to_check.isChecked(): action_to_check.setChecked(True)
        if self._is_applying_preset: return
        self._is_applying_preset = True
        for control in self.detail_controls: control.blockSignals(True)
        try:
            settings = PRESETS[preset_name]
            self.codec_combo.setCurrentText(settings["codec"]); self.resolution_combo.setCurrentText(settings["resolution"]); self.preset_option_combo.setCurrentText(settings["preset_option"]); self.rate_control_combo.setCurrentText(settings["rate_control"]); self.quality_edit.setText(settings["quality_value"]); self.audio_option_combo.setCurrentText(settings["audio_option"]); self.output_format_combo.setCurrentText(settings["output_format"]); self.parallel_jobs_spinbox.setValue(settings.get("parallel_jobs", 2))
            self.update_suffix(settings["codec"], force=True)
        finally:
            for control in self.detail_controls: control.blockSignals(False)
            self._is_applying_preset = False; self.update_encoder_options(); self.update_quality_label(); self.on_setting_changed()

    def on_setting_changed(self, *args):
        if self._is_applying_preset: return
        current_settings = self.get_current_settings(); match_found = False
        for name, preset_values in PRESETS.items():
            is_match = all(current_settings.get(key) == preset_values.get(key) for key in preset_values if key != 'preset')
            if is_match:
                action_to_check = next((a for a in self.preset_action_group.actions() if a.text() == name), None)
                if action_to_check: self.preset_action_group.blockSignals(True); action_to_check.setChecked(True); self.preset_action_group.blockSignals(False)
                match_found = True; break
        if not match_found:
             checked_action = self.preset_action_group.checkedAction()
             if checked_action: self.preset_action_group.blockSignals(True); checked_action.setChecked(False); self.preset_action_group.blockSignals(False)

    def load_app_settings(self):
        settings = self.settings_manager.load_settings()
        if settings["geometry"]: self.restoreGeometry(settings["geometry"])
        else: self.center_window()
        if settings["windowState"]: self.restoreState(settings["windowState"])
        self.input_path_edit.setText(settings["input_folder"])
        if settings["input_folder"]: self.populate_file_list_from_folders([settings["input_folder"]])
        preset_name = settings.get("preset", "일반용 / 아카이빙 (균형)")
        if preset_name != "사용자 정의" and preset_name in PRESETS:
            self.apply_preset(preset_name)
        else:
            for control in self.detail_controls: control.blockSignals(True)
            self.suffix_edit.setText(settings["suffix"]); self.codec_combo.setCurrentText(settings["codec"]); self.resolution_combo.setCurrentText(settings["resolution"]); self.preset_option_combo.setCurrentText(settings["preset_option"]); self.rate_control_combo.setCurrentText(settings["rate_control"]); self.quality_edit.setText(settings["quality_value"]); self.audio_option_combo.setCurrentText(settings["audio_option"]); self.output_format_combo.setCurrentText(settings["output_format"]); self.parallel_jobs_spinbox.setValue(settings["parallel_jobs"])
            for control in self.detail_controls: control.blockSignals(False)
            self.update_encoder_options(); self.update_quality_label()
    
    def get_current_settings(self):
        active_preset = self.preset_action_group.checkedAction(); preset_name = active_preset.text() if active_preset else "사용자 정의"
        return {'preset': preset_name,'input_folder': self.input_path_edit.text(),'suffix': self.suffix_edit.text(), 'codec': self.codec_combo.currentText(),'resolution': self.resolution_combo.currentText(), 'preset_option': self.preset_option_combo.currentText(),'rate_control': self.rate_control_combo.currentText(), 'quality_value': self.quality_edit.text(), 'audio_option': self.audio_option_combo.currentText(), 'output_format': self.output_format_combo.currentText(), 'parallel_jobs': self.parallel_jobs_spinbox.value()}
    
    def center_window(self):
        screen = self.screen().geometry(); window_size = self.geometry(); self.move((screen.width() - window_size.width()) // 2, (screen.height() - window_size.height()) // 2)

    def create_help_label(self, label_text, help_text):
        widget = QWidget(); layout = QHBoxLayout(widget); layout.setContentsMargins(0, 0, 0, 0); label = QLabel(f"{label_text}:")
        button = QToolButton(); button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MessageBoxQuestion)); button.setStyleSheet("QToolButton { border: none; padding: 0px; }")
        button.clicked.connect(lambda: QMessageBox.information(self, f"{label_text} 도움말", help_text)); layout.addWidget(label); layout.addWidget(button); layout.addStretch(); return widget
    
    def update_encoder_options(self, *args):
        is_gpu = "GPU" in self.codec_combo.currentText(); preset_label_container = self.left_form_layout.labelForField(self.preset_option_combo)
        if preset_label_container: preset_label_container.setEnabled(is_gpu)
        self.preset_option_combo.setEnabled(is_gpu); self.rate_control_combo.blockSignals(True); self.rate_control_combo.clear()
        if is_gpu: self.rate_control_combo.addItems(['CQP', 'CBR', 'VBR'])
        else: self.rate_control_combo.addItems(['CRF', 'CBR', 'VBR'])
        self.rate_control_combo.blockSignals(False); self.update_quality_label()

    def update_quality_label(self, *args):
        rc_text = self.rate_control_combo.currentText(); container_widget = self.left_form_layout.labelForField(self.quality_edit)
        if container_widget:
            label_widget = container_widget.findChild(QLabel)
            if label_widget:
                self.quality_edit.blockSignals(True)
                if rc_text == "CRF": label_widget.setText("CRF 값 (0-51):"); self.quality_edit.setText("23")
                elif rc_text == "CQP": label_widget.setText("CQP 값 (0-51):"); self.quality_edit.setText("28")
                else: label_widget.setText("비트레이트 (e.g. 10M):"); self.quality_edit.setText("10M")
                self.quality_edit.blockSignals(False)
    
    def update_suffix(self, codec_text, force=False):
        if self._is_applying_preset and not force: return
        if "H.265" in codec_text or "HEVC" in codec_text: self.suffix_edit.setText("_h265")
        elif "AV1" in codec_text: self.suffix_edit.setText("_av1")
        elif "VP9" in codec_text: self.suffix_edit.setText("_vp9")
        elif "H.264" in codec_text or "AVC" in codec_text: self.suffix_edit.setText("_avc")
        else: self.suffix_edit.setText("_converted")

    def start_conversion(self):
        selected_items = self.file_list_widget.selectedItems()
        if selected_items: files_to_process = [item.data(Qt.ItemDataRole.UserRole) for item in selected_items]
        else: files_to_process = [self.file_list_widget.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.file_list_widget.count())]
        if not files_to_process: QMessageBox.warning(self, "경고", "변환할 파일이 목록에 없습니다."); return
        self.stop_requested = False; self.set_controls_enabled(False); self.stop_button.setEnabled(True); self.statusBar().showMessage("변환 작업 시작..."); self.overall_progress_bar.setValue(0)
        settings = self.get_current_settings(); self.thread_pool.setMaxThreadCount(settings["parallel_jobs"])
        self.total_files_count = len(files_to_process); self.completed_files_count = 0; self.overall_progress_bar.setMaximum(self.total_files_count);
        self.task_mutex.lock(); self.active_tasks.clear(); self.task_mutex.unlock()
        self.log_edit.setText(f"총 {self.total_files_count}개의 파일을 변환합니다. (동시 작업 수: {settings['parallel_jobs']})")
        for file in files_to_process:
            signals = WorkerSignals(); signals.log.connect(self.append_log); signals.progress.connect(self.update_progress_log); signals.finished.connect(self.on_task_finished)
            task = FileConversionTask(file, settings, signals)
            self.task_mutex.lock(); self.active_tasks.append(task); self.task_mutex.unlock()
            self.thread_pool.start(task)
            
    def on_task_finished(self, task, success):
        self.task_mutex.lock(); 
        if task in self.active_tasks: self.active_tasks.remove(task)
        self.task_mutex.unlock()
        if self.stop_requested: return
        self.completed_files_count += 1; self.overall_progress_bar.setValue(self.completed_files_count)
        if self.completed_files_count >= self.total_files_count:
            self.conversion_finished(True, "모든 작업이 완료되었습니다.")
            
    def update_progress_log(self, filename, percentage):
        self.statusBar().showMessage(f"'{os.path.basename(filename)}' 변환 중... {percentage}%")
            
    def save_app_settings(self): settings = self.get_current_settings(); settings["geometry"] = self.saveGeometry(); settings["windowState"] = self.saveState(); self.settings_manager.save_settings(settings)
    
    def check_and_prepare_ffmpeg(self):
        ffmpeg_path = get_ffmpeg_path('ffmpeg'); ffprobe_path = get_ffmpeg_path('ffprobe');
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
        
    def apply_stylesheet(self): self.setStyleSheet("""QWidget { background-color: #f0f0f0; color: #333333; font-family: 'Malgun Gothic', 'Segoe UI', sans-serif; font-size: 10pt; } QGroupBox { background-color: #ffffff; border: 1px solid #cccccc; border-radius: 5px; margin-top: 10px; } QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; padding: 0 5px; background-color: #ffffff; color: #333333; } QLabel { color: #333333; background-color: transparent; } QLineEdit, QComboBox, QTextEdit, QSpinBox { background-color: #ffffff; color: #333333; border: 1px solid #cccccc; border-radius: 4px; padding: 5px; } QToolBar { background-color: #e8e8e8; border-bottom: 1px solid #cccccc;} QToolBar QToolButton { padding: 4px; margin: 2px; } QToolBar QToolButton:checked { background-color: #cde8ff; border: 1px solid #0078d7;} QComboBox::drop-down { border: none; } QComboBox::down-arrow { image: url(none); } QPushButton { background-color: #0078d7; color: white; border: none; padding: 8px 16px; border-radius: 4px; } QPushButton:hover { background-color: #005a9e; } QPushButton:disabled { background-color: #a0a0a0; color: #e0e0e0; } QProgressBar { text-align: center; border: 1px solid #cccccc; border-radius: 4px; padding: 1px; background-color: #e0e0e0; color: #333333; } QProgressBar::chunk { background-color: #0078d7; border-radius: 4px; } QMenuBar { background-color: #e8e8e8; color: #333333; } QMenuBar::item:selected { background-color: #d0d0d0; } QMenu { background-color: #f8f8f8; border: 1px solid #cccccc; } QMenu::item:selected { background-color: #0078d7; color: white; } QStatusBar { background-color: #e8e8e8; color: #333333; font-size: 9pt; }""")
    def create_menu_bar(self): menu_bar = self.menuBar(); file_menu = menu_bar.addMenu("&파일"); exit_action = QAction("종료", self); exit_action.triggered.connect(self.close); file_menu.addAction(exit_action); help_menu = menu_bar.addMenu("&도움말"); about_action = QAction("정보", self); about_action.triggered.connect(self.show_about_dialog); help_menu.addAction(about_action)
    
    def set_controls_enabled(self, enabled):
        for control in self.controls: control.setEnabled(enabled)
        
    def conversion_finished(self, success, message):
        self.set_controls_enabled(True); self.stop_button.setEnabled(False); self.statusBar().showMessage("준비 완료", 5000)
        if success: self.overall_progress_bar.setFormat("완료"); QMessageBox.information(self, "완료", message)
        else: self.overall_progress_bar.setFormat("오류 또는 중단"); 
        
    def stop_conversion(self):
        logging.info("모든 변환 작업을 중단합니다."); self.stop_requested = True;
        self.task_mutex.lock(); 
        for task in self.active_tasks: task.stop()
        self.active_tasks.clear(); self.task_mutex.unlock()
        self.thread_pool.clear()
        self.set_controls_enabled(True); self.stop_button.setEnabled(False); self.statusBar().showMessage("작업이 중단되었습니다.", 5000); self.overall_progress_bar.setFormat("중단됨")
        self.append_log("모든 변환 작업이 중단되었습니다.")
        
    def append_log(self, message): self.log_edit.append(message)
    
    def check_for_updates(self):
        self.statusBar().showMessage("최신 버전을 확인 중입니다..."); self.update_worker = UpdateCheckWorker(APP_VERSION); self.update_worker.finished.connect(self.on_update_check_finished); self.update_worker.start()
        
    def on_update_check_finished(self, result):
        if result.get("update"):
            self.statusBar().showMessage(f"새 버전 발견: {result.get('version')}"); msg_box = QMessageBox(self); msg_box.setIcon(QMessageBox.Icon.Information); msg_box.setText(f"새로운 버전 ({result.get('version')})이 있습니다.\n다운로드 페이지로 이동하시겠습니까?"); msg_box.setWindowTitle("업데이트 알림"); msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if msg_box.exec() == QMessageBox.StandardButton.Yes: QDesktopServices.openUrl(QUrl(result.get("url")))
        else: self.statusBar().showMessage("준비 완료", 3000)

PRESETS = {
    "일반용 / 아카이빙 (균형)": {"codec": "H.265 (HEVC) - GPU", "resolution": "원본 유지", "preset_option": "p5", "rate_control": "CQP", "quality_value": "28", "audio_option": "원본 유지 (Passthrough)", "output_format": "mkv", "parallel_jobs": 2},
    "Apple 기기 호환 (AV1)": {"codec": "AV1 - GPU", "resolution": "1080p", "preset_option": "p5", "rate_control": "CQP", "quality_value": "29", "audio_option": "원본 유지 (Passthrough)", "output_format": "mp4", "parallel_jobs": 2},
    "Android 기기 호환 (VP9)": {"codec": "VP9 - CPU", "resolution": "1080p", "preset_option": "p5", "rate_control": "CRF", "quality_value": "31", "audio_option": "원본 유지 (Passthrough)", "output_format": "mp4", "parallel_jobs": 2},
    "YouTube 업로드 (1080p)": {"codec": "H.265 (HEVC) - GPU", "resolution": "1080p", "preset_option": "p6", "rate_control": "VBR", "quality_value": "10M", "audio_option": "AAC 192kbps", "output_format": "mp4", "parallel_jobs": 2},
    "YouTube 업로드 (720p)": {"codec": "H.265 (HEVC) - GPU", "resolution": "720p", "preset_option": "p6", "rate_control": "VBR", "quality_value": "6M", "audio_option": "AAC 192kbps", "output_format": "mp4", "parallel_jobs": 2}
}
HELP_TEXTS = {
    "codec": "비디오를 압축하는 방식(알고리즘)을 선택합니다.\n\n- GPU: 그래픽카드를 사용해 매우 빠르게 변환합니다.\n- CPU: 처리 속도는 느리지만, 일부 고급 옵션 사용이 가능합니다.\n\nH.265와 AV1이 H.264보다 압축 효율이 높습니다.",
    "resolution": "동영상의 해상도(가로x세로 크기)를 설정합니다.\n\n- 원본 유지: 원본 동영상의 해상도를 그대로 사용합니다.\n- 1080p / 720p: 세로 크기를 해당 값으로 맞춥니다. 원본보다 작으면 축소, 크면 확대됩니다.",
    "preset": "GPU 인코딩의 속도와 품질 간의 균형을 설정합니다.\n\n- p1: 가장 빠르지만 압축 효율은 가장 낮습니다.\n- p7: 가장 느리지만 동일 용량 대비 화질이 가장 좋습니다.\n- p4~p5가 일반적인 균형점입니다.",
    "rate_control": "화질 또는 비트레이트를 제어하는 방식을 선택합니다.\n\n- CQP/CRF: 지정된 화질 수준(숫자)을 목표로 용량이 조절됩니다. (권장)\n- VBR/CBR: 지정된 비트레이트(용량)를 목표로 합니다. (업로드용)",
    "quality_value": "압축 품질을 설정합니다.\n\n- CQP/CRF의 경우 숫자가 낮을수록 고품질/고용량입니다. (추천: 24-28)\n- CBR/VBR의 경우 목표 비트레이트를 의미합니다. (예: 4M은 4Mbps)",
    "suffix": "변환된 파일의 원본 이름 뒤에 붙을 텍스트입니다.\n\n예: MyMovie.mp4 -> MyMovie_h265.mp4",
    "audio_option": "오디오 트랙의 처리 방식을 선택합니다.\n\n- 원본 유지 (Passthrough): 원본 오디오를 그대로 복사합니다. 가장 빠르고 음질 손실이 없습니다. (권장)\n- AAC ...kbps: 오디오를 지정된 비트레이트의 AAC 코덱으로 다시 인코딩합니다.",
    "output_format": "영상을 담을 파일 형식(컨테이너)을 선택합니다.\n\n- mp4: 가장 범용적이고 호환성이 높은 형식입니다.\n- mkv: 여러 개의 오디오/자막 트랙을 담을 수 있는 유연한 형식입니다.",
    "parallel_jobs": "동시에 몇 개의 파일을 변환할지 설정합니다.\n\n사용 중인 그래픽카드의 NVENC 엔진 수(하이엔드 모델은 2개)에 맞추는 것이 가장 효율적입니다."
}
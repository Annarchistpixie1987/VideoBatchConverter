# src/about_dialog.py
import base64
import logging
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, 
                             QPushButton, QDialogButtonBox, QStyle)
from PyQt6.QtGui import QPixmap, QDesktopServices, QIcon
from PyQt6.QtCore import QUrl, Qt

# --- 임포트 방식 수정 및 예외 처리 ---
try:
    from .icon import MAIN_ICON
except ImportError:
    MAIN_ICON = None
    logging.warning("'src/icon.py' 또는 'MAIN_ICON'을 찾을 수 없습니다. 아이콘이 표시되지 않습니다.")

class AboutDialog(QDialog):
    def __init__(self, version, parent=None):
        super().__init__(parent)
        self.setWindowTitle("VideoBatchConverter 정보")

        main_icon = QIcon()
        main_pixmap = QPixmap()
        
        if MAIN_ICON:
            try:
                icon_bytes = base64.b64decode(MAIN_ICON)
                main_pixmap.loadFromData(icon_bytes)
                main_icon = QIcon(main_pixmap)
                self.setWindowIcon(main_icon)
            except Exception as e:
                logging.error(f"메인 아이콘 로드 실패: {e}")
                self.setWindowIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon))
        else:
            self.setWindowIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon))

        main_layout = QVBoxLayout(self)
        header_layout = QHBoxLayout()
        icon_label = QLabel()
        
        if not main_pixmap.isNull():
            pixmap_scaled = main_pixmap.scaled(64, 64, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            icon_label.setPixmap(pixmap_scaled)
        
        title_layout = QVBoxLayout()
        title_label = QLabel(f"VideoBatchConverter {version}")
        title_label.setStyleSheet("font-weight: bold; font-size: 14pt;")
        info_label = QLabel("FFmpeg을 이용한 고효율 동영상 일괄 변환기")
        
        title_layout.addWidget(title_label)
        title_layout.addWidget(info_label)
        
        header_layout.addWidget(icon_label)
        header_layout.addLayout(title_layout)
        main_layout.addLayout(header_layout)

        feature_text = QTextEdit()
        feature_text.setReadOnly(True)
        feature_text.setHtml("""
            <h3 style="margin-bottom: 5px;">🚀 주요 기능</h3>
            <ul>
                <li>폴더 기반 H.264 동영상 일괄 변환</li>
                <li>NVIDIA(NVENC) GPU를 활용한 초고속 하드웨어 가속</li>
                <li>여러 파일을 동시에 변환하는 병렬 처리 기능</li>
                <li>Apple, YouTube 등 목적에 맞는 원클릭 프리셋 제공</li>
                <li>오디오 Passthrough로 음질 손실 없는 빠른 변환 지원</li>
                <li>FFmpeg 자동 다운로드 및 설정</li>
            </ul>
            <hr>
            <p>이 프로그램은 오픈소스인 FFmpeg을 기반으로 제작되었습니다.</p>
            <p>FFmpeg is a trademark of Fabrice Bellard.</p>
        """)
        main_layout.addWidget(feature_text)

        button_layout = QHBoxLayout()
        github_button = QPushButton("  GitHub 저장소 방문")
        github_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogNewFolder))
        github_button.clicked.connect(self.open_github)

        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        button_box.accepted.connect(self.accept)

        button_layout.addWidget(github_button)
        button_layout.addStretch()
        button_layout.addWidget(button_box)
        main_layout.addLayout(button_layout)
        
        self.setFixedSize(450, 400)

    def open_github(self):
        url = QUrl("https://github.com/deuxdoom/VideoBatchConverter/")
        QDesktopServices.openUrl(url)
# main.py
import sys
import os
import logging
import traceback
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import QCoreApplication

from src.logger_setup import setup_logging
import src.ui_mainwindow

def handle_exception(exc_type, exc_value, exc_traceback):
    """전역 예외 처리기: 처리되지 않은 모든 예외를 로깅합니다."""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    logging.critical("처리되지 않은 예외 발생 (Uncaught Exception):", exc_info=(exc_type, exc_value, exc_traceback))

    QMessageBox.critical(
        None, "치명적 오류 발생",
        f"예기치 않은 오류가 발생하여 프로그램을 종료해야 합니다.\n\n"
        f"자세한 내용은 'error.log' 파일을 확인해주세요.\n\n"
        f"오류 정보:\n{exc_value}"
    )

if __name__ == '__main__':
    setup_logging()
    sys.excepthook = handle_exception

    QCoreApplication.setOrganizationName("YourCompanyName")
    QCoreApplication.setApplicationName("VideoBatchConverter")

    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    window = src.ui_mainwindow.MainWindow()
    
    if window.is_initialized:
        window.show()
        sys.exit(app.exec())
    else:
        logging.warning("프로그램 초기화 실패로 종료됩니다.")
        sys.exit(-1)
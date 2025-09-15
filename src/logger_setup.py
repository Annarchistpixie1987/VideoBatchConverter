# src/logger_setup.py
import logging
import sys
import os
from logging.handlers import RotatingFileHandler

def setup_logging():
    if getattr(sys, 'frozen', False):
        log_path = os.path.dirname(sys.executable)
    else:
        log_path = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

    log_file = os.path.join(log_path, 'error.log')
    log_formatter = logging.Formatter('%(asctime)s [%(levelname)s] [%(name)s:%(lineno)d] - %(message)s')
    file_handler = RotatingFileHandler(log_file, maxBytes=5 * 1024 * 1024, backupCount=1, encoding='utf-8')
    file_handler.setFormatter(log_formatter)
    file_handler.setLevel(logging.INFO)
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)
    logging.info("="*50); logging.info("로깅 시스템이 시작되었습니다."); logging.info(f"로그 파일 위치: {log_file}"); logging.info("="*50)
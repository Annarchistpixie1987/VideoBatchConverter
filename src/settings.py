# src/settings.py
import os
from PyQt6.QtCore import QSettings, QCoreApplication

def get_settings_path():
    return os.path.join(QCoreApplication.applicationDirPath(), "settings.ini")

class SettingsManager:
    def __init__(self):
        self.settings = QSettings(get_settings_path(), QSettings.Format.IniFormat)

    def save_settings(self, settings_dict):
        for key, value in settings_dict.items():
            self.settings.setValue(key, value)

    def load_settings(self):
        return {
            "input_folder": self.settings.value("input_folder", "", type=str),
            "suffix": self.settings.value("suffix", "_h265", type=str),
            "codec": self.settings.value("codec", "H.265 (HEVC) - GPU", type=str),
            "resolution": self.settings.value("resolution", "원본 유지", type=str),
            "preset": self.settings.value("preset", "p5", type=str),
            "rate_control": self.settings.value("rate_control", "CQP", type=str),
            "quality_value": self.settings.value("quality_value", "28", type=str),
            "audio_option": self.settings.value("audio_option", "원본 유지 (Passthrough)", type=str),
            "output_format": self.settings.value("output_format", "mp4", type=str),
            "parallel_jobs": self.settings.value("parallel_jobs", 2, type=int),
            "geometry": self.settings.value("geometry"),
            "windowState": self.settings.value("windowState"),
        }
# src/update_checker.py
import requests
from PyQt6.QtCore import QThread, pyqtSignal

GITHUB_REPO_OWNER = "YourGitHubUsername"
GITHUB_REPO_NAME = "VideoBatchConverter"

class UpdateCheckWorker(QThread):
    finished = pyqtSignal(dict)
    def __init__(self, current_version):
        super().__init__(); self.current_version = current_version
        self.api_url = f"https://api.github.com/repos/{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}/releases/latest"
    def run(self):
        try:
            response = requests.get(self.api_url, timeout=5); response.raise_for_status()
            latest_release = response.json(); latest_version = latest_release.get("tag_name"); release_url = latest_release.get("html_url")
            if latest_version and self.is_newer(latest_version, self.current_version):
                self.finished.emit({"update": True, "version": latest_version, "url": release_url})
            else: self.finished.emit({"update": False})
        except requests.RequestException: self.finished.emit({"update": False})
    def is_newer(self, latest_v, current_v):
        latest = tuple(map(int, latest_v.lstrip('v').split('.'))); current = tuple(map(int, current_v.lstrip('v').split('.')))
        return latest > current
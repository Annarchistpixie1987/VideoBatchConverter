# README.md

# VideoBatchConverter

H.264로 인코딩된 동영상을 H.265, AV1 등 최신 고효율 코덱으로 일괄 변환하는 프로그램입니다. NVIDIA GPU(NVENC)를 활용한 빠른 하드웨어 가속 인코딩을 지원합니다.

![Screenshot](link_to_your_screenshot.png) ## 주요 기능

-   폴더 및 하위 폴더의 모든 H.264 영상 자동 감지
-   **하드웨어 가속:** NVIDIA (NVENC)를 사용한 H.265/AV1 초고속 인코딩
-   다양한 인코딩 옵션 설정 (해상도, 품질/비트레이트, GPU 프리셋)
-   작업 진행 상황 실시간 모니터링
-   자동 업데이트 확인 기능

## 다운로드 및 설치 (사용자용)

1.  **[GitHub Releases 페이지](link_to_your_releases_page)**로 이동합니다. 2.  최신 버전의 `VideoBatchConverter-vX.X.X.zip` 파일을 다운로드합니다.
3.  압축을 풀고 `VideoBatchConverter.exe`를 실행합니다.

## 소스 코드로 빌드하기 (개발자용)

### 사전 준비

-   Python 3.8 이상
-   Git

### 빌드 절차

1.  저장소 복제:
    ```bash
    git clone [https://github.com/YourGitHubUsername/VideoBatchConverter.git](https://github.com/YourGitHubUsername/VideoBatchConverter.git)
    cd VideoBatchConverter
    ```

2.  가상 환경 생성 및 활성화:
    ```bash
    python -m venv venv
    .\venv\Scripts\activate
    ```

3.  필요한 라이브러리 설치:
    ```bash
    pip install PyQt6 requests pyinstaller
    ```

4.  `assets/ffmpeg` 폴더에 `ffmpeg.exe`와 `ffprobe.exe`를配置합니다.

5.  PyInstaller로 빌드:
    ```bash
    pyinstaller main.py --name VideoBatchConverter --windowed --onefile --icon="assets/icon.ico" --add-data="assets;assets"
    ```

## 라이선스

이 프로젝트는 [MIT License](LICENSE)에 따라 배포됩니다. 개인적, 상업적 용도로 자유롭게 사용 가능합니다.
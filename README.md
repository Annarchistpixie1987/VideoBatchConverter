# 🎬 VideoBatchConverter v1.8.0

**H.264 동영상을 H.265, AV1 등 최신 고효율 코덱으로 초고속 변환하는 GUI 프로그램입니다.**

![GitHub](https://img.shields.io/github/license/deuxdoom/VideoBatchConverter)
![GitHub release (latest by date)](https://img.shields.io/github/v/release/deuxdoom/VideoBatchConverter)
![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![Platform](https://img.shields.io/badge/platform-windows-lightgrey.svg)

---

![VideoBatchConverter Screenshot](https://github.com/deuxdoom/VideoBatchConverter/blob/main/screenshot.png) 
## ✨ 소개 (Introduction)

오래된 H.264(AVC) 코덱으로 인코딩된 수많은 동영상 파일들을 최신 고효율 코덱으로 간편하게 변환하여 저장 공간을 절약하고 스트리밍 효율을 높일 수 있도록 설계되었습니다. 특히 NVIDIA 그래픽카드(RTX 시리즈)의 **NVENC 듀얼 인코더**를 최대한 활용하는 **병렬 처리** 기능을 통해 압도적인 변환 속도를 경험할 수 있습니다.

## 🚀 주요 기능 (Key Features)

-   📂 **폴더 기반 일괄 변환**: 지정된 폴더 및 모든 하위 폴더의 H.264 영상을 자동으로 찾아 변환합니다.
-   ⚡️ **초고속 GPU 가속**: NVIDIA (NVENC)를 사용한 H.265/AV1 하드웨어 인코딩을 완벽 지원합니다.
-   ⛓️ **병렬 처리**: 듀얼 NVENC 엔진을 탑재한 GPU의 성능을 극대화하기 위해 여러 파일을 동시에 변환합니다.
-   🎯 **원클릭 프리셋**: 'Apple 기기', 'YouTube 업로드' 등 사용 목적에 맞는 최적의 설정을 한번의 클릭으로 적용할 수 있습니다.
-   ⚙️ **상세한 옵션 제어**: 코덱, 해상도, 품질(CQP/CRF), GPU 프리셋, 오디오(Passthrough) 등 전문가 수준의 세부 설정이 가능합니다.
-   📥 **FFmpeg 자동 설치**: 프로그램 첫 실행 시, 번거로운 FFmpeg 설치 과정 없이 자동으로 최신 버전을 다운로드하고 설정합니다.
-   🔄 **자동 업데이트 알림**: GitHub에 새로운 버전이 릴리즈되면 프로그램 시작 시 알려줍니다.
-   📝 **설정 저장**: 마지막으로 사용한 폴더, 프리셋, 세부 옵션, 창 위치까지 모두 기억하여 다음 실행 시 복원합니다.

## 📦 다운로드 및 설치 (Download & Installation)

1.  **[GitHub Releases 페이지](https://github.com/deuxdoom/VideoBatchConverter/releases)**로 이동합니다.
2.  `Assets` 목록에서 최신 버전의 `VideoBatchConverter-vX.X.X.zip` 파일을 다운로드합니다.
3.  원하는 위치에 압축을 풀고 `VideoBatchConverter.exe`를 실행합니다.
    > 第一次 실행 시 FFmpeg이 자동으로 다운로드됩니다. (약 80MB)

## 📖 사용 방법 (How to Use)

1.  **프리셋 선택**: 가장 먼저 자신의 사용 목적에 맞는 프리셋을 선택합니다. (기본값: 일반용)
2.  **대상 폴더 설정**: 변환할 H.264 영상들이 들어있는 최상위 폴더를 지정합니다.
3.  **세부 설정 (선택 사항)**: 프리셋으로 자동 변경된 설정을 필요에 따라 미세 조정할 수 있습니다. (이 경우 프리셋은 '사용자 정의'로 변경됩니다.)
4.  **변환 시작**: '변환 시작' 버튼을 누르면 작업이 시작됩니다. 변환된 파일은 원본 파일과 같은 위치에 `_h265` 와 같은 접미사가 붙어 저장됩니다.

## 🎯 프리셋 설명 (Presets)

| 프리셋 이름 | 주요 목적 | 비디오 설정 | 오디오 설정 |
| :--- | :--- | :--- | :--- |
| **일반용 / 아카이빙** | 개인 소장용 (PC, TV). 품질과 용량의 균형 | H.265, 원본 해상도, CQP 28 | 원본 유지 (Passthrough) |
| **Apple 기기 호환** | 아이폰, 애플TV Plex 스트리밍 (Direct Play) | H.265, 최대 1080p, CQP 24 | 원본 유지 (Passthrough) |
| **YouTube 업로드 (1080p)**| YouTube 1080p 권장 사양 충족 | H.265, 1080p, VBR 10Mbps | AAC 192kbps |
| **YouTube 업로드 (720p)** | YouTube 720p 권장 사양 충족 | H.265, 720p, VBR 6Mbps | AAC 192kbps |

## 📜 라이선스 (License)

이 프로젝트는 [MIT License](LICENSE)에 따라 배포됩니다. 개인적, 상업적 용도로 자유롭게 사용 가능합니다.
# 🎬 VideoBatchConverter v2.0.0

**H.264 동영상을 H.265, AV1 등 최신 고효율 코덱으로 초고속 일괄 변환하는 GUI 프로그램입니다.**

![GitHub](https://img.shields.io/github/license/deuxdoom/VideoBatchConverter)
![GitHub release (latest by date)](https://img.shields.io/github/v/release/deuxdoom/VideoBatchConverter)
![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![Platform](https://img.shields.io/badge/platform-windows-lightgrey.svg)

---

![VideoBatchConverter Screenshot](httpsd://raw.githubusercontent.com/deuxdoom/VideoBatchConverter/main/screenshot.png) 

## ✨ 소개 (Introduction)

단순한 변환기를 넘어, 사용자가 변환 대상을 유연하게 관리할 수 있는 강력한 **큐(Queue) 기반의 전문적인 툴**로 발전했습니다. 폴더 내의 수많은 H.264 영상들을 최신 코덱으로 손쉽게 변환하여 저장 공간을 절약하고 스트리밍 효율을 높이세요. 특히 NVIDIA GPU의 **듀얼 NVENC 엔진**을 최대한 활용하는 병렬 처리 기능으로 압도적인 변환 속도를 경험할 수 있습니다.

## 🚀 주요 기능 (Key Features)

-   🗂️ **동적 파일 큐 관리**: 파일/폴더 추가, 선택 삭제, 목록 비우기 등 변환 대상을 자유롭게 구성할 수 있습니다.
-   🖐️ **드래그 앤 드롭**: 탐색기에서 파일이나 폴더를 창 위로 끌어다 놓아 변환 목록에 바로 추가할 수 있습니다.
-   🎯 **아이콘 툴바 프리셋**: 사용 목적(일반용, Apple, Android, YouTube)에 맞는 최적의 설정을 아이콘 클릭 한 번으로 적용합니다.
-   ℹ️ **실시간 파일 정보**: 목록에서 파일을 선택하면 해당 파일의 코덱, 해상도, 비트레이트 등 상세 정보를 바로 확인할 수 있습니다.
-   ⚡️ **초고속 GPU 가속**: NVIDIA (NVENC)를 사용한 H.265/AV1 하드웨어 인코딩을 지원합니다.
-   ⛓️ **병렬 처리**: 여러 파일을 동시에 변환하여 하이엔드 GPU의 성능을 극대화합니다. (동시 작업 수 조절 가능)
-   ⚙️ **상세 옵션 제어**: 해상도, 품질(CQP/CRF), GPU 프리셋, 오디오(Passthrough) 등 전문가 수준의 세부 설정이 가능합니다.
-   📥 **FFmpeg 자동 설치**: 프로그램 첫 실행 시 FFmpeg을 자동으로 다운로드하여 별도의 사용자 설정이 필요 없습니다.
-   🔄 **자동 업데이트 알림**: GitHub에 새로운 버전이 릴리즈되면 프로그램 시작 시 알려줍니다.
-   📝 **설정 및 창 위치 저장**: 마지막으로 사용했던 모든 설정과 창의 위치 및 크기를 기억하여 다음 실행 시 복원합니다.

## 📦 다운로드 및 설치 (Download & Installation)

1.  **[GitHub Releases 페이지](https://github.com/deuxdoom/VideoBatchConverter/releases)**로 이동합니다.
2.  `Assets` 목록에서 최신 버전의 `VideoBatchConverter-v2.0.0.zip` 파일을 다운로드합니다.
3.  원하는 위치에 압축을 풀고 `VideoBatchConverter.exe`를 실행합니다.
    > 第一次 실행 시 FFmpeg이 자동으로 다운로드됩니다. (약 80MB)

## 📖 사용 방법 (How to Use)

1.  **파일/폴더 추가**: `폴더 선택...` 버튼, `폴더 추가`, `파일 추가` 버튼 또는 **드래그 앤 드롭**으로 변환할 H.264 파일들을 좌측 '변환 목록'에 추가합니다.
2.  **프리셋 선택**: 상단 툴바에서 원하는 사용 목적의 아이콘(예: Apple 기기)을 클릭합니다. 우측의 세부 설정이 자동으로 변경됩니다.
3.  **(선택) 세부 설정**: 필요에 따라 우측 '세부 설정' 패널에서 개별 옵션을 미세 조정합니다. (이 경우 툴바의 프리셋 선택이 해제됩니다.)
4.  **(선택) 변환 대상 선택**: 좌측 '변환 목록'에서 특정 파일만 클릭하여 선택하면, 선택된 파일들만 변환을 진행합니다. (아무것도 선택하지 않으면 목록 전체를 변환합니다.)
5.  **변환 시작**: '변환 시작' 버튼을 누릅니다. 변환된 파일은 원본 파일과 같은 위치에 `_h265` 와 같은 접미사가 붙어 저장됩니다.

## 🎯 프리셋 설명 (Presets)

| 프리셋 이름 | 주요 목적 | 비디오 설정 | 오디오 설정 |
| :--- | :--- | :--- | :--- |
| **일반용 / 아카이빙** | 개인 소장용 (PC, TV). 품질과 용량의 균형 | H.265, 원본 해상도, CQP 28 | 원본 유지 (Passthrough) |
| **Apple 기기 호환 (AV1)** | 최신 Apple 기기(iPhone 15 Pro 등) 스트리밍 | **AV1**, 1080p, CQP 29 | 원본 유지 (Passthrough) |
| **Android 기기 호환 (VP9)** | 대부분의 Android 기기 스트리밍 (Google 표준) | **VP9 (CPU)**, 1080p, CRF 31 | 원본 유지 (Passthrough) |
| **YouTube 업로드 (1080p)**| YouTube 1080p 권장 사양 충족 | H.265, 1080p, VBR 10Mbps | AAC 192kbps |
| **YouTube 업로드 (720p)** | YouTube 720p 권장 사양 충족 | H.265, 720p, VBR 6Mbps | AAC 192kbps |

## 📜 라이선스 (License)

이 프로젝트는 [MIT License](LICENSE)에 따라 배포됩니다. 개인적, 상업적 용도로 자유롭게 사용 가능합니다.
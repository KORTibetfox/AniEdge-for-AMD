# 외부 구성 요소

루트 MIT 라이선스는 AniEdge for AMD의 자체 작성 코드에 적용됩니다. 아래 외부 파일은 각 원본의 저작권·라이선스를 유지합니다. 파일 출처와 해시는 `vendor/sources.json`, 설치 대상은 `assets-manifest.json`에 있습니다.

| 구성 요소 | 출처 | 라이선스 / 배포 |
|---|---|---|
| Anime4K GLSL 셰이더 | https://github.com/bloc97/Anime4K | MIT, `vendor/licenses/Anime4K-MIT.txt` |
| ArtCNN GLSL 셰이더 및 Native 파생본 | https://github.com/Artoriuz/ArtCNN | MIT, `vendor/licenses/ArtCNN-MIT.txt` 및 파일 머리말 |
| Real-CUGAN 원본 모델 | https://github.com/bilibili/ailab/tree/main/Real-CUGAN | 원본 MIT, `vendor/licenses/Real-CUGAN-LICENSE.txt` |
| Real-CUGAN Pro ONNX 내보내기 | https://github.com/AmusementClub/vs-mlrt/releases/tag/model-20211209 | upstream GPL-3.0 사본 유지: `vendor/licenses/vs-mlrt-LICENSE.txt`; 원본 ONNX 및 변환 스크립트 제공 |
| mpv Windows CI 빌드 | https://github.com/mpv-player/mpv | 설치 시 공식 배포에서 다운로드. 실행 파일은 이 릴리스 ZIP에 재배포하지 않음. Copyright 및 LGPL 문서 사본 포함 |
| ONNX Runtime DirectML | https://github.com/microsoft/onnxruntime | 설치 시 PyPI에서 다운로드, upstream MIT |
| NumPy / Pillow 및 Python | 각 공식 프로젝트 | 설치 환경에 준비하며 원본 라이선스 적용 |

Real-CUGAN 파생 ONNX는 FP16 또는 FP32 코어에 GPU RGB8 전후처리를 덧붙였습니다. 원본 ONNX와 build_optimized_model.py를 함께 제공해 변환을 재현할 수 있습니다. 외부 모델·변환 파일에 루트 MIT 라이선스만을 일괄 적용하지 않습니다.

mpv 설치 대상은 개발 CI 빌드 `v0.41.0-dev-g36abaa32d`입니다. upstream [소스](https://github.com/mpv-player/mpv)와 해당 빌드의 라이선스가 적용됩니다. mpv의 업스트림 의존성과 빌드 설정은 해당 프로젝트에서 확인하세요. 공개 테스트 영상과 추출 프레임은 포함하지 않습니다.

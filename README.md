# AniEdge for AMD

Windows용 로컬 애니메이션 복원 플레이어입니다. **HQ — Real-CUGAN Pro FP16 ×2**만 사용하며 RX 9070 XT의 DirectML 추론으로 재생합니다. 현재 버전은 **0.1.1-preview.2**입니다.

## 실행

1. [HQ 전용 릴리스](https://github.com/KORTibetfox/AniEdge-for-AMD/releases/tag/v0.1.1-preview.2)에서 `AniEdge-for-AMD-v0.1.1-preview.2-windows-x64.zip`을 다운로드하고 새 폴더에 압축을 풉니다.
2. Python 3.12 64비트(tkinter·pip 포함)를 준비하고 처음 한 번 `setup.cmd`를 실행합니다.
3. `start.cmd`를 실행합니다.
4. MP4 또는 MKV를 선택하고 **재생**을 누릅니다. 모델이나 모드를 선택할 필요가 없습니다.

기존 설치 환경은 그대로 사용할 수 있습니다. Python 경로를 지정하려면 `powershell -NoProfile -ExecutionPolicy Bypass -File .\setup.ps1 -PythonPath 'D:\Python312\python.exe'`를 실행하세요.

설치 시 GitHub와 PyPI에서 mpv·모델·Python 의존성을 다운로드하고 SHA256을 확인합니다. 실행 ZIP에는 Real-CUGAN 모델이 포함되어 모델 다운로드가 생략됩니다. 소스 설치는 가중치가 동일한 기존 모델 묶음을 사용합니다. 완전 독립 실행 EXE 패키지는 아닙니다. 이전 `v0.1.0-preview.1`은 다중 모드 버전이므로 HQ 전용 설치에는 위 릴리스를 사용하세요.

## 지원 범위

- 짝수 폭·높이, 720p 상당 이하(1280×720 이하의 픽셀 수), 1~60fps CFR 영상.
- 권장 입력: **480p 이하·30fps 이하**. 720p·고FPS에서는 실시간 속도가 부족할 수 있습니다.
- 정사각 픽셀·회전 없는 입력. VFR·인터레이스 처리는 지원하지 않습니다.
- Space 일시정지, F 전체화면, I 통계, Q 종료.
- 순차 재생만 지원하며 시간 탐색은 지원하지 않습니다.
- 원본과 같은 이름의 외부 SRT/ASS/SSA 자막을 연결합니다. 내장 자막·다중 음성 트랙 선택은 지원하지 않습니다.

지원 범위를 넘으면 오류로 종료하며 다른 모델로 전환하지 않습니다. 원본 영상은 변경하지 않으며 업로드 기능도 없습니다. 실행 로그에는 로컬 경로가 기록됩니다.

## RX 9070 XT 최적화

Real-CUGAN Pro conservative ×2의 기존 가중치에 FP16 변환, RGB8 전처리·후처리 GPU 통합, 입력 크기 고정, DXGI 장치 선택을 적용했습니다. GPU CPU fallback은 금지합니다. 디코딩과 RGB 입출력 복사는 CPU 경로에 남아 있습니다. 가중치를 재학습한 상태는 아닙니다.

기존 640×480 프레임 60개 검사에서 처리량은 28.39 → 89.11fps, 처리 p95는 11.39ms였습니다. 모델 처리량은 전체 재생 FPS와 다릅니다. FP32 대비 정밀도 검사 수치도 원본 대비 복원 화질 점수가 아닙니다.

이번 버전은 실제 360p·480p 영상 6개를 각각 10초씩 음성 포함 재생해 오류·렌더러 드롭·디코더 드롭 0을 확인했습니다. FPS 조회 종료 시 유효한 값이 0으로 바뀌던 문제를 수정하고, 문제가 있던 영상의 조회를 10회 반복 검증했습니다. 재생 창 정상 종료도 확인했습니다. 결과는 `VALIDATION.json`에 있습니다. 전체 에피소드의 장시간 안정성 검증은 아닙니다.

실패하면 화면에 실제 원인이 표시됩니다. 해당 재생의 `logs/hq-*/error.json`, `error.txt`, `probe.log`를 확인하세요. 파일명에 480·720이 들어가더라도 실제 해상도가 지원 범위를 넘으면 재생할 수 없습니다.

## 개발 자료

- [구조와 재현](docs/ARCHITECTURE.md)
- [진행 상황](docs/PROGRESS.md)
- [이전 버전 측정 기록](docs/benchmarks/REPORT.md)
- [변경 기록](CHANGELOG.md)
- [외부 구성 요소](THIRD_PARTY_NOTICES.md)

FP32 원본·비교 모델과 변환·정밀도 측정 도구는 HQ 개발 자료로 보관합니다. 재생 프로그램은 FP16 모델 하나만 사용합니다. 자체 작성 코드에는 MIT, 외부 모델·변환 파일·런타임에는 각 원본 라이선스가 적용됩니다. AMD와 공식 제휴한 제품은 아닙니다.

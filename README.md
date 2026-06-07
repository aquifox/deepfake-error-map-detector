# Deepfake Error Map Detector Extension

기존에 학습한 CNN AutoEncoder Error Map 기반 딥페이크 탐지 모델을 웹페이지 이미지 분석용 Chrome 확장 프로그램으로 연결한 프로젝트입니다.

이 프로젝트는 **확정 판정 도구가 아니라 참고용 AI 분석 도구**입니다. 결과를 법적 증거, 사실 확정, 인물 진위 판정으로 사용하지 마세요.

## 핵심 구조

```text
Web page image
  -> Chrome extension
  -> localhost FastAPI server
  -> CNN AutoEncoder reconstruction
  -> Error Map = abs(input - reconstruction)
  -> ResNet18 classifier
  -> real/fake probability
  -> badge on image
```

## Repository Layout

```text
.
├─ chrome-extension/
│  ├─ manifest.json
│  ├─ popup.html
│  ├─ popup.js
│  ├─ content.js
│  ├─ service_worker.js
│  └─ style.css
├─ models/
│  ├─ label_map.json
│  └─ put .pth files here
├─ scripts/
│  ├─ run_server.ps1
│  └─ smoke_test.py
├─ inference.py
├─ server.py
├─ requirements.txt
├─ train_deepfake_detector_colab.ipynb
├─ PRIVACY.md
├─ MODEL_ARTIFACTS.md
└─ README.md
```

## 준비물

- Python 3.10 이상 권장
- Chrome 또는 Chromium 기반 브라우저
- 학습된 모델 가중치 파일

모델 가중치는 GitHub 저장소에 직접 올리지 않는 것을 권장합니다. 용량이 크고 재학습 결과물이기 때문에 GitHub Releases, Google Drive, Hugging Face Hub 같은 별도 경로로 배포하세요.

필요한 모델 파일:

```text
models/deepfake_detector_full.pth
```

또는 split weight 방식:

```text
models/ae_weights.pth
models/classifier_weights.pth
models/label_map.json
```

## 설치

```bash
git clone https://github.com/aquifox/deepfake-error-map-detector.git
cd deepfake-error-map-detector
python -m pip install -r requirements.txt
```

Colab에서 받은 `deepfake_detector_full.pth`를 `models/` 폴더에 넣습니다.

```text
models/deepfake_detector_full.pth
```

## 로컬 서버 실행

Windows PowerShell:

```powershell
.\scripts\run_server.ps1
```

직접 실행:

```bash
python server.py --weights models/deepfake_detector_full.pth --label-map models/label_map.json
```

정상 실행되면 다음 주소에서 서버 상태를 확인할 수 있습니다.

```text
http://127.0.0.1:8000/health
```

`"status":"ready"`가 보이면 준비 완료입니다.

## 단일 이미지 추론

```bash
python inference.py --image samples/example.jpg --weights models/deepfake_detector_full.pth --label-map models/label_map.json --pretty
```

출력 예시:

```json
{
  "label": "fake",
  "confidence": 0.83,
  "real_probability": 0.17,
  "fake_probability": 0.83,
  "fake_threshold": 0.5,
  "note": "AI analysis result for reference only; not legal or factual proof."
}
```

## Chrome 확장 프로그램 로드

1. Chrome 주소창에 `chrome://extensions` 입력
2. 오른쪽 위 `개발자 모드` 켜기
3. `압축해제된 확장 프로그램을 로드` 클릭
4. 이 저장소의 `chrome-extension/` 폴더 선택
5. 로컬 서버가 켜져 있는지 확인
6. 웹페이지에서 확장 프로그램 버튼 클릭
7. `현재 페이지 이미지 분석` 클릭

확장 프로그램은 웹페이지의 `img` 태그 이미지를 탐색하고, 분석 가능한 이미지를 localhost 서버로 보낸 뒤 이미지 위에 결과 배지를 표시합니다.

표시 문구:

- fake probability가 높음: `딥페이크 의심`
- fake probability가 낮음: `REAL 가능성 높음`
- 항상 `AI 분석 결과 참고용` 문구 표시

## Colab 재학습

`train_deepfake_detector_colab.ipynb`는 Google Drive의 `Dataset.zip`을 사용해 모델을 재학습하는 노트북입니다.

기본 경로:

```text
/content/drive/MyDrive/Dataset.zip
```

학습이 끝나면 다음 파일이 생성됩니다.

```text
ae_weights.pth
classifier_weights.pth
deepfake_detector_full.pth
label_map.json
inference.py
```

이 중 `deepfake_detector_full.pth` 또는 split weight 파일을 `models/`에 넣으면 로컬 서버와 확장 프로그램에서 사용할 수 있습니다.

## 정보 윤리와 개인정보 보호

- 이 확장 프로그램은 기본적으로 이미지를 외부 서버로 보내지 않습니다.
- 분석 대상 이미지는 `http://127.0.0.1:8000/predict` 로컬 서버로만 전송됩니다.
- 결과는 확률적 AI 판단이며 사실 확정이 아닙니다.
- 민감한 이미지나 타인의 개인정보가 포함된 이미지는 분석 전 사용자가 직접 주의해야 합니다.

## 한계

- 정지 이미지 기반 모델입니다. 영상의 시간적 일관성, 음성과 입 모양 불일치 등은 분석하지 못합니다.
- 학습 데이터 분포와 다른 이미지에서는 성능이 떨어질 수 있습니다.
- 오탐이 존재합니다. 특히 real 이미지를 fake로 의심할 수 있습니다.
- 공개 서비스로 사용하기 전에는 별도 검증, 개인정보 검토, 오탐 안내 문구 보강이 필요합니다.

## License

MIT License. 자세한 내용은 `LICENSE`를 참고하세요.

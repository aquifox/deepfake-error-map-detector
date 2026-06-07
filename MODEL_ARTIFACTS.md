# Model Artifacts

이 저장소는 GitHub 본문에 큰 `.pth` 모델 가중치를 직접 커밋하지 않고, GitHub Releases를 통해 모델 파일을 제공합니다.

## 현재 제공되는 데모 가중치

- Release: [v0.1.0-model](https://github.com/aquifox/deepfake-error-map-detector/releases/tag/v0.1.0-model)
- File: [deepfake_detector_full.pth](https://github.com/aquifox/deepfake-error-map-detector/releases/download/v0.1.0-model/deepfake_detector_full.pth)
- Size: 약 49 MB
- SHA256: `a8f3f2e3a4686fb50a111882b9eb23468f962ff37c34e5dfacfe8ab63fcb20b5`

다운로드한 파일은 아래 위치에 두면 됩니다.

```text
models/deepfake_detector_full.pth
```

Windows PowerShell 예시:

```powershell
New-Item -ItemType Directory -Force models | Out-Null
Invoke-WebRequest -Uri "https://github.com/aquifox/deepfake-error-map-detector/releases/download/v0.1.0-model/deepfake_detector_full.pth" -OutFile "models/deepfake_detector_full.pth"
```

파일 검증 예시:

```powershell
Get-FileHash .\models\deepfake_detector_full.pth -Algorithm SHA256
```

출력된 해시가 위 SHA256 값과 같으면 정상적으로 받은 것입니다.

## 필요한 파일

권장 방식:

```text
models/deepfake_detector_full.pth
models/label_map.json
```

대체 방식:

```text
models/ae_weights.pth
models/classifier_weights.pth
models/label_map.json
```

현재 릴리즈에는 `deepfake_detector_full.pth`만 제공됩니다. split weight 방식으로 실행하려면 Colab 재학습 결과에서 `ae_weights.pth`, `classifier_weights.pth`를 따로 내려받아 `models/` 폴더에 넣으면 됩니다.

## 모델 성능 예시

현재 학습 결과 예시:

```text
test accuracy: 0.8974
test f1-score: 0.8966
fake precision: 0.8445
fake recall: 0.9760
confusion matrix:
[[4426,  987],
 [ 132, 5360]]
```

이 성능은 사용한 데이터셋 기준입니다. 다른 웹 이미지, 다른 생성 모델, 다른 압축 환경에서는 달라질 수 있습니다. 특히 fake recall이 높은 대신 real 이미지를 fake로 의심하는 오탐이 생길 수 있으므로 결과는 참고용으로만 해석해야 합니다.

# Colab Retraining Guide

이 저장소의 핵심 배포 대상은 로컬 추론 서버와 Chrome 확장 프로그램입니다. 모델을 다시 학습하려면 Colab에서 기존 학습 노트북을 실행해 아래 파일을 생성한 뒤 `models/` 폴더에 넣어 사용합니다.

## Dataset

기본 데이터셋 위치:

```text
/content/drive/MyDrive/Dataset.zip
```

데이터셋 구조는 자동 탐색을 전제로 합니다.

- `train/val/test` 폴더가 있으면 그대로 사용
- 없으면 전체 이미지를 train/val/test로 자동 분할
- real/fake 라벨은 파일 경로 키워드로 추론

라벨 키워드 예시:

```text
real: real, genuine, authentic
fake: fake, synthesized, synthetic, deepfake
```

## Model

학습 구조:

```text
RGB image
  -> CNN AutoEncoder
  -> reconstruction
  -> Error Map = abs(input - reconstruction)
  -> ResNet18 classifier
  -> REAL / FAKE
```

학습 손실:

```text
total_loss = ae_loss_weight * MSE(reconstruction, input) + classifier_loss_weight * CE(logits, label)
```

## Output Artifacts

Colab 학습 후 다음 파일을 다운로드합니다.

```text
ae_weights.pth
classifier_weights.pth
deepfake_detector_full.pth
label_map.json
inference.py
```

GitHub repo에서 실행하려면 보통 아래 파일만 있으면 됩니다.

```text
models/deepfake_detector_full.pth
models/label_map.json
```

## Colab Stability Note

Colab/Jupyter 환경에서는 `DataLoader(num_workers > 0)`가 multiprocessing cleanup 오류를 낼 수 있습니다. 안정성을 위해 기본값을 아래처럼 두는 것을 권장합니다.

```python
CONFIG["num_workers"] = 0
```

## Recommended Distribution

큰 `.pth` 파일은 GitHub 저장소에 직접 커밋하지 말고 GitHub Releases, Google Drive, Hugging Face Hub 등으로 배포하세요.

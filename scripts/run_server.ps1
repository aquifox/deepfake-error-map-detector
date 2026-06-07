$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $repoRoot

$fullWeights = Join-Path $repoRoot "models\deepfake_detector_full.pth"
$aeWeights = Join-Path $repoRoot "models\ae_weights.pth"
$classifierWeights = Join-Path $repoRoot "models\classifier_weights.pth"
$labelMap = Join-Path $repoRoot "models\label_map.json"

if (-not (Test-Path -LiteralPath $labelMap)) {
  throw "models\label_map.json not found."
}

if (Test-Path -LiteralPath $fullWeights) {
  python server.py --weights $fullWeights --label-map $labelMap
} elseif ((Test-Path -LiteralPath $aeWeights) -and (Test-Path -LiteralPath $classifierWeights)) {
  python server.py --ae-weights $aeWeights --classifier-weights $classifierWeights --label-map $labelMap
} else {
  throw "No model weights found. Put deepfake_detector_full.pth or split weights in models\."
}

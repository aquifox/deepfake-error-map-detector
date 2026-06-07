const SERVER_ORIGIN = "http://127.0.0.1:8000";
const MAX_IMAGE_BYTES = 12 * 1024 * 1024;

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message?.type === "DEEPFAKE_HEALTH") {
    handleHealth().then(sendResponse);
    return true;
  }

  if (message?.type === "DEEPFAKE_ANALYZE_IMAGE") {
    handleAnalyzeImage(message).then(sendResponse);
    return true;
  }

  return false;
});

async function handleHealth() {
  try {
    const response = await fetch(`${SERVER_ORIGIN}/health`, {
      method: "GET",
      cache: "no-store",
    });
    const data = await response.json();
    if (!response.ok) {
      return { ok: false, error: data?.detail || response.statusText };
    }
    return { ok: true, data };
  } catch (error) {
    return {
      ok: false,
      error: "localhost 추론 서버에 연결할 수 없습니다. server.py가 실행 중인지 확인하세요.",
    };
  }
}

async function handleAnalyzeImage(message) {
  try {
    const blob = await loadImageBlob(message.src);
    if (blob.size > MAX_IMAGE_BYTES) {
      throw new Error("이미지 파일이 너무 큽니다.");
    }
    const data = await sendImageToLocalServer(blob, message.src);
    return { ok: true, data };
  } catch (error) {
    return { ok: false, error: error.message };
  }
}

async function loadImageBlob(src) {
  if (!src || typeof src !== "string") {
    throw new Error("이미지 주소가 비어 있습니다.");
  }

  if (src.startsWith("data:image/")) {
    const response = await fetch(src);
    const blob = await response.blob();
    return blob;
  }

  if (src.startsWith("blob:")) {
    throw new Error("blob: 이미지는 보안상 확장 프로그램 백그라운드에서 직접 읽을 수 없습니다.");
  }

  const url = new URL(src);
  if (url.protocol !== "http:" && url.protocol !== "https:") {
    throw new Error(`지원하지 않는 이미지 URL 형식입니다: ${url.protocol}`);
  }

  const response = await fetch(url.href, {
    method: "GET",
    credentials: "omit",
    cache: "no-store",
    redirect: "follow",
  });

  if (!response.ok) {
    throw new Error(`이미지 다운로드 실패: HTTP ${response.status}`);
  }

  const blob = await response.blob();
  if (blob.type && !blob.type.startsWith("image/")) {
    throw new Error(`이미지 콘텐츠가 아닙니다: ${blob.type}`);
  }
  return blob;
}

async function sendImageToLocalServer(blob, src) {
  const formData = new FormData();
  const extension = guessExtension(blob.type);
  formData.append("file", blob, `page-image.${extension}`);

  const response = await fetch(`${SERVER_ORIGIN}/predict`, {
    method: "POST",
    body: formData,
  });

  let data = null;
  try {
    data = await response.json();
  } catch (error) {
    data = null;
  }

  if (!response.ok) {
    const detail = data?.detail || response.statusText || "분석 서버 오류";
    throw new Error(detail);
  }
  return data;
}

function guessExtension(contentType) {
  if (contentType === "image/png") {
    return "png";
  }
  if (contentType === "image/webp") {
    return "webp";
  }
  if (contentType === "image/gif") {
    return "gif";
  }
  return "jpg";
}

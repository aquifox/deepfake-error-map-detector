const analyzeButton = document.getElementById("analyzeButton");
const checkServerButton = document.getElementById("checkServerButton");
const serverStatus = document.getElementById("serverStatus");

function setStatus(message, tone = "neutral") {
  serverStatus.textContent = message;
  serverStatus.dataset.tone = tone;
}

function sendRuntimeMessage(message) {
  return new Promise((resolve, reject) => {
    chrome.runtime.sendMessage(message, (response) => {
      const error = chrome.runtime.lastError;
      if (error) {
        reject(new Error(error.message));
        return;
      }
      resolve(response);
    });
  });
}

function getActiveTab() {
  return new Promise((resolve, reject) => {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      const error = chrome.runtime.lastError;
      if (error) {
        reject(new Error(error.message));
        return;
      }
      if (!tabs || !tabs[0]?.id) {
        reject(new Error("활성 탭을 찾을 수 없습니다."));
        return;
      }
      resolve(tabs[0]);
    });
  });
}

function sendTabMessage(tabId, message) {
  return new Promise((resolve, reject) => {
    chrome.tabs.sendMessage(tabId, message, (response) => {
      const error = chrome.runtime.lastError;
      if (error) {
        reject(new Error(error.message));
        return;
      }
      resolve(response);
    });
  });
}

function injectContentScript(tabId) {
  return Promise.all([
    chrome.scripting.insertCSS({
      target: { tabId },
      files: ["style.css"],
    }),
    chrome.scripting.executeScript({
      target: { tabId },
      files: ["content.js"],
    }),
  ]);
}

async function sendAnalyzeCommand(tabId) {
  try {
    return await sendTabMessage(tabId, { type: "DEEPFAKE_ANALYZE_PAGE" });
  } catch (firstError) {
    await injectContentScript(tabId);
    return sendTabMessage(tabId, { type: "DEEPFAKE_ANALYZE_PAGE" });
  }
}

async function checkServer() {
  setStatus("서버 확인 중...", "neutral");
  try {
    const response = await sendRuntimeMessage({ type: "DEEPFAKE_HEALTH" });
    if (response?.ok) {
      const device = response.data?.runtime?.device || "unknown";
      setStatus(`서버 준비 완료 · device=${device}`, "ok");
    } else {
      setStatus(response?.error || "서버 응답을 확인할 수 없습니다.", "error");
    }
  } catch (error) {
    setStatus(`서버 연결 실패: ${error.message}`, "error");
  }
}

checkServerButton.addEventListener("click", checkServer);

analyzeButton.addEventListener("click", async () => {
  analyzeButton.disabled = true;
  setStatus("현재 페이지 이미지 분석 요청 중...", "neutral");
  try {
    const tab = await getActiveTab();
    const result = await sendAnalyzeCommand(tab.id);
    if (result?.ok) {
      setStatus(
        `분석 시작: 대상 ${result.total}개, 건너뜀 ${result.skipped}개`,
        "ok"
      );
    } else {
      setStatus(result?.error || "분석 요청 실패", "error");
    }
  } catch (error) {
    setStatus(`분석 요청 실패: ${error.message}`, "error");
  } finally {
    analyzeButton.disabled = false;
  }
});

checkServer();

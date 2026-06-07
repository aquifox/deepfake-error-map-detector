(() => {
  if (window.__deepfakeDetectorContentLoaded) {
    return;
  }
  window.__deepfakeDetectorContentLoaded = true;

  const MIN_IMAGE_WIDTH = 80;
  const MIN_IMAGE_HEIGHT = 80;
  const BADGE_CLASS = "dfd-result-badge";
  const analyzedImages = new WeakMap();
  const visibleBadges = new Set();

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

  function isUsableImage(img) {
    if (!(img instanceof HTMLImageElement)) {
      return false;
    }
    if (!img.complete || img.naturalWidth === 0 || img.naturalHeight === 0) {
      return false;
    }
    if (img.naturalWidth < MIN_IMAGE_WIDTH || img.naturalHeight < MIN_IMAGE_HEIGHT) {
      return false;
    }
    const rect = img.getBoundingClientRect();
    if (rect.width < MIN_IMAGE_WIDTH || rect.height < MIN_IMAGE_HEIGHT) {
      return false;
    }
    const style = window.getComputedStyle(img);
    return style.display !== "none" && style.visibility !== "hidden" && Number(style.opacity) > 0;
  }

  function collectImages() {
    const images = Array.from(document.images);
    const usable = [];
    let skipped = 0;
    for (const img of images) {
      if (isUsableImage(img)) {
        usable.push(img);
      } else {
        skipped += 1;
      }
    }
    return { usable, skipped };
  }

  function createBadge(img) {
    const badge = document.createElement("div");
    badge.className = BADGE_CLASS;
    badge.textContent = "분석 대기";
    document.documentElement.appendChild(badge);
    visibleBadges.add({ img, badge });
    positionBadge(img, badge);
    return badge;
  }

  function positionBadge(img, badge) {
    if (!document.documentElement.contains(img)) {
      badge.remove();
      return;
    }
    const rect = img.getBoundingClientRect();
    badge.style.left = `${Math.max(0, rect.left + window.scrollX + 6)}px`;
    badge.style.top = `${Math.max(0, rect.top + window.scrollY + 6)}px`;
    badge.style.maxWidth = `${Math.max(140, rect.width - 12)}px`;
  }

  function repositionBadges() {
    for (const entry of Array.from(visibleBadges)) {
      if (!entry.badge.isConnected || !entry.img.isConnected) {
        visibleBadges.delete(entry);
      } else {
        positionBadge(entry.img, entry.badge);
      }
    }
  }

  function updateBadge(badge, text, tone, titleText) {
    badge.textContent = text;
    badge.dataset.tone = tone;
    badge.title = titleText || text;
  }

  function formatProbability(value) {
    if (typeof value !== "number" || Number.isNaN(value)) {
      return "";
    }
    return `${Math.round(value * 100)}%`;
  }

  async function analyzeImage(img) {
    let badge = analyzedImages.get(img);
    if (!badge) {
      badge = createBadge(img);
      analyzedImages.set(img, badge);
    }
    updateBadge(badge, "분석 중...", "pending");

    const src = img.currentSrc || img.src;
    if (!src) {
      updateBadge(badge, "분석 불가", "error", "이미지 주소를 찾을 수 없습니다.");
      return;
    }

    try {
      const response = await sendRuntimeMessage({
        type: "DEEPFAKE_ANALYZE_IMAGE",
        src,
        pageUrl: window.location.href,
        width: img.naturalWidth,
        height: img.naturalHeight,
      });

      if (!response?.ok) {
        throw new Error(response?.error || "분석 실패");
      }

      const result = response.data;
      const fakeProbability = Number(result.fake_probability);
      const confidence = Number(result.confidence);
      const probabilityText = formatProbability(
        result.label === "fake" ? fakeProbability : confidence
      );
      if (result.label === "fake") {
        updateBadge(
          badge,
          `⚠ 딥페이크 의심 ${probabilityText} · AI 분석 결과 참고용`,
          "fake",
          `fake_probability=${fakeProbability.toFixed(4)}`
        );
      } else {
        updateBadge(
          badge,
          `REAL 가능성 높음 ${probabilityText} · AI 분석 결과 참고용`,
          "real",
          `fake_probability=${fakeProbability.toFixed(4)}`
        );
      }
    } catch (error) {
      updateBadge(badge, "분석 불가 · AI 분석 결과 참고용", "error", error.message);
    }
  }

  async function analyzePage() {
    const { usable, skipped } = collectImages();
    for (const img of usable) {
      await analyzeImage(img);
    }
    return { ok: true, total: usable.length, skipped };
  }

  chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message?.type !== "DEEPFAKE_ANALYZE_PAGE") {
      return false;
    }
    analyzePage()
      .then(sendResponse)
      .catch((error) => sendResponse({ ok: false, error: error.message }));
    return true;
  });

  window.addEventListener("scroll", repositionBadges, { passive: true });
  window.addEventListener("resize", repositionBadges);
})();

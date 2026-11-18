/* Service Worker
 * - 導覽請求：網路優先，離線時顯示 /offline
 * - /pwa/ 靜態資源（圖示等）：Stale-While-Revalidate
 * - Gradio 的 API / 串流 / 上傳 / 下載一律不攔截，避免影響即時互動
 * 更新程式後請調整 VERSION，舊快取會自動清除。
 */
const VERSION = "v1";
const CACHE = `csv-viewer-${VERSION}`;
const PRECACHE = [
  "/offline",
  "/pwa/icons/icon-192.png",
  "/pwa/icons/icon-512.png",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE).then((cache) => cache.addAll(PRECACHE)).then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(
          keys.filter((k) => k.startsWith("csv-viewer-") && k !== CACHE).map((k) => caches.delete(k))
        )
      )
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") return;

  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;

  // 頁面導覽：網路優先，失敗時顯示離線頁
  if (req.mode === "navigate") {
    event.respondWith(fetch(req).catch(() => caches.match("/offline")));
    return;
  }

  // 自家靜態資源：Stale-While-Revalidate
  if (url.pathname.startsWith("/pwa/")) {
    event.respondWith(
      caches.open(CACHE).then((cache) =>
        cache.match(req).then((cached) => {
          const network = fetch(req)
            .then((res) => {
              if (res && res.ok) cache.put(req, res.clone());
              return res;
            })
            .catch(() => cached);
          return cached || network;
        })
      )
    );
  }
  // 其餘（/gradio_api、/queue、/file= ...）交給瀏覽器處理
});

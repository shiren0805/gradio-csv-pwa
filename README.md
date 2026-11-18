# 📈 公開資料 CSV 瀏覽器（Gradio · PWA · RWD）

使用 [Gradio](https://www.gradio.app/) 製作的 CSV 瀏覽工具，支援 **PWA（可安裝成 App）** 與 **RWD（手機、平板、桌機自動適應）**。輸入 CSV 連結（預設為證交所公開資料），即可載入、搜尋、篩選欄位並下載結果。

## 功能

- 輸入任意 CSV 連結並一鍵載入（預設：`https://mopsfin.twse.com.tw/opendata/t187ap46_L_1.csv`）
- 自動處理繁體中文編碼（utf-8-sig → big5 → cp950）
- 可選擇是否移除空值（`dropna`）
- 全欄位關鍵字搜尋、自訂顯示欄位
- 下載原始 CSV 與篩選後的 CSV
- **PWA**：可安裝到手機主畫面或桌面、全螢幕開啟、離線時顯示提示頁
- **RWD**：桌機左右分欄，平板縮窄側欄，手機改為直向堆疊，按鈕符合觸控尺寸，並支援瀏海安全區與深色模式

## 專案結構

```
.
├── app.py              # FastAPI 外層 + Gradio 介面
├── pwa_head.html       # 注入 <head>：manifest、meta、SW 註冊、安裝提示
├── pwa/
│   ├── manifest.webmanifest
│   ├── sw.js           # Service Worker
│   ├── offline.html    # 離線頁
│   └── icons/          # 192 / 512 / maskable / apple-touch / favicon
├── tools/make_icons.py # 重新產生圖示（可自行換成你的 Logo）
├── requirements.txt
├── render.yaml         # Render Blueprint（選用）
├── .python-version
└── README.md
```

## 運作方式

`app.py` 以 FastAPI 為外層，提供以下路徑，最後把 Gradio 掛載在 `/`：

| 路徑 | 用途 |
| --- | --- |
| `/manifest.webmanifest` | PWA 安裝資訊 |
| `/sw.js` | Service Worker（必須從根路徑提供，才能控制整站） |
| `/offline` | 離線時顯示的頁面 |
| `/pwa/*` | 圖示等靜態檔 |
| `/healthz` | 健康檢查（供 Render 使用） |

Service Worker 只處理頁面導覽與 `/pwa/*` 靜態資源，Gradio 的 API、串流與檔案下載不會被攔截，不影響互動。

## 本機執行

```bash
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

開啟 http://127.0.0.1:7860。`localhost` 也算安全來源，所以本機就能測試 PWA。

## 部署到 Render

### 1. 上傳到 GitHub

```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/<你的帳號>/<你的repo>.git
git push -u origin main
```

### 2. 在 Render 建立服務

**方式 A：手動建立**

1. 登入 [Render](https://render.com/)，點選 **New → Web Service**，連結你的 repo。
2. 填寫設定：

| 欄位 | 值 |
| --- | --- |
| Runtime | Python 3 |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `python app.py` |
| Health Check Path | `/healthz` |
| Instance Type | Free（或付費方案） |

3. 點選 **Create Web Service**，部署完成後用 Render 提供的 `https://xxx.onrender.com` 開啟。

**方式 B：Blueprint**

repo 內已附 `render.yaml`。在 Render 點選 **New → Blueprint**，選擇此 repo 即會自動建立。

> PWA 需要 HTTPS，Render 預設提供，不需額外設定。

## 安裝成 App

| 平台 | 方式 |
| --- | --- |
| Android Chrome | 開啟網站後點畫面下方「安裝」，或選單 → 安裝應用程式 |
| 桌面 Chrome / Edge | 網址列右側的安裝圖示 |
| iPhone / iPad Safari | 分享按鈕 → 加入主畫面（網站會顯示提示） |

## 更新與維護

- 修改 `pwa/` 內的檔案後，把 `pwa/sw.js` 的 `VERSION` 加一（例如 `v2`），舊快取會自動清除。
- 想換 Logo：直接用同檔名的 PNG 覆蓋 `pwa/icons/` 內檔案，或修改 `tools/make_icons.py` 後重新執行。
- 更換預設連結：修改 `app.py` 的 `DEFAULT_URL`。
- 可在 Chrome DevTools → Application 面板檢查 Manifest 與 Service Worker，或用 Lighthouse 跑 PWA 檢測。

## 注意事項

- 免費方案閒置後會休眠，再次開啟需等待數十秒。
- 免費方案檔案系統為暫存，請用介面的下載按鈕保存檔案。
- 程式以 `verify=False` 略過 SSL 憑證驗證（沿用原程式），僅建議用於信任的公開資料來源。
- 離線時只會顯示離線提示頁，載入資料仍需要網路。

## 授權

MIT

"""公開資料 CSV 瀏覽器（Gradio + PWA + RWD）

架構：FastAPI 為外層，負責提供 PWA 所需的
    /manifest.webmanifest、/sw.js、/offline、/pwa/*（圖示）、/healthz
Gradio 以 mount_gradio_app 掛載在根路徑 "/"。
"""
import io
import os
import tempfile
from pathlib import Path

import gradio as gr
import pandas as pd
import requests
import urllib3
import uvicorn
from fastapi import FastAPI
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

# verify=False 會產生警告，這裡關閉提示
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_DIR = Path(__file__).resolve().parent
PWA_DIR = BASE_DIR / "pwa"
HEAD_HTML = (BASE_DIR / "pwa_head.html").read_text(encoding="utf-8")

DEFAULT_URL = "https://mopsfin.twse.com.tw/opendata/t187ap46_L_1.csv"  # 換連結


def _tmp_path(filename: str) -> str:
    """每次請求建立獨立暫存資料夾，避免多人同時使用時檔案互相覆蓋"""
    return os.path.join(tempfile.mkdtemp(), filename)


# ------------------------------------------------------------------
# 核心功能
# ------------------------------------------------------------------
def fetch_csv(url: str, drop_na: bool):
    """下載 CSV → DataFrame"""
    url = (url or "").strip()
    if not url:
        raise gr.Error("請輸入 CSV 連結")

    try:
        response = requests.get(url, verify=False, timeout=30)
        response.raise_for_status()
    except requests.RequestException as e:
        raise gr.Error(f"下載失敗：{e}")

    # 存檔（等同原本的 data01.csv）
    save_path = _tmp_path("data01.csv")
    with open(save_path, "wb") as f:
        f.write(response.content)

    # 繁體中文編碼：優先 utf-8-sig，失敗再退回 big5 / cp950
    df = None
    for enc in ("utf-8-sig", "big5", "cp950"):
        try:
            df = pd.read_csv(io.BytesIO(response.content), encoding=enc)
            break
        except (UnicodeDecodeError, pd.errors.ParserError):
            continue
    if df is None:
        raise gr.Error("無法解析 CSV，請確認編碼或格式")

    raw_rows = len(df)
    if drop_na:
        df = df.dropna()

    status = f"✅ 載入成功　原始 {raw_rows:,} 筆 → 目前 {len(df):,} 筆"
    stats = (
        f"### 📊 資料概況\n"
        f"- **筆數**：{len(df):,}\n"
        f"- **欄位數**：{df.shape[1]}\n"
        f"- **移除空值筆數**：{raw_rows - len(df):,}"
    )
    cols = gr.update(choices=list(df.columns), value=[])
    return df, df, status, stats, cols, save_path


def filter_data(df: pd.DataFrame, keyword: str, columns: list):
    """依關鍵字搜尋，並可限制顯示欄位"""
    if df is None:
        raise gr.Error("請先載入資料")

    result = df
    keyword = (keyword or "").strip()
    if keyword:
        mask = result.astype(str).apply(
            lambda col: col.str.contains(keyword, case=False, na=False, regex=False)
        ).any(axis=1)
        result = result[mask]

    show = result[columns] if columns else result
    return show, f"🔍 符合 {len(result):,} 筆 / 共 {len(df):,} 筆"


def export_filtered(df_view: pd.DataFrame):
    """匯出目前畫面上的表格"""
    if df_view is None or len(df_view) == 0:
        raise gr.Error("沒有可匯出的資料")
    path = _tmp_path("filtered.csv")
    df_view.to_csv(path, index=False, encoding="utf-8-sig")
    return path


# ------------------------------------------------------------------
# 介面（RWD）
# ------------------------------------------------------------------
theme = gr.themes.Soft(
    primary_hue="indigo",
    secondary_hue="sky",
    neutral_hue="slate",
    font=[gr.themes.GoogleFont("Noto Sans TC"), "system-ui", "sans-serif"],
)

css = """
/* ---------- 共用 ---------- */
.gradio-container {
    max-width: 1200px !important;
    margin: auto;
    padding-left: max(12px, env(safe-area-inset-left)) !important;
    padding-right: max(12px, env(safe-area-inset-right)) !important;
    padding-bottom: max(12px, env(safe-area-inset-bottom)) !important;
}
#title { text-align: center; padding: 8px 0 0 0; }
#title h1 { font-size: clamp(1.35rem, 4vw, 2rem); }
#subtitle { text-align: center; color: #64748b; margin-bottom: 8px; }
button { min-height: 44px; }                 /* 觸控目標至少 44px */
footer { display: none !important; }

/* 已安裝成 App（standalone）時，避開狀態列瀏海 */
@media (display-mode: standalone) {
    .gradio-container { padding-top: max(8px, env(safe-area-inset-top)) !important; }
}

/* ---------- 平板 (<= 1024px)：側欄縮窄 ---------- */
@media (max-width: 1024px) {
    #side-col { min-width: 240px !important; }
}

/* ---------- 手機 (<= 768px)：全部直向堆疊 ---------- */
@media (max-width: 768px) {
    .gradio-container { padding-top: 6px !important; }
    #url-row, #main-row { flex-direction: column !important; gap: 10px !important; }
    #url-row > *, #main-row > * {
        width: 100% !important;
        min-width: 100% !important;
        max-width: 100% !important;
        flex: 1 1 auto !important;
    }
    #btn-row { flex-direction: row !important; }
    #btn-row > * { min-width: 0 !important; }
    #data-table { font-size: 12px; }
    #data-table .table-wrap { max-height: 60vh; }
}

/* ---------- 小螢幕手機 (<= 480px) ---------- */
@media (max-width: 480px) {
    #subtitle { font-size: 0.85rem; }
    #data-table { font-size: 11px; }
}

/* 減少動態偏好 */
@media (prefers-reduced-motion: reduce) {
    * { animation: none !important; transition: none !important; }
}
"""

with gr.Blocks(
    theme=theme,
    css=css,
    head=HEAD_HTML,
    title="公開資料 CSV 瀏覽器",
) as demo:
    gr.Markdown("# 📈 公開資料 CSV 瀏覽器", elem_id="title")
    gr.Markdown("輸入 CSV 連結 → 一鍵載入 → 搜尋、篩選欄位、下載", elem_id="subtitle")

    full_df = gr.State()  # 完整資料

    with gr.Group():
        with gr.Row(elem_id="url-row"):
            url_box = gr.Textbox(
                label="CSV 連結",
                value=DEFAULT_URL,
                placeholder="https://...",
                scale=5,
                min_width=200,
            )
            drop_na = gr.Checkbox(label="移除空值 (dropna)", value=True, scale=1, min_width=140)
            load_btn = gr.Button("🚀 載入資料", variant="primary", scale=1, min_width=140)

    status = gr.Markdown("尚未載入資料")

    with gr.Row(elem_id="main-row"):
        with gr.Column(scale=1, min_width=260, elem_id="side-col"):
            stats = gr.Markdown("### 📊 資料概況\n尚無資料")
            keyword = gr.Textbox(label="🔍 關鍵字搜尋", placeholder="輸入公司代號、名稱…")
            columns = gr.Dropdown(
                label="顯示欄位（留空＝全部）",
                choices=[],
                multiselect=True,
            )
            with gr.Row(elem_id="btn-row"):
                search_btn = gr.Button("搜尋 / 套用", variant="secondary", min_width=100)
                reset_btn = gr.Button("重設", min_width=80)
            with gr.Accordion("📥 下載", open=False):
                raw_file = gr.File(label="原始 CSV (data01.csv)")
                export_btn = gr.Button("匯出目前篩選結果")
                export_file = gr.File(label="篩選後 CSV")

        with gr.Column(scale=3, min_width=300):
            table = gr.Dataframe(
                label="資料表",
                interactive=False,
                wrap=True,
                max_height=600,
                elem_id="data-table",
            )

    # 事件綁定
    load_btn.click(
        fetch_csv,
        inputs=[url_box, drop_na],
        outputs=[full_df, table, status, stats, columns, raw_file],
    )
    search_btn.click(filter_data, [full_df, keyword, columns], [table, status])
    keyword.submit(filter_data, [full_df, keyword, columns], [table, status])
    reset_btn.click(
        lambda df: (df, "", gr.update(value=[]), "已重設"),
        inputs=full_df,
        outputs=[table, keyword, columns, status],
    )
    export_btn.click(export_filtered, inputs=table, outputs=export_file)


# ------------------------------------------------------------------
# FastAPI 外層：PWA 檔案 + 掛載 Gradio
# ------------------------------------------------------------------
app = FastAPI(title="CSV Viewer PWA", docs_url=None, redoc_url=None, openapi_url=None)


@app.get("/manifest.webmanifest", include_in_schema=False)
def manifest():
    return FileResponse(PWA_DIR / "manifest.webmanifest", media_type="application/manifest+json")


@app.get("/sw.js", include_in_schema=False)
def service_worker():
    # Service Worker 必須由根路徑提供，才能控制整個網站 (scope="/")
    return FileResponse(
        PWA_DIR / "sw.js",
        media_type="application/javascript",
        headers={"Cache-Control": "no-cache", "Service-Worker-Allowed": "/"},
    )


@app.get("/offline", include_in_schema=False)
def offline():
    return FileResponse(PWA_DIR / "offline.html", media_type="text/html")


@app.get("/healthz", include_in_schema=False)
def healthz():
    return PlainTextResponse("ok")


# 注意：不要掛在 /static，Gradio 自己會用到該路徑
app.mount("/pwa", StaticFiles(directory=PWA_DIR), name="pwa")

# 必須最後掛載（根路徑 "/" 會接管所有未匹配的請求）
app = gr.mount_gradio_app(app, demo, path="/")


if __name__ == "__main__":
    # Render 會提供 PORT 環境變數，且必須綁定 0.0.0.0
    port = int(os.environ.get("PORT", 7860))
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        proxy_headers=True,        # 在 Render 的反向代理後面，正確辨識 https
        forwarded_allow_ips="*",
    )

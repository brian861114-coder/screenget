"""
i18n.py - 簡易多語系
支援 zh_TW / en_US / ja_JP，切換後立即套用。
"""

from typing import Dict

_LANG = "zh_TW"

TRANSLATIONS: Dict[str, Dict[str, str]] = {
    # ── 導航 / 主視窗 ──
    "app_title": {
        "zh_TW": "ScreenGet - 螢幕使用監控",
        "en_US": "ScreenGet - Screen Time Monitor",
        "ja_JP": "ScreenGet - 画面使用モニター",
    },
    "nav_dashboard": {"zh_TW": "使用總覽", "en_US": "Overview", "ja_JP": "概要"},
    "nav_browser": {"zh_TW": "瀏覽器分析", "en_US": "Browser", "ja_JP": "ブラウザ"},
    "nav_analysis": {"zh_TW": "軟體分析", "en_US": "Apps", "ja_JP": "アプリ分析"},
    "nav_settings": {"zh_TW": "設定", "en_US": "Settings", "ja_JP": "設定"},
    "status_tracking": {"zh_TW": "追蹤中", "en_US": "Tracking", "ja_JP": "追跡中"},
    "status_idle": {"zh_TW": "閒置中", "en_US": "Idle", "ja_JP": "アイドル"},
    "status_paused": {"zh_TW": "已暫停", "en_US": "Paused", "ja_JP": "一時停止"},

    # ── 週期 ──
    "period_today": {"zh_TW": "今日", "en_US": "Today", "ja_JP": "今日"},
    "period_week": {"zh_TW": "本週", "en_US": "Week", "ja_JP": "今週"},
    "period_month": {"zh_TW": "本月", "en_US": "Month", "ja_JP": "今月"},
    "period_custom": {"zh_TW": "自訂", "en_US": "Custom", "ja_JP": "カスタム"},
    "date_from": {"zh_TW": "起", "en_US": "From", "ja_JP": "開始"},
    "date_to": {"zh_TW": "迄", "en_US": "To", "ja_JP": "終了"},

    # ── 儀表板 ──
    "dash_title": {"zh_TW": "使用狀況總覽", "en_US": "Usage Overview", "ja_JP": "使用状況"},
    "card_total": {"zh_TW": "總使用時長 (點擊查看全部)", "en_US": "Total time (click for all)", "ja_JP": "合計時間（クリックで一覧）"},
    "card_apps": {"zh_TW": "使用程式數", "en_US": "Apps used", "ja_JP": "アプリ数"},
    "card_top": {"zh_TW": "最常使用", "en_US": "Most used", "ja_JP": "最も使用"},
    "section_timeline": {"zh_TW": "使用時間段", "en_US": "Timeline", "ja_JP": "タイムライン"},
    "section_hourly": {"zh_TW": "24 小時使用分佈", "en_US": "24-hour distribution", "ja_JP": "24時間分布"},
    "section_ranking": {"zh_TW": "使用時長排行", "en_US": "Usage ranking", "ja_JP": "使用ランキング"},
    "section_category": {"zh_TW": "分類使用占比", "en_US": "By category", "ja_JP": "カテゴリ別"},
    "filter_top5": {"zh_TW": "使用量前 5 名", "en_US": "TOP 5 most used", "ja_JP": "使用量 TOP 5"},
    "no_data": {"zh_TW": "暫無資料", "en_US": "No data", "ja_JP": "データなし"},
    "chart_hour": {"zh_TW": "當日時間", "en_US": "Hour of day", "ja_JP": "時刻"},
    "chart_minutes": {"zh_TW": "使用時間 (分鐘)", "en_US": "Minutes", "ja_JP": "使用時間（分）"},
    "chart_hours": {"zh_TW": "使用時間 (小時)", "en_US": "Hours", "ja_JP": "使用時間（時）"},
    "chart_date": {"zh_TW": "日期", "en_US": "Date", "ja_JP": "日付"},
    "chart_minutes_short": {"zh_TW": "分鐘", "en_US": "min", "ja_JP": "分"},
    "chart_hours_short": {"zh_TW": "小時", "en_US": "h", "ja_JP": "時"},
    "unit_label": {"zh_TW": "單位", "en_US": "Unit", "ja_JP": "単位"},
    "unit_auto": {"zh_TW": "自動", "en_US": "Auto", "ja_JP": "自動"},
    "unit_hours": {"zh_TW": "小時", "en_US": "Hours", "ja_JP": "時間"},
    "unit_minutes": {"zh_TW": "分鐘", "en_US": "Minutes", "ja_JP": "分"},
    "unit_header": {
        "zh_TW": "時長顯示單位",
        "en_US": "Duration display unit",
        "ja_JP": "時間の表示単位",
    },
    "unit_desc": {
        "zh_TW": "自動會依數值大小切換小時／分鐘軸，避免長時段圖表難讀。",
        "en_US": "Auto switches chart axes between hours and minutes for readability.",
        "ja_JP": "自動は数値に応じて時間／分の軸を切り替えます。",
    },
    "font_header": {
        "zh_TW": "介面字體大小",
        "en_US": "Interface font size",
        "ja_JP": "画面の文字サイズ",
    },
    "font_desc": {
        "zh_TW": "調整整體文字與圖表標籤大小，立即生效。",
        "en_US": "Adjust overall text and chart label size. Applies immediately.",
        "ja_JP": "全体の文字とグラフラベルサイズを調整します。即時反映されます。",
    },
    "font_label": {"zh_TW": "字體大小：", "en_US": "Font size:", "ja_JP": "文字サイズ："},
    "font_small": {"zh_TW": "小", "en_US": "Small", "ja_JP": "小"},
    "font_medium": {"zh_TW": "標準", "en_US": "Medium", "ja_JP": "標準"},
    "font_large": {"zh_TW": "大", "en_US": "Large", "ja_JP": "大"},
    "font_xlarge": {"zh_TW": "更大", "en_US": "Extra large", "ja_JP": "特大"},
    "cred_short_exact": {"zh_TW": "精", "en_US": "exact", "ja_JP": "正"},
    "cred_short_mixed": {"zh_TW": "混", "en_US": "mix", "ja_JP": "混"},
    "cred_short_est": {"zh_TW": "估", "en_US": "est.", "ja_JP": "推"},
    "cred_legend": {
        "zh_TW": "可信度：精＝有 URL · 混＝部分 URL · 估＝標題推斷",
        "en_US": "Credibility: exact=URL · mix=partial URL · est.=title inferred",
        "ja_JP": "信頼度：正＝URL · 混＝一部 URL · 推＝タイトル推定",
    },
    "cred_summary": {
        "zh_TW": "整體 URL 覆蓋 {n}%",
        "en_US": "URL coverage {n}%",
        "ja_JP": "URL カバー率 {n}%",
    },

    # ── 瀏覽器 ──
    "browser_title": {"zh_TW": "瀏覽器網站分析", "en_US": "Browser analysis", "ja_JP": "ブラウザ分析"},
    "card_browse_total": {"zh_TW": "瀏覽總時長 (點擊查看全部)", "en_US": "Browse time (click for all)", "ja_JP": "閲覧合計（クリックで一覧）"},
    "card_sites": {"zh_TW": "瀏覽網站數", "en_US": "Sites", "ja_JP": "サイト数"},
    "card_top_site": {"zh_TW": "最常造訪網站", "en_US": "Top site", "ja_JP": "最多訪問"},
    "section_browse_trend": {"zh_TW": "瀏覽時間趨勢", "en_US": "Browse trend", "ja_JP": "閲覧トレンド"},
    "section_site_ranking": {"zh_TW": "網站造訪排行", "en_US": "Site ranking", "ja_JP": "サイトランキング"},

    # ── 分析 ──
    "analysis_title": {"zh_TW": "軟體使用分析", "en_US": "App analysis", "ja_JP": "アプリ分析"},
    "select_app": {"zh_TW": "選擇軟體：", "en_US": "Select app:", "ja_JP": "アプリ選択："},
    "card_today": {"zh_TW": "今日使用時長", "en_US": "Today", "ja_JP": "今日"},
    "card_week": {"zh_TW": "本週使用時長", "en_US": "This week", "ja_JP": "今週"},
    "card_month": {"zh_TW": "本月使用時長", "en_US": "This month", "ja_JP": "今月"},
    "card_range": {"zh_TW": "選定區間時長", "en_US": "Selected range", "ja_JP": "選択期間"},
    "section_trend": {"zh_TW": "使用趨勢", "en_US": "Usage trend", "ja_JP": "使用トレンド"},

    # ── 詳情 ──
    "back": {"zh_TW": "返回", "en_US": "Back", "ja_JP": "戻る"},
    "detail_apps": {"zh_TW": "所有程式使用排行", "en_US": "All apps ranking", "ja_JP": "全アプリランキング"},
    "detail_sites": {"zh_TW": "網站造訪總排行", "en_US": "All sites ranking", "ja_JP": "全サイトランキング"},
    "no_records": {"zh_TW": "目前無使用紀錄", "en_US": "No usage records", "ja_JP": "利用記録なし"},

    # ── 設定 ──
    "settings_title": {"zh_TW": "應用程式設定", "en_US": "Settings", "ja_JP": "設定"},
    "lang_header": {"zh_TW": "語言設定", "en_US": "Language", "ja_JP": "言語"},
    "autostart": {"zh_TW": "開機自動執行 ScreenGet", "en_US": "Start ScreenGet on boot", "ja_JP": "起動時に ScreenGet を実行"},
    "idle_header": {"zh_TW": "閒置門檻", "en_US": "Idle timeout", "ja_JP": "アイドル閾値"},
    "idle_desc": {
        "zh_TW": "超過此時間無鍵盤／滑鼠操作後，暫停追蹤並排除該段閒置時間。",
        "en_US": "Pause tracking after no keyboard/mouse input for this long.",
        "ja_JP": "この時間キーボード／マウス操作がないと追跡を一時停止します。",
    },
    "idle_label": {"zh_TW": "閒置多久後暫停：", "en_US": "Pause after:", "ja_JP": "一時停止まで："},
    "minutes_fmt": {"zh_TW": "{n} 分鐘", "en_US": "{n} min", "ja_JP": "{n} 分"},
    "bridge_header": {"zh_TW": "瀏覽器橋接", "en_US": "Browser bridge", "ja_JP": "ブラウザ橋渡し"},
    "bridge_ok": {
        "zh_TW": "狀態：擴充套件近期有回報（橋接運作中）",
        "en_US": "Status: Extension reporting (bridge OK)",
        "ja_JP": "状態：拡張機能が応答中（正常）",
    },
    "bridge_warn": {
        "zh_TW": "狀態：尚未收到擴充套件訊息（請註冊橋接並重載擴充套件）",
        "en_US": "Status: No extension signal (register & reload extension)",
        "ja_JP": "状態：拡張機能未応答（登録／再読込してください）",
    },
    "ext_id": {"zh_TW": "擴充套件 ID：", "en_US": "Extension ID:", "ja_JP": "拡張機能 ID："},
    "btn_register": {"zh_TW": "註冊橋接", "en_US": "Register bridge", "ja_JP": "橋渡しを登録"},
    "bridge_hint": {
        "zh_TW": "請確認已載入 browser_extension，並在 chrome://extensions 開啟開發人員模式。註冊後需重新載入擴充套件或重開瀏覽器。",
        "en_US": "Load browser_extension in chrome://extensions (Developer mode). Reload extension after registering.",
        "ja_JP": "browser_extension を読み込み、登録後に拡張機能を再読み込みしてください。",
    },
    "cat_header": {"zh_TW": "分類與標籤", "en_US": "Categories", "ja_JP": "カテゴリ"},
    "cat_desc": {
        "zh_TW": "為應用程式或網站指定分類，儀表板會依分類彙總時長。",
        "en_US": "Assign categories to apps/sites for dashboard breakdown.",
        "ja_JP": "アプリ／サイトにカテゴリを割り当てます。",
    },
    "item": {"zh_TW": "項目：", "en_US": "Item:", "ja_JP": "項目："},
    "category": {"zh_TW": "分類：", "en_US": "Category:", "ja_JP": "カテゴリ："},
    "btn_apply_cat": {"zh_TW": "套用分類", "en_US": "Apply", "ja_JP": "適用"},
    "whitelist_header": {"zh_TW": "數據排除白名單", "en_US": "Exclusion list", "ja_JP": "除外リスト"},
    "whitelist_desc": {
        "zh_TW": "加入列表的程式或網站將不會出現在統計圖表中。",
        "en_US": "Listed apps/sites are excluded from stats.",
        "ja_JP": "リストの項目は統計から除外されます。",
    },
    "btn_add": {"zh_TW": "加入", "en_US": "Add", "ja_JP": "追加"},
    "btn_remove": {"zh_TW": "移除選中項目", "en_US": "Remove selected", "ja_JP": "選択を削除"},
    "export_header": {"zh_TW": "匯出資料", "en_US": "Export", "ja_JP": "エクスポート"},
    "export_desc": {
        "zh_TW": "匯出指定日期區間的使用紀錄（sessions）。",
        "en_US": "Export usage sessions for a date range.",
        "ja_JP": "指定期間の利用記録を書き出します。",
    },
    "btn_export_csv": {"zh_TW": "匯出 CSV", "en_US": "Export CSV", "ja_JP": "CSV 出力"},
    "btn_export_json": {"zh_TW": "匯出 JSON", "en_US": "Export JSON", "ja_JP": "JSON 出力"},

    # ── 健康檢查 ──
    "health_header": {"zh_TW": "資料健康檢查", "en_US": "Data health", "ja_JP": "データ健全性"},
    "health_desc": {
        "zh_TW": "檢查追蹤、橋接與資料庫異常，並可一鍵修復常見問題。",
        "en_US": "Check tracking, bridge and database issues; repair common problems.",
        "ja_JP": "追跡・橋渡し・DB の異常を検査し、一般的な問題を修復できます。",
    },
    "btn_health_run": {"zh_TW": "執行檢查", "en_US": "Run check", "ja_JP": "検査する"},
    "btn_health_repair": {"zh_TW": "修復可修正項目", "en_US": "Repair fixable", "ja_JP": "修復する"},
    "health_ok": {"zh_TW": "全部正常", "en_US": "All clear", "ja_JP": "問題なし"},
    "health_summary": {
        "zh_TW": "檢查完成：{ok} 正常，{warn} 警告，{error} 錯誤",
        "en_US": "Done: {ok} ok, {warn} warnings, {error} errors",
        "ja_JP": "完了：正常 {ok}／警告 {warn}／エラー {error}",
    },

    # ── 對話框 ──
    "msg_lang_updated": {
        "zh_TW": "語言已切換。",
        "en_US": "Language updated.",
        "ja_JP": "言語を切り替えました。",
    },
    "msg_updated": {"zh_TW": "設定已更新", "en_US": "Settings updated", "ja_JP": "設定を更新しました"},
    "msg_tip": {"zh_TW": "提示", "en_US": "Notice", "ja_JP": "お知らせ"},
    "msg_bridge_ok": {"zh_TW": "橋接已註冊", "en_US": "Bridge registered", "ja_JP": "登録完了"},
    "msg_bridge_ok_body": {
        "zh_TW": "已寫入 Native Messaging 設定。\n請到 chrome://extensions 重新載入 ScreenGet 擴充套件，或重開瀏覽器。",
        "en_US": "Native Messaging registered.\nReload the ScreenGet extension or restart the browser.",
        "ja_JP": "Native Messaging を登録しました。\n拡張機能を再読み込みしてください。",
    },
    "msg_bridge_fail": {"zh_TW": "註冊失敗", "en_US": "Registration failed", "ja_JP": "登録失敗"},
    "msg_need_ext_id": {"zh_TW": "請先填入擴充套件 ID。", "en_US": "Please enter the extension ID.", "ja_JP": "拡張機能 ID を入力してください。"},
    "msg_export_done": {"zh_TW": "匯出完成", "en_US": "Export complete", "ja_JP": "出力完了"},
    "msg_export_fail": {"zh_TW": "匯出失敗", "en_US": "Export failed", "ja_JP": "出力失敗"},
    "msg_exported_to": {"zh_TW": "已匯出至：\n{path}", "en_US": "Saved to:\n{path}", "ja_JP": "保存先：\n{path}"},
    "msg_date_error": {"zh_TW": "結束日期必須晚於或等於開始日期。", "en_US": "End date must be on or after start date.", "ja_JP": "終了日は開始日以降にしてください。"},
    "msg_already_listed": {"zh_TW": "該項目已在列表中。", "en_US": "Already in the list.", "ja_JP": "既にリストにあります。"},
    "msg_repair_done": {
        "zh_TW": "已修復 {n} 項問題。",
        "en_US": "Repaired {n} issue(s).",
        "ja_JP": "{n} 件を修復しました。",
    },
    "empty_title": {
        "zh_TW": "目前還沒有資料",
        "en_US": "No data yet",
        "ja_JP": "まだデータがありません",
    },
    "empty_body": {
        "zh_TW": "繼續使用電腦即可開始累積統計。若是瀏覽器頁面，請確認擴充套件已連線。",
        "en_US": "Keep using your computer to collect stats. For browser pages, make sure the extension is connected.",
        "ja_JP": "PC を使い続けると統計が蓄積されます。ブラウザは拡張機能の接続を確認してください。",
    },
    "empty_action": {
        "zh_TW": "前往設定檢查",
        "en_US": "Open settings",
        "ja_JP": "設定を開く",
    },
    "loading": {
        "zh_TW": "資料更新中…",
        "en_US": "Updating…",
        "ja_JP": "更新中…",
    },
    "click_hint": {
        "zh_TW": "點擊可查看詳細",
        "en_US": "Click for details",
        "ja_JP": "クリックで詳細",
    },
    "chart_click_hint": {
        "zh_TW": "點擊長條可開啟該項目分析",
        "en_US": "Click a bar to open analysis",
        "ja_JP": "棒をクリックして分析を開く",
    },
    "chart_click_site_hint": {
        "zh_TW": "點擊長條可查看該網站趨勢與頁面",
        "en_US": "Click a bar to open site details",
        "ja_JP": "棒をクリックしてサイト詳細を開く",
    },
    "browser_layer_hint": {
        "zh_TW": "層級：瀏覽總時長 網站排行 單一網站（與桌面軟體分開）",
        "en_US": "Layers: browse total site ranking single site (separate from desktop apps)",
        "ja_JP": "階層：閲覧合計 サイト順位 単一サイト（アプリとは別）",
    },
    "website_layer_hint": {
        "zh_TW": "第三層：單一網站的時段、趨勢與頁面排行",
        "en_US": "Layer 3: timeline, trend, and pages for one site",
        "ja_JP": "第3層：単一サイトの時間帯・推移・ページ",
    },
    "layer_l1": {
        "zh_TW": "第一層：全部網站合計趨勢",
        "en_US": "Layer 1: all sites combined",
        "ja_JP": "第1層：全サイト合計",
    },
    "website_title": {
        "zh_TW": "單一網站分析",
        "en_US": "Website analysis",
        "ja_JP": "サイト分析",
    },
    "select_site": {"zh_TW": "選擇網站：", "en_US": "Select site:", "ja_JP": "サイト選択："},
    "section_site_trend": {
        "zh_TW": "網站每日趨勢",
        "en_US": "Site daily trend",
        "ja_JP": "サイト日次推移",
    },
    "section_page_ranking": {
        "zh_TW": "頁面／標題排行",
        "en_US": "Page / title ranking",
        "ja_JP": "ページ／タイトル順位",
    },
    "precision_exact": {
        "zh_TW": "精確（含 URL）",
        "en_US": "Exact (with URL)",
        "ja_JP": "正確（URL あり）",
    },
    "precision_mixed": {
        "zh_TW": "混合（部分 URL）",
        "en_US": "Mixed (partial URL)",
        "ja_JP": "混合（一部 URL）",
    },
    "precision_estimated": {
        "zh_TW": "推估（依標題）",
        "en_US": "Estimated (from title)",
        "ja_JP": "推定（タイトル）",
    },
    "crumb_overview": {"zh_TW": "使用總覽", "en_US": "Overview", "ja_JP": "概要"},
    "crumb_browser": {"zh_TW": "瀏覽器", "en_US": "Browser", "ja_JP": "ブラウザ"},
    "crumb_analysis": {"zh_TW": "軟體分析", "en_US": "App analysis", "ja_JP": "アプリ分析"},
    "crumb_detail": {"zh_TW": "完整排行", "en_US": "Full ranking", "ja_JP": "全ランキング"},
    "crumb_site_list": {"zh_TW": "網站排行", "en_US": "Site ranking", "ja_JP": "サイト順位"},
    "crumb_website": {"zh_TW": "網站詳情", "en_US": "Site detail", "ja_JP": "サイト詳細"},
    "settings_tab_general": {"zh_TW": "一般", "en_US": "General", "ja_JP": "一般"},
    "settings_tab_tracking": {"zh_TW": "追蹤與健康", "en_US": "Tracking", "ja_JP": "追跡と健全性"},
    "settings_tab_organize": {"zh_TW": "分類與排除", "en_US": "Organize", "ja_JP": "分類と除外"},
    "settings_tab_export": {"zh_TW": "匯出", "en_US": "Export", "ja_JP": "出力"},
    "detail_click_hint": {
        "zh_TW": "點擊項目可開啟分析",
        "en_US": "Click an item to open analysis",
        "ja_JP": "項目をクリックして分析",
    },
}


def set_language(lang: str):
    global _LANG
    if lang in ("zh_TW", "en_US", "ja_JP"):
        _LANG = lang
    else:
        _LANG = "zh_TW"


def get_language() -> str:
    return _LANG


def t(key: str, **kwargs) -> str:
    """取得目前語言的字串；缺 key 時回傳 key 本身。"""
    entry = TRANSLATIONS.get(key)
    if not entry:
        text = key
    else:
        text = entry.get(_LANG) or entry.get("zh_TW") or key
    if kwargs:
        try:
            return text.format(**kwargs)
        except Exception:
            return text
    return text

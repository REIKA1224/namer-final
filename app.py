# =====================================================================
# Namers AI ～AI名付け支援ツール～ の画面（Streamlit）
#
#   画面 ………… このファイル（app.py）
#   裏の処理 …… logic.py（AIへのお願い、名前のチェック、診断、商標、ドメイン）
#   漢字 ………… kanji_check.py ＋ kanji.json
#
# 手元で動かす：streamlit run app.py
# =====================================================================
import base64
import csv
import io
import os
import time
import uuid
from collections import defaultdict
from datetime import datetime
from html import escape
from zoneinfo import ZoneInfo

import streamlit as st
from PIL import Image, ImageOps

import logic
from logic import TARGETS

st.set_page_config(page_title="Namers AI ～AI名付け支援ツール～", page_icon="🪶", layout="centered")


# ---------------------------------------------------------------------
# 設定（APIキーなどは Streamlit の Secrets に入れる。コードには書かない）
# ---------------------------------------------------------------------
def secret(name, default=""):
    try:
        if name in st.secrets:
            return st.secrets[name]
    except Exception:  # Secrets がまったく設定されていないとき
        pass
    return os.environ.get(name, default)  # Secrets になければ、環境変数を見る


logic.API_KEY = secret("OPENAI_API_KEY")
logic.MODEL = secret("OPENAI_MODEL") or "gpt-6-luna"
PREMIUM_CODE = secret("PREMIUM_CODE")  # 空なら、詳細診断は誰でも使える
NOTE_URL = "https://note.com/namersai/n/nd1fda095acbc?sub_rt=share_pb"
SURVEY_URL = "https://docs.google.com/forms/d/e/1FAIpQLSd_NxM6_s0_3Ho1UQGg1PF1CTUZvzl1_6BfmLSgw2HBy7yTsg/viewform?usp=publish-editor"
TABS = ["💡  \n名前を考える", "💎  \n詳細診断", "🔍  \n商標・ドメイン", "⭐  \nお気に入り"]  # 絵文字の下に名前

# 同じ人が1時間に使える回数（APIの料金を使いすぎないため）
LIMITS = {"generate": 30, "diagnose": 10, "trademark": 10, "domains": 30}

# 見た目（色や大きさ）。「nm-」で始まる名前は、このアプリの画面用に自分でつけた名前
st.markdown("""
<style>
:root { --nm-main:#0a7f61; --nm-light:#e6f5f0; --nm-accent:#00cc96; --nm-star:#e0a100;
        --nm-ok-bg:#e7f6ec; --nm-ok:#1e7b3a; --nm-warn-bg:#fff6dc; --nm-warn:#7a5600; }
[data-testid="stMainBlockContainer"] { padding-top: 2.5rem; max-width: 760px; }
.nm-title { font-size: 2rem; font-weight: 700; margin: 0; }
.nm-subtitle { color: var(--nm-main); font-weight: 700; margin: 0; }
.nm-caption { color: var(--nm-sub); font-size: 0.9rem; margin: 6px 0 0; }
.nm-h2 { border-left: 6px solid var(--nm-accent); padding-left: 10px; font-size: 1.3rem; font-weight: 700; margin: 2px 0 6px; }
.nm-h3 { font-weight: 700; font-size: 1.05rem; margin: 6px 0 2px; }
.nm-h3 small { font-weight: 400; color: var(--nm-sub); font-size: 0.8rem; }
.nm-group { font-size: 0.85rem; color: var(--nm-sub); margin: 0; }
/* 対象の4つのボタン：スマホでは2つずつ2段、PCでは横に4つ */
.st-key-targets > div { flex: 1 1 calc(50% - 0.5rem) !important; width: auto !important; max-width: none !important;
                        min-width: 0 !important; }
@media (min-width: 640px) { .st-key-targets > div { flex-basis: calc(25% - 0.75rem) !important; } }
.st-key-targets button { width: 100%; min-height: 88px; border-radius: 12px; padding: 6px; }
.st-key-targets button p { font-size: 1rem; line-height: 1.5; }
.st-key-targets [data-testid="stBaseButton-primary"],
.st-key-targets [data-testid="stBaseButton-primary"]:hover { background: var(--nm-light); color: var(--nm-main);
                                                            border: 2px solid var(--nm-main); font-weight: 700; }
/* 色の設定ファイル（.streamlit/config.toml）がなくても、メインのボタンを緑にする */
[data-testid="stBaseButton-primary"] { background: var(--nm-main); border-color: var(--nm-main); color: #ffffff; }
button[data-variant="pills"][data-selected="true"] { background: var(--nm-light) !important; border-color: var(--nm-main) !important;
                                                     color: var(--nm-main) !important; }
/* タブ：スマホでも4つが1行に収まるように */
[data-testid="stTabs"] [role="tablist"] { gap: 0; }
[data-testid="stTab"] { flex: 1 1 0; min-width: 0; padding: 4px 2px; justify-content: center; }
[data-testid="stTab"] p { font-size: 0.78rem; white-space: normal; text-align: center; line-height: 1.35; }
.nm-dir { display: inline-block; background: #f0f0f0; color: #333333; border-radius: 6px; padding: 2px 10px; font-size: 0.85rem; }
.nm-name-line { line-height: 1.3; }
.nm-name-line .surname { font-size: 1.3rem; color: var(--nm-sub); margin-right: 6px; }
.nm-name-line .name { font-size: 2rem; font-weight: 700; }
.nm-name-line .yomi { color: var(--nm-sub); margin-left: 6px; }
.nm-romaji { color: var(--nm-sub); font-size: 0.9rem; }
.nm-catch { font-weight: 700; margin: 6px 0; }
.nm-badge { display: inline-block; padding: 2px 10px; border-radius: 6px; font-size: 0.85rem; margin: 2px 6px 2px 0;
            background: #f0f0f0; color: #333333; }
.nm-badge.ok { background: var(--nm-ok-bg); color: var(--nm-ok); }
.nm-badge.warn { background: var(--nm-warn-bg); color: var(--nm-warn); }
.nm-score { display: grid; grid-template-columns: max-content 1fr; gap: 2px 18px; margin-top: 8px; }
.nm-score .axis { color: var(--nm-sub); }
.nm-stars { color: var(--nm-star); letter-spacing: 1px; white-space: nowrap; }
.nm-stars .off { color: #bbbbbb; }
.nm-stars .num { color: var(--nm-sub); font-size: 0.8rem; margin-left: 6px; letter-spacing: 0; }
.nm-judge { border-radius: 8px; padding: 10px 12px; margin: 4px 0 8px; color: #333333; }
.nm-judge .nm-small { color: #555555; }
.nm-judge.ok { background: var(--nm-ok-bg); }
.nm-judge.warn { background: var(--nm-warn-bg); }
.nm-small { font-size: 0.85rem; color: var(--nm-sub); }
.nm-live { border: 1px dashed #bbbbbb; border-radius: 8px; padding: 10px 12px; margin: 6px 0; }
.nm-table-wrap { overflow-x: auto; }
.nm-table { border-collapse: collapse; width: 100%; font-size: 0.9rem; }
.nm-table th, .nm-table td { border: 1px solid #dddddd; padding: 6px 8px; text-align: center; }
.nm-table th { background: var(--nm-light); color: #333333; white-space: nowrap; }
.nm-table td:first-child { white-space: nowrap; text-align: left; }
.nm-footer { color: var(--nm-sub); font-size: 0.8rem; }
</style>
""", unsafe_allow_html=True)


# 明るい表示（ライト）と暗い表示（ダーク）で変える色。暗い表示でカードを白くすると、白い文字が読めなくなるため
try:
    DARK = st.context.theme.type == "dark"
except Exception:
    DARK = False
if DARK:
    st.markdown("<style>:root { --nm-sub: #b0b0b0; }</style>", unsafe_allow_html=True)
else:
    st.markdown("<style>:root { --nm-sub: #666666; } div[class*='st-key-box-'] { background: #ffffff; }</style>",
                unsafe_allow_html=True)


# ---------------------------------------------------------------------
# セッション（このブラウザでアプリを開いている間だけ残るデータ）
# ---------------------------------------------------------------------
DEFAULTS = {
    "target": None,       # いま選んでいる対象（baby / pet / character / brand）
    "blocks": [],         # 画面に出している結果のまとまり（「もっと見る」などで増える）
    "shown": {},          # 対象ごとに、もう出した名前（次は別の名前を出すため）
    "pending": None,      # これからAIに頼むこと（ボタンが押されたときに入る）
    "favorites": [],
    "history": [],
    "report": None,       # 詳細診断の結果
    "tm_result": None,    # 商標チェックの結果
    "dom_result": None,   # ドメインの確認結果
    "unlocked": False,    # 詳細診断のアクセスコードが合っているか
    "clear_armed": False,  # 「履歴を消す」を1回押した状態か
    "restored": "",       # 読み込んだCSV（同じファイルを2回読み込まないため）
}
for _key, _value in DEFAULTS.items():
    if _key not in st.session_state:
        st.session_state[_key] = _value


# ---------------------------------------------------------------------
# 回数制限（全員で共有する記録。サーバーが動いている間だけ残る目安）
# ---------------------------------------------------------------------
@st.cache_resource
def usage_log():
    return defaultdict(list)


def visitor_id():
    ip = (st.context.headers.get("X-Forwarded-For") or "").split(",")[0].strip()
    if ip:
        return ip
    if "visitor" not in st.session_state:  # IPアドレスがわからないときは、開いている画面ごとに数える
        st.session_state.visitor = str(uuid.uuid4())
    return st.session_state.visitor


def over_limit(kind):
    log, now = usage_log(), time.time()
    key = (kind, visitor_id())
    log[key] = [t for t in log[key] if now - t < 3600]
    if len(log[key]) >= LIMITS[kind]:
        return True
    log[key].append(now)
    return False


LIMIT_MESSAGE = "短い時間に何度も使われたため、一時的に止めています。1時間ほどしてからお試しください。"


# ---------------------------------------------------------------------
# 表示用の小さな関数
# ---------------------------------------------------------------------
def e(text):
    """AIの答えなどをHTMLに入れる前に、記号を置きかえる（HTMLとして動かないように）"""
    return escape(str(text if text is not None else ""))


def html(text):
    st.markdown(text, unsafe_allow_html=True)


def heading(text):
    html(f"<div class='nm-h2'>{text}</div>")


def stars(score):
    try:
        n = max(1, min(5, round(float(score))))
    except (TypeError, ValueError):
        n = 3
    return f"<span class='nm-stars'>{'★' * n}<span class='off'>{'☆' * (5 - n)}</span><span class='num'>{n}</span></span>"


def score_rows(scores):
    return "<div class='nm-score'>" + "".join(
        f"<span class='axis'>{e(axis)}</span>{stars(score)}" for axis, score in scores.items()) + "</div>"


LEVEL_TONE = {"◎": "ok", "○": "ok", "⚠": "warn"}
LEVEL_DESC = {
    "◎": "すべての字が、辞書にある音読み・訓読みで読めます。",
    "○": "名乗り（名前で使われる読み）や、漢字の読みの一部を使っています。名前ではよくある読み方です。",
    "⚠": "辞書の読みでは説明できない読みです。名付けで広く使われている読み（例：陽葵＝ひまり）でも、辞書にないとこの表示になります。",
}


def parts_text(parts):
    return " ＋ ".join(f"{c}＝{y}（{k}）" for c, y, k in parts)


def judge_html(check):
    if not check.get("level"):
        return ""
    text = f"<b>{e(check['label'])}</b><br>{LEVEL_DESC[check['level']]}"
    if check["parts"]:
        text += f"<br><span class='nm-small'>内訳：{e(parts_text(check['parts']))}</span>"
    text += ("<br><span class='nm-small'>※2025年5月26日から、戸籍に名前の読み方（フリガナ）も記載されるようになりました。"
             "読み方は「一般に認められているもの」である必要があり、窓口で説明を求められる場合があります。"
             "この判定は辞書データによる目安です。</span>")
    return f"<div class='nm-judge {LEVEL_TONE[check['level']]}'>{text}</div>"


def now_text():
    try:
        return datetime.now(ZoneInfo(st.context.timezone or "Asia/Tokyo")).strftime("%m/%d %H:%M")
    except Exception:
        return datetime.now().strftime("%m/%d %H:%M")


def photo_to_data_url(file):
    """写真を小さくして（長い辺1024px）、AIに送れる形にする"""
    img = ImageOps.exif_transpose(Image.open(file)).convert("RGB")
    img.thumbnail((1024, 1024))
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=85)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


# ---------------------------------------------------------------------
# ボタンを押したときに動く関数（コールバック）
# ---------------------------------------------------------------------
def select_target(key):
    if st.session_state.target != key:
        st.session_state.target = key
        st.session_state.blocks = []   # 別の対象に切りかえたら、前の結果は消す（履歴には残っている）
        st.session_state.pending = None


def ask_generate(mode, like=None):
    st.session_state.pending = {"mode": mode, "like": like}


def make_record(item, target, surname):
    check = item.get("check")
    return {"name": item["name"], "yomi": item["yomi"], "romaji": item.get("romaji", ""), "target": target,
            "surname": surname, "direction": item.get("direction", ""), "catch": item.get("catch", ""),
            "reason": item.get("reason", ""), "scores": item.get("scores", {}),
            "mark": check["level"] if check else "", "strokes": check["strokes"] if check else 0, "time": now_text()}


def is_fav(name):
    return any(f["name"] == name for f in st.session_state.favorites)


def toggle_fav(record):
    if is_fav(record["name"]):
        st.session_state.favorites = [f for f in st.session_state.favorites if f["name"] != record["name"]]
        st.toast(f"「{record['name']}」をお気に入りから外しました")
    else:
        st.session_state.favorites.insert(0, dict(record))
        st.toast(f"⭐「{record['name']}」をお気に入りに保存しました")


def open_diagnose(item, target, surname):
    st.session_state.d_target = target
    st.session_state.d_surname = surname
    st.session_state.d_name = item["name"]
    st.session_state.d_yomi = item["yomi"]
    st.session_state.report = None
    st.session_state.tab = TABS[1]   # 詳細診断のタブに切りかえる
    st.toast(f"💎「{item['name']}」を詳細診断に入れました")


def open_trademark(item):
    st.session_state.t_name = item["name"]
    st.session_state.t_yomi = item["yomi"]
    st.session_state.o_base = logic.to_domain_label(item.get("romaji", ""))
    st.session_state.tm_result = None
    st.session_state.dom_result = None
    st.session_state.tab = TABS[2]
    st.toast(f"🔍「{item['name']}」を商標・ドメインに入れました")


def use_alternative(name, yomi):
    st.session_state.d_name = name
    st.session_state.d_yomi = yomi
    st.session_state.report = None


def toggle_compare(name):
    picked = [f["name"] for f in st.session_state.favorites if st.session_state.get(f"cmp_{f['name']}")]
    if len(picked) > 3:   # 比べられるのは3つまで
        st.session_state[f"cmp_{name}"] = False
        st.toast("比べられるのは3つまでです")


def delete_fav(name):
    st.session_state.favorites = [f for f in st.session_state.favorites if f["name"] != name]


def clear_history():
    if not st.session_state.clear_armed:  # 1回目は確認、2回目で本当に消す
        st.session_state.clear_armed = True
        return
    st.session_state.history = []
    st.session_state.clear_armed = False
    st.toast("履歴を消しました")


# ---------------------------------------------------------------------
# AIに名前を考えてもらう
# ---------------------------------------------------------------------
def current_request(like):
    """画面で選んでいる条件を、logic.py に渡す形にまとめる"""
    t = st.session_state.target
    conf = TARGETS[t]
    ss = st.session_state
    tags = []
    for i in range(len(conf["tags"])):
        tags += ss.get(f"tag_{t}_{i}") or []
    photo = ss.get(f"photo_{t}") if conf["photo"] else None
    axes = ss.get(f"axes_{t}")
    if axes is None:  # まだ判断軸の欄を開いていないときは、対象ごとのおすすめ
        axes = conf["axes"]
    return {
        "target": t, "tags": tags,
        "wish": (ss.get(f"wish_{t}") or "").strip(),
        "surname": (ss.get("surname") or "").strip() if conf["surname"] else "",
        "gender": ss.get(f"gender_{t}", "指定なし") if conf["gender"] else "指定なし",
        "include": (ss.get("include") or "").strip(),
        "exclude": (ss.get("exclude") or "").strip(),
        "length": ss.get("length", 0),
        "allow_ateji": bool(conf["ateji"] and ss.get("allow_ateji")),
        "axes": list(axes),
        "shown": ss.shown.get(t, [])[-80:],
        "like": like,
        "image": photo_to_data_url(photo) if photo else None,
    }


def stats_text(target, total, removed):
    count = sum(removed.values())
    how = "漢字データなどで" if target == "baby" else ""
    if not count:
        return f"AIが出した{total}案を{how}チェックしました（外した案はありません）。"
    reasons = "、".join(f"{k} {v}件" for k, v in removed.items())
    return f"AIが出した{total}案を{how}チェックして、条件に合わない{count}案を外しました（{reasons}）。"


def run_generate(mode, like):
    t = st.session_state.target
    req = current_request(like)
    title = {"new": "🪶 提案された名前", "more": "🔄 さらに候補"}.get(mode) or f"🌱 「{like['name']}」に近い案"
    block = {"id": uuid.uuid4().hex[:8], "title": title, "target": t, "surname": req["surname"],
             "names": [], "note": "", "error": ""}
    if not logic.API_KEY:
        block["error"] = "APIキーが設定されていません（Streamlit の Secrets に OPENAI_API_KEY を入れてください）。"
    elif not 3 <= len(req["axes"]) <= 5:
        block["error"] = "評価の判断軸は3〜5個えらんでください（「もっと細かく設定する」の中にあります）。"
    elif over_limit("generate"):
        block["error"] = LIMIT_MESSAGE
    else:
        with st.spinner("💎 分析中...（AIが考えて、漢字をチェックしています）"):
            try:
                data = logic.generate(req)
            except Exception as err:
                block["error"] = logic.error_message(err)
            else:
                block["names"] = data["names"]
                block["note"] = stats_text(t, data["total"], data["removed"])
                shown = st.session_state.shown.setdefault(t, [])
                for item in data["names"]:
                    shown.append(item["name"])
                    st.session_state.history.insert(0, make_record(item, t, req["surname"]))
                for name in data["skipped"]:  # チェックで外した名前も、次は出さない
                    if name not in shown:
                        shown.append(name)
                st.session_state.history = st.session_state.history[:150]
    st.session_state.pending = None
    if mode == "new":
        st.session_state.blocks = []
    st.session_state.blocks.append(block)


def show_card(block, i, item):
    t, surname = block["target"], block["surname"]
    key = f"{block['id']}_{i}"
    record = make_record(item, t, surname)
    with st.container(border=True, key=f"box-card-{key}"):
        with st.container(horizontal=True, horizontal_alignment="distribute", vertical_alignment="center"):
            html(f"<span class='nm-dir'>🏷️ {e(item.get('direction') or TARGETS[t]['label'])}</span>")
            fav = is_fav(item["name"])
            st.button("★ 保存済み" if fav else "☆ 保存", key=f"fav_{key}", on_click=toggle_fav, args=(record,))

        top = "<div class='nm-name-line'>"
        if surname:
            top += f"<span class='surname'>{e(surname)}</span>"
        top += f"<span class='name'>{e(item['name'])}</span><span class='yomi'>（{e(item['yomi'])}）</span></div>"
        if item.get("romaji"):
            top += f"<div class='nm-romaji'>{e(item['romaji'])}</div>"
        if item.get("catch"):
            top += f"<div class='nm-catch'>「{e(item['catch'])}」</div>"
        check = item.get("check")
        if check:  # 赤ちゃんの名前は、漢字チェックの結果を出す
            top += ("<div><span class='nm-badge ok'>✅ 名前に使える字</span>"
                    f"<span class='nm-badge {LEVEL_TONE[check['level']]}'>📖 読み：{e(check['label'])}</span>"
                    f"<span class='nm-badge'>✏️ {check['strokes']}画</span></div>")
        if item.get("scores"):
            top += score_rows(item["scores"])
        html(top)

        with st.expander("📝 くわしく見る"):
            html(f"<div class='nm-h3'>📖 由来・込めた願い</div>{e(item.get('reason'))}")
            if item.get("caution"):
                html(f"<div class='nm-h3'>⚠️ 気をつけたい点（AIの指摘）</div>{e(item['caution'])}")
            if check:
                html(f"<div class='nm-h3'>📚 読み方の判定（漢字データ）</div>{judge_html(check)}")
                if check["chars"]:
                    strokes = "　".join(f"{e(k['char'])}：{k['strokes']}画（{e(k['kubun'])}漢字）" for k in check["chars"])
                    html(f"<div class='nm-h3'>✏️ 漢字の画数</div>{strokes}")

        with st.container(horizontal=True, gap="small"):
            st.button("🌱 近い案", key=f"like_{key}", on_click=ask_generate,
                      args=("like", {"name": item["name"], "yomi": item["yomi"]}))
            st.button("💎 診断", key=f"diag_{key}", on_click=open_diagnose, args=(item, t, surname))
            if t in ("brand", "character"):
                st.button("🔍 商標", key=f"tm_{key}", on_click=open_trademark, args=(item,))
            with st.popover("📤 共有"):
                st.caption("右上のボタンでコピーできます")
                text = f"{item['name']}（{item['yomi']}）" + (f"\n{item['catch']}" if item.get("catch") else "")
                st.code(text + "\nNamers AI で見つけた名前", language=None)


# =====================================================================
# 画面
# =====================================================================
html("<div class='nm-title'>🪶 Namers AI</div><div class='nm-subtitle'>～AI名付け支援ツール～</div>"
     "<p class='nm-caption'>名前の生成から詳細診断、商標・ドメインのチェックまでを1つのアプリで。"
     "AIが考えた名前は、漢字データで「名前に使える漢字か」「読み方は自然か」もチェックしています！</p>")
if not logic.API_KEY:
    st.warning("⚠️ APIキーが設定されていません。（管理者の方へ：Streamlit の Secrets に OPENAI_API_KEY を設定してください）")

tab_gen, tab_diag, tab_tm, tab_fav = st.tabs(TABS, key="tab", on_change="rerun")

# ---------------- 💡 名前を考える ----------------
with tab_gen:
    with st.container(border=True, key="box-form"):
        heading("📋 名付けの条件")
        html("<div class='nm-h3'>① 何に名前をつける？</div>")
        with st.container(horizontal=True, key="targets", gap="small"):
            for t_key, conf in TARGETS.items():
                st.button(f"{conf['emoji']}  \n{conf['label']}", key=f"target_{t_key}", wrap=True,
                          type="primary" if st.session_state.target == t_key else "secondary",
                          on_click=select_target, args=(t_key,))

        target = st.session_state.target
        if target:
            conf = TARGETS[target]
            html("<div class='nm-h3'>② どんな名前にしたい？ <small>（タグを選ぶだけでもOK！）</small></div>")
            for i, (group, options) in enumerate(conf["tags"].items()):
                html(f"<div class='nm-group'>{group}</div>")
                st.pills(group, options, selection_mode="multi", key=f"tag_{target}_{i}", label_visibility="collapsed")

            st.text_area("その他の願い・詳細（任意）", key=f"wish_{target}", placeholder=conf["placeholder"],
                         max_chars=400, height=90)
            if conf["surname"] or conf["gender"]:
                col1, col2 = st.columns(2)
                if conf["surname"]:
                    col1.text_input("苗字（省略可）", key="surname", max_chars=10, placeholder="例：佐藤")
                if conf["gender"]:
                    (col2 if conf["surname"] else col1).selectbox("性別", conf["gender"], key=f"gender_{target}")
            if conf["photo"]:
                st.file_uploader("📸 写真やイラストからイメージする（任意）", type=["png", "jpg", "jpeg", "webp"],
                                 key=f"photo_{target}")

            with st.expander("⚙️ もっと細かく設定する（漢字・文字数など）"):
                col1, col2 = st.columns(2)
                col1.text_input("使いたい漢字（省略可）", key="include", max_chars=30, placeholder="例：翔、陽")
                col2.text_input("避けたい漢字（省略可）", key="exclude", max_chars=30, placeholder="例：子")
                st.caption("※使いたい漢字を複数書いたときは、そのうちどれか1つを使います")
                st.selectbox("文字数", [0, 1, 2, 3, 4], key="length",
                             format_func=lambda n: "おまかせ" if n == 0 else f"{n}文字")
                if conf["ateji"]:
                    st.checkbox("辞書にない読み（当て字など）の名前も出す", key="allow_ateji")
                st.multiselect("📐 評価の判断軸（3〜5個えらんでください）", logic.ALL_AXES, default=conf["axes"],
                               max_selections=5, key=f"axes_{target}")

            st.button("✨ AIに名前を考えてもらう", type="primary", width="stretch",
                      on_click=ask_generate, args=("new",))

    # ボタンが押されていたら、ここでAIに頼む（考えている間は、ここに「分析中」が出る）
    if st.session_state.pending and st.session_state.target:
        run_generate(st.session_state.pending["mode"], st.session_state.pending["like"])

    # 結果（新しいものが上）
    for n, block in enumerate(reversed(st.session_state.blocks)):
        html(f"<div class='nm-h2'>{e(block['title'])}<span class='nm-small'>　{len(block['names'])}件</span></div>")
        if block["error"]:
            st.error(f"❌ {block['error']}")
        for i, item in enumerate(block["names"]):
            show_card(block, i, item)
        if block["note"]:
            st.caption(f"🔎 {block['note']}")
        if block["note"] and not block["names"]:
            st.warning("条件に合う名前が見つかりませんでした。「使いたい漢字」や「文字数」などの条件をゆるめて、もう一度お試しください。")
        if n == 0:
            st.button("🔄 もっと見る", key="more", width="stretch", on_click=ask_generate, args=("more",))

# ---------------- 💎 詳細診断 ----------------
with tab_diag:
    with st.container(border=True, key="box-diagnose"):
        heading("💎 プレミアム詳細診断レポート")
        st.write("考えた名前を入力すると、AIが響き・意味・海外での響きなどを多角的に分析してレポートにします。")
        if PREMIUM_CODE and not st.session_state.unlocked:
            with st.container(border=True):
                st.markdown("🔒 この機能を利用するにはアクセスコードが必要です。")
                st.text_input("アクセスコード", type="password", key="code_input")
                st.link_button("コードを取得（noteへ）", NOTE_URL)

        st.selectbox("命名の対象", list(TARGETS), key="d_target", format_func=lambda k: TARGETS[k]["label"])
        d_target = st.session_state.d_target
        col1, col2 = st.columns(2)
        if d_target == "baby":
            col1.text_input("苗字（任意）", key="d_surname", max_chars=10)
        (col2 if d_target == "baby" else col1).text_input("名前（必須）", key="d_name", max_chars=20,
                                                          placeholder="例：陽葵", live=True)
        st.text_input("読み仮名（必須・ひらがな）", key="d_yomi", max_chars=40, placeholder="例：ひまり", live=True)

        # 入力中に、AIを使わず漢字データだけでチェックする（赤ちゃんの名前のとき）
        d_name = (st.session_state.d_name or "").strip()
        d_yomi = (st.session_state.d_yomi or "").strip()
        if d_target == "baby" and d_name:
            k = logic.kanji_info(d_name, d_yomi)
            rows = ["✅ すべて名前に使える字です" if k["ok"] else f"❌ 名前に使えない字があります：{e(''.join(k['bad_chars']))}"]
            if d_yomi and k["level"]:
                rows.append(f"📖 読み方：{e(k['label'])}")
                if k["parts"]:
                    rows.append(f"内訳：{e(parts_text(k['parts']))}")
            rows.append(f"✏️ 画数：漢字 合計{k['strokes']}画")
            html("<div class='nm-live'><b>🔎 その場チェック（漢字データ）</b><br>" + "<br>".join(rows) + "</div>")

        st.text_area("この名前に込めた想いや、世界観（任意）", key="d_wish", max_chars=400, height=70,
                     placeholder="例：人を明るくする子に／和風ファンタジーの巫女")
        st.caption("💡「名前を考える」の結果で「💎 診断」を押すと、ここに自動で入力されます。")

        if st.button("📝 詳細評価レポートを作成する", type="primary", width="stretch"):
            st.session_state.report = None
            code = (st.session_state.get("code_input") or "").strip()
            if not d_name or not d_yomi:
                st.warning("「名前」と「読み仮名」は必ず入力してください。")
            elif PREMIUM_CODE and not st.session_state.unlocked and code != PREMIUM_CODE:
                st.error("❌ アクセスコードが違います。")
            elif not logic.API_KEY:
                st.error("❌ APIキーが設定されていません。")
            elif over_limit("diagnose"):
                st.error(f"❌ {LIMIT_MESSAGE}")
            else:
                was_locked = not st.session_state.unlocked
                st.session_state.unlocked = True
                surname = (st.session_state.get("d_surname") or "").strip() if d_target == "baby" else ""
                with st.spinner("🔍 専門的な視点で多角的に分析中..."):
                    try:
                        result = logic.diagnose(d_target, d_name, d_yomi, surname, (st.session_state.d_wish or "").strip())
                        st.session_state.report = {"data": result, "name": d_name, "surname": surname,
                                                   "target": d_target}
                    except Exception as err:
                        st.error(f"❌ {logic.error_message(err)}")
                if was_locked and PREMIUM_CODE:
                    st.rerun()  # コードが合ったので、コードの入力欄を消して表示しなおす

    report = st.session_state.report
    if report:
        r, check = report["data"]["report"], report["data"]["check"]
        with st.container(border=True, key="box-report"):
            heading(f"📋 【{e((report['surname'] + ' ') if report['surname'] else '')}{e(report['name'])}】診断レポート")
            st.info(f"**📝 総評**\n\n{r.get('summary', '')}")
            html("<div class='nm-h3'>📊 評価</div>")
            for axis, s in (r.get("scores") or {}).items():
                if isinstance(s, dict):
                    html(f"<div><b>{e(axis)}</b>　{stars(s.get('score'))}<br><span class='nm-small'>{e(s.get('reason'))}</span></div>")
            if check:
                html("<div class='nm-h3'>📚 漢字データでの確認</div>")
                st.write("✅ すべて名前に使える字です（常用漢字・人名用漢字・かな）" if check["ok"]
                         else f"❌ 名前に使えない字があります：{''.join(check['bad_chars'])}")
                html(judge_html(check))
                st.write(f"✏️ 漢字の画数：合計{check['strokes']}画")
            html("<div class='nm-h3'>🔍 1. 響きと意味の分析</div>")
            st.markdown(f"**🗣️ 響き：** {r.get('sound', '')}")
            st.markdown(f"**📖 意味・由来：** {r.get('meaning', '')}")
            risks = r.get("risks") or []
            if isinstance(risks, str):
                risks = [risks]
            if risks:
                html("<div class='nm-h3'>⚠️ 2. 誤読・からかいのリスク</div>")
                st.markdown("\n".join(f"- {x}" for x in risks))
            g = r.get("global_risk") if isinstance(r.get("global_risk"), dict) else {}
            if g:
                html("<div class='nm-h3'>🌍 3. 海外での響き</div>")
                box = {"低": st.success, "中": st.warning, "高": st.error}.get(g.get("level"), st.info)
                box(f"**【注意度：{g.get('level', '－')}】** {g.get('detail', '')}")
            html("<div class='nm-h3'>💡 4. アドバイス</div>")
            st.write(r.get("advice", ""))
            alternatives = [a for a in (r.get("alternatives") or []) if isinstance(a, dict)]
            if alternatives:
                html("<div class='nm-h3'>✨ 改善案</div>")
                for j, alt in enumerate(alternatives):
                    mark = f"　<span class='nm-small'>読み{e(alt['mark'])}</span>" if alt.get("mark") else ""
                    html(f"<b style='font-size:1.15rem'>{e(alt.get('name'))}</b>（{e(alt.get('yomi'))}）{mark}"
                         f"<br>{e(alt.get('reason'))}")
                    st.button("💎 この案を診断する", key=f"alt_{j}", on_click=use_alternative,
                              args=(str(alt.get("name") or ""), str(alt.get("yomi") or "")))
            st.caption("※評価はAIによるものです。AIの分析には誤りが含まれることがあります。")

# ---------------- 🔍 商標・ドメイン ----------------
with tab_tm:
    with st.container(border=True, key="box-trademark"):
        heading("🔍 商標リスク 事前チェック")
        st.write("サービス名・商品名・屋号として使う前に、商標としてのリスクをAIが事前チェックします。")
        st.warning("⚠️ このチェックはAIの知識による事前スクリーニングで、商標データベースとの照合ではありません。"
                   "正式な確認は特許庁の J-PlatPat で必ず行ってください。")
        col1, col2 = st.columns(2)
        col1.text_input("チェックしたい名前（必須）", key="t_name", max_chars=40, placeholder="例：Namers AI")
        col2.text_input("読み仮名（任意）", key="t_yomi", max_chars=60, placeholder="例：ネイマーズエーアイ")
        classes = st.pills("想定する用途（商標の区分）", logic.TRADEMARK_CLASSES, selection_mode="multi", key="t_classes",
                           format_func=lambda c: f"{c.split('：')[1]}（{c.split('：')[0]}）")
        if st.button("🛡️ 商標リスクをチェックする", type="primary", width="stretch"):
            name = (st.session_state.t_name or "").strip()
            if not name:
                st.warning("チェックしたい名前を入力してください。")
            elif not logic.API_KEY:
                st.error("❌ APIキーが設定されていません。")
            elif over_limit("trademark"):
                st.error(f"❌ {LIMIT_MESSAGE}")
            else:
                with st.spinner("🛡️ 商標の観点から分析中..."):
                    try:
                        st.session_state.tm_result = {"name": name, "data": logic.trademark(
                            name, (st.session_state.t_yomi or "").strip(), classes or [])}
                    except Exception as err:
                        st.error(f"❌ {logic.error_message(err)}")

        tm = st.session_state.tm_result
        if tm:
            r = tm["data"]

            def as_list(x):  # AIの答えが配列（リスト）でなかったときも、配列として扱う
                return x if isinstance(x, list) else ([x] if x else [])

            html(f"<div class='nm-h3'>🛡️ 【{e(tm['name'])}】商標事前チェック結果</div>")
            html("<div class='nm-h3'>🗣️ 1. 称呼（呼び方）</div>")
            st.markdown(f"**{r.get('shoko', '')}**")
            if as_list(r.get("similar")):
                st.write(f"似ていると判断されやすい呼び方：{'、'.join(map(str, as_list(r.get('similar'))))}")
            html("<div class='nm-h3'>🧩 2. 識別力（登録のされやすさ）</div>")
            st.markdown(f"**タイプ：{r.get('type', '')}**  \n{r.get('type_comment', '')}")
            html("<div class='nm-h3'>⚔️ 3. 有名ブランドとの似かより</div>")
            conflicts = [c for c in as_list(r.get("conflicts")) if isinstance(c, dict)]
            if conflicts:
                st.markdown("\n".join(f"- **{c.get('name', '')}**：{c.get('comment', '')}" for c in conflicts))
            else:
                st.write("AIの知識の範囲では、はっきりした懸念は見つかりませんでした（データベースとの照合ではないので、"
                         "必ずJ-PlatPatで確認してください）。")
            html("<div class='nm-h3'>✅ 4. 次のステップ：J-PlatPatで正式に確認する</div>")
            st.write("下のキーワードは、右上のボタンでコピーできます。J-PlatPatの「商標検索」で称呼（カタカナ）を検索してください。")
            for kw in as_list(r.get("keywords")):
                st.code(str(kw), language=None)
            with st.container(horizontal=True):
                st.link_button("🏛️ J-PlatPat を開く（特許庁）", "https://www.j-platpat.inpit.go.jp/")
                st.link_button("🔎 Toreru商標検索 を開く", "https://search.toreru.jp/")

    with st.container(border=True, key="box-domain"):
        heading("🌐 ドメイン空きチェック")
        st.write("こちらは商標と違い、ドメインの登録情報（RDAP）に問い合わせて確認します。")
        st.text_input("ドメインにしたい英字表記", key="o_base", max_chars=60, placeholder="例：namers-ai")
        tlds = st.pills("確認するドメインの種類", logic.TLDS, selection_mode="multi", key="o_tlds",
                        default=[".com", ".jp", ".net", ".app"])
        if st.button("🌐 ドメインの空きを確認する", type="primary", width="stretch"):
            base = logic.to_domain_label(st.session_state.o_base)
            if not base:
                st.warning("英字の表記（例：namers-ai）を入力してください。")
            elif not tlds:
                st.warning("確認するドメインの種類を1つ以上えらんでください。")
            elif over_limit("domains"):
                st.error(f"❌ {LIMIT_MESSAGE}")
            else:
                with st.spinner("🌐 確認中..."):
                    st.session_state.dom_result = {"base": base, "results": logic.check_domains(base, tlds)}
        dom = st.session_state.dom_result
        if dom:
            html(f"<div class='nm-h3'>「{e(dom['base'])}」の確認結果</div>")
            for it in dom["results"]:
                mark = {"available": "⭕", "taken": "❌", "unknown": "❓"}[it["status"]]
                line = f"{mark} `{it['domain']}`：{it['note']}"
                if it["status"] == "unknown" and it["domain"].endswith(".jp"):
                    line += "　[JPRS WHOISで確認](https://whois.jprs.jp/)"
                st.markdown(line)
            st.caption("※確認した時点の情報です。実際に取れるかは、お名前.com・ムームードメインなどの登録サービスで確認してください。")


# ---------------- ⭐ お気に入り・履歴 ----------------
CSV_HEADER = ["名前", "読み", "ローマ字", "対象", "方向性", "ひとこと", "由来", "読みの判定", "画数", "評価", "日時"]


def to_csv(records):
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(CSV_HEADER)
    for f in records:
        writer.writerow([f["name"], f["yomi"], f["romaji"], TARGETS.get(f["target"], {}).get("label", f["target"]),
                         f["direction"], f["catch"], f["reason"], f["mark"], f["strokes"] or "",
                         " / ".join(f"{a}:{s}" for a, s in f["scores"].items()), f["time"]])
    return "﻿" + buf.getvalue()  # 先頭の印（BOM）があると、Excel で開いても文字化けしない


def from_csv(file):
    """保存したCSVから、お気に入りを読み込む"""
    labels = {conf["label"]: k for k, conf in TARGETS.items()}
    records = []
    for row in csv.DictReader(io.StringIO(file.getvalue().decode("utf-8-sig"))):
        if not row.get("名前"):
            continue
        scores = {}
        for pair in (row.get("評価") or "").split(" / "):
            axis, _, score = pair.rpartition(":")
            if axis and score.isdigit():
                scores[axis] = int(score)
        records.append({"name": row["名前"], "yomi": row.get("読み", ""), "romaji": row.get("ローマ字", ""),
                        "target": labels.get(row.get("対象"), "baby"), "surname": "",
                        "direction": row.get("方向性", ""), "catch": row.get("ひとこと", ""),
                        "reason": row.get("由来", ""), "scores": scores, "mark": row.get("読みの判定", ""),
                        "strokes": int(row["画数"]) if (row.get("画数") or "").isdigit() else 0,
                        "time": row.get("日時", "")})
    return records


with tab_fav:
    st.info("📌 お気に入りと履歴は、このアプリを開いているあいだだけ保存されます（サーバーには残りません）。"
            "残したいときは CSV で保存してください。保存した CSV を読み込むと、お気に入りを戻せます。")
    favorites = st.session_state.favorites
    with st.container(border=True, key="box-favorites"):
        heading(f"⭐ お気に入りの名前（{len(favorites)}件）")
        if not favorites:
            st.write("まだお気に入りはありません。「名前を考える」の結果で「☆ 保存」を押すと、ここに保存されます。")
        else:
            st.caption("チェックを入れた名前（3つまで）を、下の表で比べられます。")
            for f in favorites:
                with st.container(border=True):
                    with st.container(horizontal=True, horizontal_alignment="distribute", vertical_alignment="center"):
                        st.checkbox(f"{f['surname'] + ' ' if f['surname'] else ''}{f['name']}（{f['yomi']}）",
                                    key=f"cmp_{f['name']}", on_change=toggle_compare, args=(f["name"],))
                        st.button("🗑️ 削除", key=f"del_{f['name']}", on_click=delete_fav, args=(f["name"],))
                    sub = [TARGETS.get(f["target"], {}).get("label", ""), f"読み{f['mark']}" if f["mark"] else "",
                           f["catch"]]
                    st.caption("／".join(x for x in sub if x))

            picked = [f for f in favorites if st.session_state.get(f"cmp_{f['name']}")]
            if len(picked) == 1:
                st.caption("もう1つチェックすると比べられます")
            elif len(picked) >= 2:
                axes = []
                for p in picked:
                    axes += [a for a in p["scores"] if a not in axes]
                rows = [("読み", [e(p["yomi"]) for p in picked]),
                        ("読みの判定", [e(p["mark"] or "－") for p in picked]),
                        ("画数", [f"{p['strokes']}画" if p["strokes"] else "－" for p in picked])]
                rows += [(a, [stars(p["scores"][a]) if a in p["scores"] else "－" for p in picked]) for a in axes]
                table = "<tr><th></th>" + "".join(f"<th>{e(p['name'])}</th>" for p in picked) + "</tr>"
                table += "".join(f"<tr><td>{e(label)}</td>" + "".join(f"<td>{v}</td>" for v in values) + "</tr>"
                                 for label, values in rows)
                html("<div class='nm-h3'>📊 比べてみる</div>"
                     f"<div class='nm-table-wrap'><table class='nm-table'>{table}</table></div>")
            st.download_button("📥 お気に入りをCSVで保存", to_csv(favorites), file_name="favorites.csv", mime="text/csv")

        restore = st.file_uploader("📂 保存したCSVから、お気に入りを戻す", type=["csv"], key="restore")
        if restore and st.session_state.restored != restore.file_id:
            st.session_state.restored = restore.file_id
            try:
                added = [r for r in from_csv(restore) if not is_fav(r["name"])]
                st.session_state.favorites = added + st.session_state.favorites
                st.toast(f"📂 お気に入りを{len(added)}件戻しました")
                st.rerun()
            except Exception:
                st.error("CSVを読み込めませんでした。このアプリで保存したCSVか確認してください。")

    with st.container(border=True, key="box-history"):
        heading("📜 生成履歴")
        history = st.session_state.history
        if not history:
            st.write("まだ生成履歴はありません。")
        else:
            for n, h in enumerate(history[:100]):
                with st.container(horizontal=True, horizontal_alignment="distribute", vertical_alignment="center"):
                    sub = "／".join(x for x in [TARGETS[h["target"]]["label"], h["direction"], h["time"]] if x)
                    html(f"<b>{e(h['name'])}</b><span class='nm-small'>（{e(h['yomi'])}）<br>{e(sub)}</span>")
                    st.button("★ 保存済み" if is_fav(h["name"]) else "☆ 保存", key=f"hist_{n}",
                              on_click=toggle_fav, args=(h,))
            with st.container(horizontal=True):
                st.download_button("📥 履歴をCSVで保存", to_csv(history), file_name="naming_log.csv", mime="text/csv")
                st.button("⚠️ もう一度押すと全部消えます" if st.session_state.clear_armed else "🗑️ 履歴を消す",
                          key="clear_history", on_click=clear_history)

# ---------------- フッター ----------------
st.divider()
st.link_button("🧸 アンケートに答える（アプリの改善にご協力ください！）", SURVEY_URL)
html("<p class='nm-footer'>※名前の案はAIの提案、漢字のチェックは辞書データによる目安です。出生届の受理や商標登録を保証するものではありません。<br>"
     "※入力した内容は名前を考えるためにAIサービスへ送られますが、このアプリのサーバーには保存しません。<br>"
     "※漢字データには、EDRDG の <a href='https://www.edrdg.org/wiki/index.php/KANJIDIC_Project' target='_blank'>KANJIDIC2</a>・"
     "<a href='https://www.edrdg.org/wiki/index.php/JMdict-EDICT_Dictionary_Project' target='_blank'>JMdict</a> を"
     "<a href='https://www.edrdg.org/edrdg/licence.html' target='_blank'>ライセンス</a>（CC BY-SA）に従って使っています。</p>")

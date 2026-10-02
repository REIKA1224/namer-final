# =====================================================================
# Namers AI の「裏の処理」（画面は app.py）
#
#   ・AIに名前を考えてもらう（OpenAI の API）
#   ・赤ちゃんの名前を、漢字データでチェックする（kanji_check.py）
#   ・名前の詳細診断、商標の事前チェック、ドメインの空き確認
#
# このファイルは Streamlit を使っていないので、画面と切りはなして読めます。
# =====================================================================
import json
import re

import requests
from openai import AuthenticationError, BadRequestError, OpenAI, RateLimitError

import kanji_check as kc

# 設定（app.py が Streamlit の Secrets から入れる。コードには書かない）
API_KEY = ""
MODEL = "gpt-6-luna"


# ---------------------------------------------------------------------
# 対象ごとの設定（画面に出すタグなどと、AIへのルール）
# ---------------------------------------------------------------------
TARGETS = {
    "baby": {
        "label": "赤ちゃん", "emoji": "👶",
        "placeholder": "例：春生まれなので、温かいイメージを入れたい",
        "tags": {
            "基本のイメージ": ["明るい", "元気", "やさしい", "クール", "知的", "上品", "美しい", "かっこいい", "かわいい",
                        "凛とした", "おだやか", "芯が強い"],
            "自然・季節": ["春", "夏", "秋", "冬", "海・水", "空・宇宙", "太陽", "月・星", "花・植物", "宝石", "光", "風"],
            "時代・雰囲気": ["古風", "モダン", "和風", "洋風", "レトロ", "神秘的", "今どき"],
            "個性・色": ["国際的", "ユニーク", "中性的", "赤", "青", "黄", "白", "黒", "茶", "紫", "緑", "橙", "灰", "桃"],
            "音・響き": ["1文字", "2文字", "3文字", "呼びやすい", "やわらかい響き", "力強い響き", "和風の響き", "洋風の響き"],
        },
        "gender": ["指定なし", "男の子", "女の子"], "surname": True, "photo": False, "ateji": True,
        "axes": ["響き", "意味・願い", "読みやすさ", "書きやすさ", "独自性"],
        "rule": "日本の戸籍に届け出る赤ちゃんの名前。使える字は常用漢字・人名用漢字・ひらがな・カタカナだけ。"
                "悪い意味の漢字は使わない。苗字があれば、続けて読んだときの響きも考える。",
        "directions": ["王道", "今どき", "ひと味ちがう"],
    },
    "pet": {
        "label": "ペット", "emoji": "😻",
        "placeholder": "例：白くてふわふわのオスの子猫。のんびり屋さん",
        "tags": {
            "どんな子？": ["犬", "猫", "うさぎ", "鳥", "ハムスター", "フェレット", "魚", "爬虫類"],
            "見た目・色": ["白", "黒", "茶", "グレー", "三毛", "ぶち", "金色", "ふわふわ", "小さい", "大きい"],
            "性格": ["おっとり", "やんちゃ", "あまえんぼう", "元気", "クール", "上品"],
            "イメージ": ["かわいい", "かっこいい", "食べ物の名前", "お菓子", "果物", "和風", "洋風", "ユニーク", "呼びやすい",
                     "2文字", "3文字"],
        },
        "gender": None, "surname": False, "photo": True, "ateji": False,
        "axes": ["呼びやすさ", "かわいさ", "覚えやすさ", "独自性"],
        "rule": "ペットの名前。呼びかけやすい2〜4音の名前を中心にする。表記はカタカナかひらがなが基本。",
        "directions": ["呼びやすい", "見た目から", "ユニーク"],
    },
    "character": {
        "label": "キャラクター", "emoji": "🧙",
        "placeholder": "例：和風ファンタジーの寡黙な剣士。過去に故郷を失っている",
        "tags": {
            "世界観": ["現代", "学園", "和風ファンタジー", "西洋ファンタジー", "SF", "ダーク", "歴史もの", "未来風", "ゴシック"],
            "役割": ["主人公", "ヒロイン", "勇者", "ライバル", "悪役", "師匠", "仲間", "魔法使い", "騎士", "姫・貴族", "王族",
                   "人外"],
            "印象": ["クール", "熱血", "儚い", "狂気", "最強", "ミステリアス", "高貴", "無邪気", "冷酷", "神秘的"],
            "色・モチーフ": ["赤", "青", "黒", "白", "金", "銀", "月・星", "炎", "氷", "花"],
            "名前の形": ["和名", "カタカナ名", "漢字＋独自の読み", "短い名前", "長い名前", "二つ名つき"],
        },
        "gender": ["指定なし", "男性", "女性"], "surname": False, "photo": True, "ateji": False,
        "axes": ["世界観との一致", "印象の強さ", "覚えやすさ", "独自性"],
        "rule": "創作キャラクター（小説・ゲーム・TRPGなど）の名前。世界観や役割に合う表記にする。"
                "独自の読みを使うときは、その理由を reason に書く。外国語が由来なら、元の単語と意味を書く。",
        "directions": ["世界観重視", "印象に残る", "意外性"],
    },
    "brand": {
        "label": "お店・サービス", "emoji": "🏪",
        "placeholder": "例：北海道の小さなパン屋。朝の光とあたたかさを感じる名前",
        "tags": {
            "業種": ["カフェ", "パン・お菓子", "飲食店", "美容・サロン", "雑貨・ショップ", "アパレル", "アプリ・Web", "ゲーム",
                   "教室・スクール", "会社・事務所", "イベント"],
            "雰囲気": ["おしゃれ", "親しみやすい", "高級感", "ナチュラル", "ポップ", "信頼感", "和モダン", "レトロ", "未来風",
                    "かわいい"],
            "表記": ["英字", "カタカナ", "ひらがな", "漢字", "造語"],
            "響き・長さ": ["短い", "呼びやすい", "国際的", "ユニーク"],
        },
        "gender": None, "surname": False, "photo": True, "ateji": False,
        "axes": ["覚えやすさ", "発音しやすさ", "業種との一致", "独自性", "国際性"],
        "rule": "お店・サービス・商品の名前。覚えやすく発音しやすい名前にする。"
                "一般的な言葉を並べただけの名前は商標登録されにくいので避ける。",
        "directions": ["伝わる", "おしゃれ", "造語"],
    },
}
ALL_AXES = ["響き", "意味・願い", "読みやすさ", "書きやすさ", "呼びやすさ", "覚えやすさ", "独自性", "親しみやすさ",
            "上品さ", "力強さ", "国際性", "古風さ", "新しさ", "かわいさ", "世界観との一致", "印象の強さ", "業種との一致",
            "発音しやすさ"]


# ---------------------------------------------------------------------
# AIを呼ぶ
# ---------------------------------------------------------------------
def ask_ai(system, user, image=None):
    """AIに質問して、答え（JSON）を辞書にして返す"""
    client = OpenAI(api_key=API_KEY, timeout=90)  # 90秒たっても答えがなければあきらめる
    content = user
    if image:  # 画像があるときは、文章と画像をいっしょに送る
        content = [{"type": "text", "text": user}, {"type": "image_url", "image_url": {"url": image}}]
    messages = [{"role": "system", "content": system}, {"role": "user", "content": content}]
    try:
        # reasoning_effort="low"：考える時間を短くして、速く答えてもらう
        res = client.chat.completions.create(model=MODEL, messages=messages,
                                             response_format={"type": "json_object"}, reasoning_effort="low")
    except BadRequestError as e:
        if "reasoning" not in str(e):  # そのモデルが reasoning_effort に対応していないときだけ、外してやり直す
            raise
        res = client.chat.completions.create(model=MODEL, messages=messages, response_format={"type": "json_object"})
    return json.loads(res.choices[0].message.content)


def error_message(e):
    """AIのエラーを、わかりやすい日本語にする"""
    if isinstance(e, AuthenticationError):
        return "APIキーが正しくありません。Streamlit の Secrets の OPENAI_API_KEY を確認してください。"
    if isinstance(e, RateLimitError):
        if "insufficient_quota" in str(e):
            return "OpenAIのクレジット残高が足りません。OpenAIの管理画面（Billing）を確認してください。"
        return "AIが混み合っています。少し時間をおいてお試しください。"
    return f"AIの呼び出しでエラーが発生しました（{type(e).__name__}）。もう一度お試しください。"


def kanji_info(name, yomi):
    """漢字チェックの結果をまとめる（赤ちゃんの名前用）"""
    level, parts = kc.check_reading(name, yomi) if yomi else (None, [])
    return {
        "ok": not kc.bad_chars(name),
        "bad_chars": kc.bad_chars(name),
        "level": level,
        "label": kc.READING_LABELS.get(level, ""),
        "parts": parts,
        "strokes": kc.strokes(name),
        "chars": [{"char": c, "strokes": kc.KANJI[c]["画数"], "kubun": kc.KANJI[c]["区分"]}
                  for c in name if c in kc.KANJI],
    }


# ---------------------------------------------------------------------
# 名前を考える
# ---------------------------------------------------------------------
GEN_SYSTEM = """あなたはプロの命名アドバイザーです。条件に合う名前を考えて、JSONだけで答えてください。
・由来や意味は、確実に知っていることだけを書く（不確かな語源を作らない）
・有名人・有名キャラクター・有名ブランドとまったく同じ名前は避ける
・方向性（direction）は指定された3つから選び、3つともまんべんなく使う。候補どうしで似た響きにしない
・scores は、指定された判断軸ごとに1〜5の整数（5＝とても良い、3＝ふつう、1＝問題あり）。甘くつけない
出力形式：
{"names": [{"name": "名前の表記", "yomi": "読み（ひらがな）", "romaji": "ローマ字",
  "direction": "方向性", "catch": "名前の印象をひとことで（20字以内）",
  "reason": "由来・意味と、願いにどう合うか（100字以内）",
  "caution": "誤読されやすい・からかわれやすいなど気をつけたい点（なければ空文字）",
  "scores": {"判断軸": 1〜5}}]}"""


def split_chars(text):
    """「翔、陽」→ ["翔", "陽"]（区切りの記号や空白を除いて1文字ずつ）"""
    return [c for c in text if c not in " 　、,・/"]


def clean_scores(scores, axes):
    """AIがつけた点数を、判断軸ごとに1〜5の整数にそろえる（点数がない軸は出さない）"""
    result = {}
    for axis in axes:
        try:
            result[axis] = min(5, max(1, round(float(scores[axis]))))
        except (KeyError, TypeError, ValueError):
            pass
    return result


def make_prompt(req):
    """画面で選んだ条件（req）から、AIへのお願いの文章を作る"""
    target = TARGETS[req["target"]]
    lines = [f"【対象】{target['label']}" + (f"（性別：{req['gender']}）" if req["gender"] != "指定なし" else ""),
             f"【ルール】{target['rule']}"]
    if req["target"] == "baby":
        if req["allow_ateji"]:
            lines.append("【読み】漢字の読みのほか、名付けで広く使われている読み（例：陽葵＝ひまり）も使ってよい")
        else:
            lines.append("【読み】各漢字の音読み・訓読み・名乗りで説明できる読みだけにする。当て字は使わない")
    if req["surname"]:
        lines.append(f"【苗字】{req['surname']}")
    lines.append(f"【イメージ】{'、'.join(req['tags']) or 'おまかせ'}")
    if req["wish"]:
        lines.append(f"【願い・詳細】{req['wish']}")
    if req["include"]:
        lines.append(f"【使いたい漢字】{'、'.join(split_chars(req['include']))}（このうちどれか1つを必ず使う）")
    if req["exclude"]:
        lines.append(f"【使わない漢字】{'、'.join(split_chars(req['exclude']))}")
    if req["length"]:
        lines.append(f"【文字数】{req['length']}文字")
    if req["image"]:
        lines.append("【画像】あり（画像の雰囲気や色も参考にする）")
    lines.append(f"【方向性】{'、'.join(target['directions'])}")
    lines.append(f"【判断軸】{'、'.join(req['axes'])}")
    if req["like"]:
        lines.append(f"【近づけたい名前】{req['like']['name']}（{req['like']['yomi']}）と、響き・雰囲気が近い別の名前にする")
    if req["shown"]:
        lines.append(f"【もう出した名前（使わない）】{'、'.join(req['shown'][-60:])}")
    lines.append("名前の候補を8つ考えてください。")
    return "\n".join(lines)


def check_name(item, req, shown):
    """1つの候補をチェックする。外すときはその理由を、問題なければ None を返す"""
    name, yomi = item["name"], item["yomi"]
    if not name or not yomi:
        return "AIの答えの形がおかしい"
    if name in shown or (req["like"] and name == req["like"]["name"]):
        return "もう出した名前"
    include, exclude = split_chars(req["include"]), split_chars(req["exclude"])
    if include and not any(c in name for c in include):
        return "使いたい漢字が入っていない"
    if any(c in name for c in exclude):
        return "避けたい漢字が入っている"
    if req["length"] and len(name) != req["length"]:
        return "文字数が違う"
    if req["target"] == "baby":
        if kc.bad_chars(name):
            return "名前に使えない字"
        if kc.ng_chars(name):
            return "名前に向かない字"
        item["check"] = kanji_info(name, yomi)
        if item["check"]["level"] == "⚠" and not req["allow_ateji"]:
            return "読みが漢字と合わない"
    return None


def generate(req):
    """AIに名前を考えてもらい、チェックに合格した名前と、外した数を返す（AIのエラーはそのまま投げる）"""
    target = TARGETS[req["target"]]
    data = ask_ai(GEN_SYSTEM, make_prompt(req), req["image"])
    shown = list(req["shown"])
    names, removed, skipped, total = [], {}, [], 0
    for raw in data.get("names", []):
        if not isinstance(raw, dict):
            continue
        total += 1
        item = {key: str(raw.get(key) or "").strip() for key in ["name", "yomi", "romaji", "catch", "reason", "caution"]}
        item["direction"] = raw.get("direction") if raw.get("direction") in target["directions"] else ""
        item["scores"] = clean_scores(raw.get("scores"), req["axes"])
        reason = check_name(item, req, shown)
        if reason:
            removed[reason] = removed.get(reason, 0) + 1
            if item["name"]:
                skipped.append(item["name"])  # 外した名前も、次から「もう出した名前」としてAIに伝える
        else:
            names.append(item)
            shown.append(item["name"])  # 同じ回の中で同じ名前が2回出ないように
    return {"names": names, "total": total, "removed": removed, "skipped": skipped}


# ---------------------------------------------------------------------
# 詳細診断
# ---------------------------------------------------------------------
DIAGNOSE_SYSTEM = """あなたは経験豊富なネーミングコンサルタントです。名前を多角的に診断して、JSONだけで答えてください。
・確実でないことは断定しない。外国語での意味は、確実に知っているものだけを書く
・良い点だけでなく、弱点やリスクも具体的に書く。お世辞は言わない
出力形式：
{"summary": "総評（2〜3文）", "scores": {"判断軸": {"score": 1〜5, "reason": "理由（1文）"}},
 "sound": "響きの分析", "meaning": "意味・由来", "risks": ["誤読やからかいにつながる点"],
 "global_risk": {"level": "低 / 中 / 高", "detail": "英語など他の言語での響きや意味"},
 "advice": "さらに良くするためのアドバイス", "alternatives": [{"name": "改善案", "yomi": "読み", "reason": "理由"}]}"""
DIAGNOSE_AXES = {
    "baby": ["響き", "意味・願い", "読みやすさ", "書きやすさ", "独自性"],
    "pet": ["呼びやすさ", "かわいさ", "覚えやすさ", "独自性"],
    "character": ["世界観との一致", "印象の強さ", "覚えやすさ", "独自性"],
    "brand": ["覚えやすさ", "発音しやすさ", "業種との一致", "独自性", "国際性"],
}


def diagnose(target, name, yomi, surname="", wish=""):
    """名前を診断して、レポートと（赤ちゃんなら）漢字チェックの結果を返す"""
    full_name = f"{surname} {name}" if surname else name
    user = (f"対象：{TARGETS[target]['label']}\n名前：{full_name}\n読み：{yomi}\n"
            f"込めた想い：{wish or 'なし'}\n判断軸：{'、'.join(DIAGNOSE_AXES[target])}")
    report = ask_ai(DIAGNOSE_SYSTEM, user)
    check = None
    if target == "baby":
        check = kanji_info(name, yomi)
        for alt in report.get("alternatives") or []:  # 改善案にも、漢字チェックの印をつける
            if isinstance(alt, dict):
                alt_name, alt_yomi = str(alt.get("name") or ""), str(alt.get("yomi") or "")
                alt["mark"] = "使えない字" if kc.bad_chars(alt_name) else kc.check_reading(alt_name, alt_yomi)[0]
    return {"report": report, "check": check}


# ---------------------------------------------------------------------
# 商標の事前チェック（AIの知識による。データベース照合ではない）
# ---------------------------------------------------------------------
TRADEMARK_SYSTEM = """あなたは商標に詳しいネーミングコンサルタントです。名前を商標の観点から事前チェックして、JSONだけで答えてください。
・あなたは商標データベースを見られないので、断定せず「可能性」として書く
・存在が不確かな商標や会社名を作らない。確実に知っている有名なものだけ挙げる（なければ空のリスト）
出力形式：
{"shoko": "呼び方（カタカナ）", "similar": ["似ていると判断されやすい呼び方"],
 "type": "一般名称に近い / 説明的 / 暗示的 / 造語 のどれか", "type_comment": "登録のされやすさについて",
 "conflicts": [{"name": "似ている有名ブランド", "comment": "理由"}], "keywords": ["J-PlatPatで検索するカタカナ"]}"""
TRADEMARK_CLASSES = ["第9類：アプリ・ソフトウェア", "第28類：おもちゃ・ゲーム機", "第35類：広告・小売・ネットショップ",
                     "第41類：教育・エンタメ", "第42類：Webサービス・IT", "第3類：化粧品", "第25類：衣服・靴",
                     "第30類：菓子・パン・コーヒー", "第43類：飲食店・宿泊", "第44類：美容・医療"]


def trademark(name, yomi, classes):
    user = f"名前：{name}\n読み：{yomi or '未入力（推定してください）'}\n分野：{'、'.join(classes) or '未指定'}"
    return ask_ai(TRADEMARK_SYSTEM, user)


# ---------------------------------------------------------------------
# ドメインの空き確認（RDAP：ドメインの登録情報を調べる仕組み）
# ---------------------------------------------------------------------
TLDS = [".com", ".jp", ".net", ".org", ".app", ".dev", ".io", ".ai"]


def to_domain_label(text):
    """「Namers AI」→「namers-ai」（ドメインに使える文字だけにする）"""
    text = re.sub(r"[\s_.]+", "-", (text or "").lower().strip())
    text = re.sub(r"[^a-z0-9-]", "", text)
    return re.sub(r"-{2,}", "-", text).strip("-")[:63]


def check_domains(base, tlds):
    results = []
    for tld in tlds:
        domain = base + tld
        try:
            r = requests.get(f"https://rdap.org/domain/{domain}", timeout=8)
            # rdap.org は、そのドメインを管理している登録所に転送してくれる。
            # 転送先で「見つからない（404）」なら空いている。転送されずに 404 なら、確認に対応していない種類
            if r.status_code == 200:
                results.append({"domain": domain, "status": "taken", "note": "すでに登録されています"})
            elif r.status_code == 404 and r.history:
                results.append({"domain": domain, "status": "available", "note": "空いている可能性があります"})
            else:
                results.append({"domain": domain, "status": "unknown",
                                "note": "確認できませんでした（この種類は確認に対応していない可能性があります）"})
        except requests.RequestException:
            results.append({"domain": domain, "status": "unknown", "note": "確認できませんでした"})
    return results

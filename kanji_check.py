# 漢字チェック
# AIが考えた赤ちゃんの名前を、漢字データ（kanji.json）で確かめる。
#
#  1. 名前に使える字か … 常用漢字・人名用漢字（kanji.json に載っている字）と、ひらがな・カタカナだけか
#  2. 読み方は自然か   … 名前の読みを、1字ずつの読み（音読み・訓読み・名乗り）に分けられるか
#       ◎ 辞書どおりの読み（音読み・訓読みだけで読める）
#       ○ 名前でよく使う読み（名乗りや、読みの一部を使っている。例：陽翔＝はると、心春＝こはる）
#       ⚠ 辞書の読みでは説明できない読み（当て字の可能性）
import json
from pathlib import Path

KANJI = json.loads((Path(__file__).parent / "kanji.json").read_text(encoding="utf-8"))

# 赤ちゃんの名前には使わない字（悪い意味が強いもの）
NG_KANJI = set("死亡殺病苦悪毒呪罪犯貧敗凶災禍痛墓腐堕奴喪葬棺怨憎嫌愚狂惨虐暴盗醜汚滅嘘妬憂傷損廃崩獄辱")

# 濁る音（連濁：はな → ばな）、半濁音（へい → ぺい）
DAKUTEN = dict(zip("かきくけこさしすせそたちつてとはひふへほ", "がぎぐげござじずぜぞだぢづでどばびぶべぼ"))
HANDAKUTEN = dict(zip("はひふへほ", "ぱぴぷぺぽ"))


def to_hiragana(text):
    """カタカナをひらがなにする（読みの比較用）"""
    return "".join(chr(ord(c) - 0x60) if "ァ" <= c <= "ヶ" else c for c in text)


def is_kana(ch):
    return "ぁ" <= ch <= "ゖ" or "ァ" <= ch <= "ヺ" or ch in "ーゝゞヽヾ"


def bad_chars(name):
    """名前に使えない字のリストを返す（空のリストなら、全部使える字）"""
    return [ch for ch in name if not (is_kana(ch) or ch == "々" or ch in KANJI)]


def ng_chars(name):
    """名前に向かない字のリストを返す"""
    return [ch for ch in name if ch in NG_KANJI]


def strokes(name):
    """漢字の画数の合計"""
    return sum(KANJI[ch]["画数"] for ch in name if ch in KANJI)


def readings(name, i):
    """name の i 文字目の読みの候補を、(読み, 種類) のリストで返す"""
    ch = name[i]
    if is_kana(ch):
        return [(to_hiragana(ch), "かな")]
    if ch == "々" and i > 0:  # 「菜々」の「々」は、前の字と同じ読み
        ch = name[i - 1]
    if ch not in KANJI:
        return []

    words = [(r, "音訓") for r in KANJI[ch]["音訓"]] + [(r, "名乗り") for r in KANJI[ch]["名乗り"]]
    result = list(words)
    for r, kind in words:
        # 読みの一部だけを使う（心 → こ）
        for n in range(1, len(r)):
            if r[n] not in "ゃゅょぁぃぅぇぉ":
                result.append((r[:n], "読みの一部"))
        # 「いち」→「いっ」のように、最後が「っ」になる（一平＝いっぺい）
        if len(r) >= 2 and r[-1] in "つちくき":
            result.append((r[:-1] + "っ", kind))
        # 2文字目からは、最初の音がにごることがある（はな → ばな、へい → ぺい）
        if i > 0 and r[0] in DAKUTEN:
            result.append((DAKUTEN[r[0]] + r[1:], kind))
        if i > 0 and r[0] in HANDAKUTEN:
            result.append((HANDAKUTEN[r[0]] + r[1:], kind))
    return result


def check_reading(name, yomi):
    """読みが漢字の読みで説明できるか調べる。
    戻り値：("◎" / "○" / "⚠", 内訳のリスト [(字, 読み, 種類), ...])
    """
    yomi = to_hiragana(yomi.replace(" ", "").replace("　", ""))
    memo = {}

    def search(i, j):
        # 名前の i 文字目から先を、読みの j 文字目から先で読めるか（読めたら一番良い読み方を返す）
        if i == len(name):
            return (0, []) if j == len(yomi) else None
        if (i, j) in memo:
            return memo[(i, j)]
        best = None
        for r, kind in readings(name, i):
            if yomi.startswith(r, j):
                rest = search(i + 1, j + len(r))
                if rest is None:
                    continue
                level = max(rest[0], 0 if kind in ("音訓", "かな") else 1)
                if best is None or level < best[0]:
                    best = (level, [(name[i], r, kind)] + rest[1])
        memo[(i, j)] = best
        return best

    found = search(0, 0)
    if found is None:
        return "⚠", []
    return ("◎" if found[0] == 0 else "○"), found[1]


READING_LABELS = {
    "◎": "◎ 辞書どおりの読み",
    "○": "○ 名前でよく使う読み",
    "⚠": "⚠ 辞書の読みでは説明できない読み",
}

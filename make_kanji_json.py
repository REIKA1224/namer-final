# kanji.json を作るためのスクリプト（アプリの実行には使いません）
#
# 漢字辞書 KANJIDIC2 から、子どもの名前に使える漢字（常用漢字・人名用漢字）だけを取り出して、
# 「画数」「区分」「音訓（音読み・訓読み）」「名乗り（名前で使う読み）」を kanji.json に保存します。
#
# 使い方：
#   pip install jamdict-data
#   python make_kanji_json.py
#   （インストールできない場合は、PyPI の jamdict-data のファイル jamdict_data-1.5.tar.gz を
#     ダウンロードして解凍し、中にある jamdict.db.xz をこのフォルダに置いてから実行してください）
#
# 辞書データ：Electronic Dictionary Research and Development Group（EDRDG）の KANJIDIC2・JMdict
#   CC BY-SA ライセンス（LICENSE-EDRDG.md）
import json
import lzma
import re
import sqlite3
import unicodedata
from pathlib import Path

# 辞書の版より後に人名用漢字に追加された字（2017年「渾」、2026年「勒」）
ADDED_JINMEIYO = {"渾", "勒"}


def hira(text):
    """カタカナをひらがなにする"""
    return "".join(chr(ord(c) - 0x60) if "ァ" <= c <= "ヶ" else c for c in text)


def nfc(text):
    return unicodedata.normalize("NFC", text)


def add(lst, value):
    if value and value not in lst:
        lst.append(value)


def open_db():
    """jamdict-data に入っている辞書データベース（圧縮されている）を展開して開く"""
    db_path = Path("jamdict.db")
    if not db_path.exists():
        xz_path = Path("jamdict.db.xz")
        if not xz_path.exists():
            import jamdict_data  # pip install jamdict-data でインストールしたもの

            xz_path = Path(jamdict_data.__file__).parent / "jamdict.db.xz"
        db_path.write_bytes(lzma.decompress(xz_path.read_bytes()))
    return sqlite3.connect(db_path)


def main():
    cur = open_db().cursor()
    kanji = {}

    # 1. KANJIDIC2：常用漢字（grade 1〜8）と人名用漢字（grade 9・10）
    for cid, literal, strokes, grade in cur.execute(
        "select ID, literal, stroke_count, grade from character"
    ).fetchall():
        ch = nfc(literal)
        if grade and grade.isdigit() and 1 <= int(grade) <= 8:
            kubun = "常用"
        elif grade in ("9", "10") or ch in ADDED_JINMEIYO:
            kubun = "人名用"
        else:
            continue
        entry = kanji.setdefault(ch, {"画数": strokes, "区分": kubun, "音訓": [], "名乗り": []})
        if kubun == "常用":
            entry["区分"] = "常用"  # 常用と人名用の両方に出てくる字は「常用」にする
        for (gid,) in cur.execute("select ID from rm_group where cid=?", (cid,)).fetchall():
            for r_type, value in cur.execute(
                "select r_type, value from reading where gid=? and r_type in ('ja_on', 'ja_kun')", (gid,)
            ).fetchall():
                value = hira(value).replace("-", "")
                if r_type == "ja_kun" and "." in value:
                    add(entry["音訓"], value.split(".")[0])  # 送り仮名の前まで（例：と.ぶ → と）
                    add(entry["音訓"], value.replace(".", ""))  # 送り仮名まで（例：とぶ）
                else:
                    add(entry["音訓"], value)
        for (value,) in cur.execute("select value from nanori where cid=?", (cid,)).fetchall():
            if hira(value) not in entry["音訓"]:
                add(entry["名乗り"], hira(value))

    # 2. JMdict：「碧い（あおい）」のような送り仮名つきの短い言葉から、訓読みを補う
    #    ・漢字の部分の読み（碧い → あお）を追加。2文字以上のものだけ
    #    ・送り仮名が「い」のとき（形容詞）は、送り仮名まで含めた読み（あおい）も追加
    kana_by_entry = {}
    for idseq, text in cur.execute("select idseq, text from Kana where nokanji = 0").fetchall():
        kana_by_entry.setdefault(idseq, []).append(hira(nfc(text)))
    for idseq, text in cur.execute("select idseq, text from Kanji").fetchall():
        m = re.fullmatch(r"(.)([ぁ-ゖ]{1,2})", nfc(text))
        if not m or m.group(1) not in kanji:
            continue
        ch, okuri = m.group(1), m.group(2)
        for reading in kana_by_entry.get(idseq, []):
            stem = reading[: -len(okuri)]
            if reading.endswith(okuri) and len(stem) >= 2 and re.fullmatch(r"[ぁ-ゖ]+", reading):
                add(kanji[ch]["音訓"], stem)
                if okuri == "い":
                    add(kanji[ch]["音訓"], reading)

    Path("kanji.json").write_text(json.dumps(kanji, ensure_ascii=False, indent=0), encoding="utf-8")
    joyo = sum(1 for v in kanji.values() if v["区分"] == "常用")
    print(f"kanji.json：{len(kanji)}字（常用 {joyo}字・人名用 {len(kanji) - joyo}字）")


if __name__ == "__main__":
    main()

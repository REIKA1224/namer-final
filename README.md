# 🪶 Namers AI ～AI名付け支援ツール～（Streamlit 版）

赤ちゃん・ペット・キャラクター・お店の名前を、AIが考えるWebアプリです。
登録なし・説明なしで、タグを選んでボタンを押すだけで使えます。

## できること

- 💡 **名前を考える**：対象とイメージ（タグ・文章・画像）から、AIが名前を提案。判断軸ごとに★5段階で評価
- 💎 **詳細診断**：考えた名前を、響き・意味・海外での印象などから診断してレポートにする
- 🔍 **商標・ドメイン**：商標のAI事前チェックと、ドメインの空き確認
- ⭐ **お気に入り**：気になる名前を保存して、3つまで比べる。CSVで保存・読み込みもできる

## しくみ

ひとことで言うと「全部 Python。画面は Streamlit、AIへの依頼と漢字チェックも Python、公開は Streamlit Community Cloud」です。

```
画面（app.py：Streamlit）
   │  ボタンを押すと、選んだ条件を logic.py に渡す
   ▼
logic.py（裏の処理）
   ├─ OpenAI の API に「名前を8つ、決まった形（JSON）で」と頼む
   ├─ 赤ちゃんの名前は kanji_check.py でチェック
   │    ・名前に使える字か …… 常用漢字・人名用漢字（2,943字）とかなだけか
   │    ・読み方は自然か …… 「陽翔＝はると」を「陽＝はる」「翔＝と」のように、
   │                         1字ずつの読み（音読み・訓読み・名乗り）に分けられるか
   └─ チェックに合格した名前だけを画面に返す
```

| ファイル | 中身 |
|---|---|
| `app.py` | 画面（Streamlit）。ボタンを押したときの流れ |
| `logic.py` | 裏の処理。AIへのお願い、名前のチェック、詳細診断、商標、ドメイン |
| `kanji_check.py` | 漢字チェック |
| `kanji.json` | 名前に使える漢字 2,943字の読みと画数（漢字辞書 KANJIDIC2 から作成） |
| `.streamlit/config.toml` | 画面の色の設定（緑を基本にする） |
| `requirements.txt` | 使うライブラリ |
| `make_kanji_json.py` | `kanji.json` を作ったスクリプト（アプリでは使わない） |
| `LICENSE-EDRDG.md` | 漢字データのライセンス |

## 公開のしかた（Streamlit Community Cloud）

### 1. GitHub に新しいリポジトリを作る

1. GitHub で「**New repository**」→ 名前を入れて「**Create repository**」
2. 「**uploading an existing file**」を押して、このフォルダの中身をドラッグ＆ドロップ →「**Commit changes**」
   - `app.py` がリポジトリのいちばん上に来るようにする（フォルダの中に入れない）
3. アップロードしたあと、リポジトリに `.streamlit` フォルダがあるか確認する。
   名前が「.」で始まるフォルダは、ドラッグ＆ドロップでは入らないことがあります。入っていなかったら：
   - 「**Add file**」→「**Create new file**」
   - 名前の欄に `.streamlit/config.toml` と入れる
   - 中身に、このフォルダの `.streamlit/config.toml` の中身をそのまま貼って「**Commit changes**」
   - なくてもアプリは動きますが、ボタンなどの色が Streamlit の標準（赤）になります

### 2. Streamlit Community Cloud で公開する

1. https://share.streamlit.io に GitHub でログイン
2. 「**Create app**」→ GitHub のリポジトリから作る方を選ぶ
3. Repository に作ったリポジトリ、Branch に `main`、Main file path に `app.py` を入れる
4. 「**Advanced settings**」の「**Secrets**」に、次のように書く

   ```toml
   OPENAI_API_KEY = "sk-で始まるキー"
   ```

   詳細診断にアクセスコードをつけるときは、`PREMIUM_CODE = "好きなコード"` の行も足します。
5. 「**Deploy**」を押すと、数分で `https://〇〇.streamlit.app` で公開される

GitHub のファイルを書きかえると、公開中のアプリにも自動で反映されます。
Secrets はあとから、アプリの「Settings」→「Secrets」で変えられます。

## 設定（Secrets）

| 名前 | 必須？ | 中身 |
|---|---|---|
| `OPENAI_API_KEY` | 必須 | OpenAI の APIキー。**コードや GitHub には絶対に書かない** |
| `PREMIUM_CODE` | 任意 | 詳細診断のアクセスコード。設定しなければ、詳細診断は誰でも使える |
| `OPENAI_MODEL` | 任意 | 使うAIのモデル名。設定しなければ `gpt-6-luna` |

> ⚠️ Streamlit Community Cloud の規約では、個人情報を扱う使い方の場合、
> 個人的で非商用の目的（試用・教育・家庭での利用など）に限るとされています。
> このアプリは苗字などを入力できるので、詳細診断のコードを有料で売るなら、規約を確認するか Streamlit に問い合わせてください。
> 参考：https://streamlit.io/deployment-terms-of-use

## 手元で動かす

```bash
pip install -r requirements.txt
# .streamlit/secrets.toml というファイルを作り、上の Secrets と同じ内容を書く（このファイルは GitHub に上げない）
streamlit run app.py
```

ブラウザで http://localhost:8501 が開きます。

## 知っておいてほしいこと

- **12時間アクセスがないと、アプリが眠ります。** 眠っているときは「Yes, get this app back up!」を押すと起きます（誰でも押せます）。起きるまで少し待ちます
- **お気に入りと履歴は、アプリを開いているあいだだけ残ります。** ページを開きなおすと消えるので、残したいときは CSV で保存してください。保存した CSV を「お気に入り」タブで読み込むと、お気に入りを戻せます
- 名前ができても、画面は自動でスクロールしません。「AIに名前を考えてもらう」ボタンのすぐ下に結果が出ます
- 写真を選ぶ欄の文字（Upload など）は、Streamlit の部品なので英語で表示されます
- 漢字チェックは辞書データによる目安です。出生届の受理や商標登録を保証するものではありません
- 辞書にない読みは、名付けでよく使われる読みでも「⚠」になります（例：陽葵＝ひまり、大和＝やまと、日向＝ひなた）。
  「⚙️ もっと細かく設定する」で「辞書にない読み（当て字など）の名前も出す」をオンにすると表示されます
- 商標チェックはAIの知識による事前チェックで、データベースとの照合ではありません
- ドメインの空き確認は rdap.org に問い合わせています。.jp など、確認できない種類もあります
- 使いすぎを防ぐため、同じ人が1時間に使える回数を決めています（名前を考える 30回、詳細診断 10回、商標 10回、ドメイン 30回）。
  サーバーが入れかわると数え直しになるので、目安です
- OpenAI の利用料金は、APIキーの持ち主に請求されます。OpenAI の管理画面で、月の使用額の上限を決めておくと安心です

## 漢字データのライセンス

`kanji.json` は、Electronic Dictionary Research and Development Group（EDRDG）の
KANJIDIC2・JMdict から作成し、同グループのライセンス（クリエイティブ・コモンズ 表示-継承）に従って使用しています。
詳しくは `LICENSE-EDRDG.md` と https://www.edrdg.org/edrdg/licence.html を見てください。

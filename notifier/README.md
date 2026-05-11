# 終電 LINE 通知

23:00 にスマホの位置情報を確認し、自宅から離れていたら終電情報を LINE に送ります。

## コスト

| サービス | 無料枠 | 実際の費用 |
|---------|--------|-----------|
| LINE Messaging API | 200通/月 | 無料 |
| Google Maps Directions API | $200/月クレジット | 実質無料（月30回≒$0.15） |
| Railway (ホスティング) | $5/月クレジット | 無料枠で収まる |

---

## セットアップ手順

### 1. LINE Messaging API の設定

1. [LINE Developers](https://developers.line.biz/) にアクセスし、LINEアカウントでログイン
2. **新しい Provider** を作成（名前は何でも可）
3. **Messaging API チャネル** を作成
   - チャネルの種類: Messaging API
   - チャネル名: 任意（例: 終電通知）
4. **チャネルアクセストークン** を発行（「チャネル設定」→「Messaging API設定」→下部で発行）
5. **自分の LINE User ID** を取得
   - 「LINE Developers コンソール」右上のアイコン → 「Your user ID」に表示される `U...` の文字列
6. 作成したボットを **LINE アプリで友だち追加**（QRコードはチャネル設定ページにあります）

```
LINE_CHANNEL_TOKEN = 手順4のトークン
LINE_USER_ID      = 手順5のUser ID（U で始まる文字列）
```

### 2. Google Maps API の設定（任意）

設定しない場合は Google Maps リンクのみ送信されます。設定すると出発・到着時刻も通知されます。

1. [Google Cloud Console](https://console.cloud.google.com/) でプロジェクト作成
2. 「Directions API」を有効化
3. APIキーを作成（「認証情報」→「APIキーを作成」）
4. **請求先アカウントを設定**（クレジットカード必要。月$200無料枠があるので実際には請求なし）

```
GOOGLE_MAPS_KEY = 作成したAPIキー
```

### 3. 自宅座標の確認

Google Maps で自宅を右クリック → 緯度・経度をコピー

```
HOME_LAT = 35.XXXX
HOME_LON = 139.XXXX
```

### 4. Railway へのデプロイ

1. [Railway](https://railway.app/) に GitHub アカウントでサインアップ
2. 「New Project」→「Deploy from GitHub repo」→ このリポジトリを選択
3. 「Root Directory」を `notifier` に設定
4. 「Variables」タブで環境変数を設定（`.env.example` の内容を参考に）
5. デプロイ完了後、「Settings」→「Public Networking」でドメインを発行
   - 例: `https://your-app.railway.app`

### 5. Android の自動化設定（MacroDroid）

[MacroDroid](https://play.google.com/store/apps/details?id=com.arlosoft.macrodroid) をインストールします（無料・マクロ5個まで無料枠で十分）。

デプロイ後の URL を `https://your-app.railway.app/notify` として使います。

#### 手順

**① 新しいマクロを作成**

MacroDroid を開き、右下の「＋」→「マクロを追加」

---

**② トリガーを設定**

「トリガーを追加」→「時計/カレンダー」→「指定時刻」
- 時刻: **23:00**
- 繰り返し: **毎日**

---

**③ アクションを設定（順番通りに追加）**

「アクションを追加」から以下を順に追加します。

**アクション 1: 現在地を取得**
- カテゴリ: 「位置情報」→「現在地の座標を取得」
- 保存先の変数名: `latitude`（緯度）、`longitude`（経度）を自動で保存

> ※ 位置情報の権限を「常に許可」にしておく必要があります
> （Android 設定 → アプリ → MacroDroid → 権限 → 位置情報 → 常に許可）

**アクション 2: HTTP リクエストを送信**
- カテゴリ: 「接続性」→「HTTP リクエスト」
- 設定内容:

| 項目 | 値 |
|------|-----|
| URL | `https://your-app.railway.app/notify` |
| HTTP メソッド | `POST` |
| ヘッダー（追加） | `Content-Type: application/json` |
| リクエスト本文 | 下記参照 |

リクエスト本文（コピー＆ペーストしてください）:
```
{"lat": {latitude}, "lon": {longitude}}
```
> `{latitude}` `{longitude}` は MacroDroid の変数記法です。そのまま入力してください。

---

**④ 制約を設定（任意・推奨）**

「制約を追加」→「電話/通話状態」→「通話中でない」を追加しておくと通話中に誤動作しません。

---

**⑤ マクロを保存**

名前（例: 終電通知）を入力して保存。トグルスイッチが ON になっていることを確認。

---

#### 動作確認

マクロ一覧でマクロを長押し → 「実行」で即時テストできます。
位置情報を取得しサーバーに送信、自宅から離れていれば LINE に通知が来ます。

---

## ローカルでのテスト

```bash
cd notifier
pip install -r requirements.txt
cp .env.example .env
# .env を編集して実際の値を設定

python app.py
```

別ターミナルでテスト（自宅から離れた座標を指定）:

```bash
# 自宅から離れた場所（通知が来るはず）
curl -X POST http://localhost:5000/notify \
  -H "Content-Type: application/json" \
  -d '{"lat": 35.6812, "lon": 139.7671}'

# 自宅付近（通知が来ないはず）
curl -X POST http://localhost:5000/notify \
  -H "Content-Type: application/json" \
  -d '{"lat": YOUR_HOME_LAT, "lon": YOUR_HOME_LON}'
```

---

## 通知例

```
【終電アラート】
自宅まで約 8.3km

出発: 23:12
到着: 00:04 (52分)
経路: 23:12 渋谷→新宿(埼京線) / 23:31 新宿→○○(中央線)

https://www.google.com/maps/dir/?...
```

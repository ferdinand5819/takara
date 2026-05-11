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

### 5. スマホの自動化設定

デプロイ後の URL を `https://your-app.railway.app/notify` として使います。

#### iPhone (ショートカット)

1. **ショートカット** アプリ → 「オートメーション」タブ → 「+」
2. 「時刻」→ 23:00 に設定 → 「毎日」
3. 以下のアクションを追加:

```
[現在地を取得]
   ↓
[変数を設定: myLocation = 現在地]
   ↓
[URLの内容を取得]
   URL: https://your-app.railway.app/notify
   方法: POST
   ヘッダー: Content-Type = application/json
   本文(JSON):
     lat = [マジック変数: myLocation の 緯度]
     lon = [マジック変数: myLocation の 経度]
```

**具体的な手順:**
1. アクション追加 →「現在地を取得」を検索して追加
2. アクション追加 →「URLの内容を取得」を追加
   - URL に `https://your-app.railway.app/notify` を入力
   - 「詳細を表示」→ 方法: `POST`
   - ヘッダー: `Content-Type` / `application/json`
   - 本文: `JSON` を選択
     - キー `lat`、値: 「現在地を取得」の結果から「緯度」（変数アイコンをタップして選択）
     - キー `lon`、値: 同様に「経度」

#### Android (Tasker ※無料の MacroDroid でも可)

**MacroDroid（無料）の場合:**

1. MacroDroid をインストール
2. 「マクロを追加」
3. **トリガー**: 「時計/日付」→「時刻を指定」→ 23:00
4. **アクション**:
   - 「接続性」→「HTTP リクエスト」
   - URL: `https://your-app.railway.app/notify`
   - 方法: POST
   - 本文（JSON）:
     ```json
     {"lat": "[location_latitude]", "lon": "[location_longitude]"}
     ```
   - ※ MacroDroid の変数: `{location_latitude}`, `{location_longitude}`

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

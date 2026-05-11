# 終電 LINE 通知

**追加アプリのインストール不要。** LINE だけで動きます。

## 動作の流れ

2つのモードがあります。好きな方を選んでください。

### モード A：LINE のみ（タップ1回必要）
```
23:00 サーバーが自動で LINE に送信
  「現在地を送ってください 📍」
        ↓
  LINE の「＋」→「位置情報」をタップ（5秒）
        ↓
  自宅付近 → 「おつかれさまでした！」
  離れてる → 「【終電アラート】出発 23:12 / 到着 00:04 ...」
```

### モード B：MacroDroid（完全自動・タップ不要）
```
23:00 MacroDroid が自動で GPS 取得 → サーバーへ送信
        ↓（何もしなくてよい）
  自宅付近 → 何も来ない
  離れてる → 「【終電アラート】出発 23:12 / 到着 00:04 ...」
```
> MacroDroid は無料アプリ（マクロ5個まで無料枠）

## コスト

| サービス | 無料枠 | 実際の費用 |
|---------|--------|-----------|
| LINE Messaging API | 200通/月 | 無料 |
| Google Maps Directions API | $200/月クレジット | 実質無料（月60回≒$0.30） |
| Railway (ホスティング) | $5/月クレジット | 無料枠で収まる |

---

## セットアップ手順

### 1. LINE Messaging API の設定

1. [LINE Developers](https://developers.line.biz/) にアクセス → LINE アカウントでログイン
2. **新しい Provider を作成**（名前は何でも可）
3. **「Messaging API」チャネルを作成**
   - チャネルの種類: Messaging API
   - チャネル名: 任意（例: 終電通知）
4. 「**チャネル基本設定**」タブ → **チャネルシークレット**をコピー
5. 「**Messaging API 設定**」タブ → 一番下の「**チャネルアクセストークン（長期）**」を発行 → コピー
6. 同ページの **Webhook URL** 欄に、Railway デプロイ後の URL を設定（後述）
   - 例: `https://your-app.railway.app/webhook`
   - 「Webhook の利用」を **ON** にする
7. **自分の LINE User ID を取得**
   - コンソール右上のアイコン → **「Your user ID」** に表示される `U` で始まる文字列
8. 作成したボットを **LINE で友だち追加**（チャネル設定ページの QR コードから）

```
LINE_CHANNEL_SECRET = 手順4のチャネルシークレット
LINE_CHANNEL_TOKEN  = 手順5のチャネルアクセストークン
LINE_USER_ID        = 手順7のUser ID（U で始まる文字列）
```

---

### 2. Google Maps API の設定（任意）

設定しない場合は Google マップのリンクだけ送信されます。  
設定すると **出発・到着時刻・乗換路線** も通知に含まれます。

1. [Google Cloud Console](https://console.cloud.google.com/) でプロジェクト作成
2. 「Directions API」を有効化
3. 「認証情報」→「APIキーを作成」
4. **請求先アカウントを設定**（カード登録必要。月 $200 無料枠があるので実際には無料）

```
GOOGLE_MAPS_KEY = 作成した API キー
```

---

### 3. 自宅座標の確認

Google Maps で自宅を長押し → 緯度・経度をコピー

```
HOME_LAT = 35.XXXX
HOME_LON = 139.XXXX
```

---

### 4. Railway へのデプロイ

1. [Railway](https://railway.app/) に GitHub アカウントでサインアップ
2. 「New Project」→「Deploy from GitHub repo」→ このリポジトリを選択
3. 「**Root Directory**」を `notifier` に設定
4. 「**Variables**」タブで環境変数を設定（`.env.example` を参考に）
5. デプロイ完了後、「**Settings**」→「**Public Networking**」でドメインを発行
   - 例: `https://your-app.railway.app`
6. 発行した URL + `/webhook` を LINE Developers の Webhook URL に設定（手順1-6）

---

### 5. 動作確認

LINE でボットに **テキストメッセージ** を送っても反応しません（位置情報のみ処理します）。

位置情報を送って試してみてください：

- LINE でボットのトーク画面を開く
- 「＋」→「位置情報」→ 現在地または任意の場所を送信
- 自宅から離れた座標なら終電情報が返ってくれば成功

---

## モード B：MacroDroid の設定（完全自動）

[MacroDroid](https://play.google.com/store/apps/details?id=com.arlosoft.macrodroid) をインストール（無料）。

### 手順

**① 新しいマクロを作成**

右下の「＋」→「マクロを追加」

**② トリガー**

「トリガーを追加」→「時計/カレンダー」→「指定時刻」→ **23:00 / 毎日**

**③ アクション（順番に追加）**

アクション 1：**現在地を取得**
- 「位置情報」→「現在地の座標を取得」
- 緯度が `{latitude}`、経度が `{longitude}` に保存される

> 事前に Android 設定 → アプリ → MacroDroid → 権限 → 位置情報 → **「常に許可」** にしておく

アクション 2：**HTTP リクエスト**
- 「接続性」→「HTTP リクエスト」

| 項目 | 値 |
|------|-----|
| URL | `https://your-app.railway.app/notify` |
| メソッド | `POST` |
| ヘッダー | `Content-Type: application/json` |
| 本文 | `{"lat": {latitude}, "lon": {longitude}}` |

**④ マクロを保存・ON にする**

マクロ一覧で長押し →「実行」で即時テストできます。

---

## ローカルでのテスト

```bash
cd notifier
pip install -r requirements.txt
cp .env.example .env
# .env を実際の値で編集

python app.py
```

webhook のテスト（curl）:

```bash
# 自宅から離れた場所をシミュレート
curl -X POST http://localhost:5000/webhook \
  -H "Content-Type: application/json" \
  -H "X-Line-Signature: dummy" \
  -d '{
    "events": [{
      "type": "message",
      "replyToken": "dummy",
      "message": {"type": "location", "latitude": 35.6812, "longitude": 139.7671}
    }]
  }'
```

> ローカルテストは署名検証をスキップするため、本番では必ず Railway にデプロイして使ってください。

---

## 通知例

**23:00 に届くメッセージ**
```
終電チェック 🚃
現在地を送ってください📍

LINE の「＋」ボタン →「位置情報」をタップ
```

**位置情報を送ったときの返信（自宅外の場合）**
```
【終電アラート】
自宅まで約 8.3km

出発: 23:12
到着: 00:04 (52分)
経路: 23:12 渋谷→新宿(山手線) / 23:28 新宿→○○(中央線)

https://www.google.com/maps/dir/?...
```

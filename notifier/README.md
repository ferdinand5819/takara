# 終電 LINE 通知（MacroDroid）

23:00 に Android が自動で位置情報を取得し、自宅から離れていたら終電情報を LINE に送ります。

## 動作の流れ

```
23:00 MacroDroid が自動で GPS 取得 → サーバーへ送信
        ↓（何もしなくてよい）
  自宅付近 → 何も来ない
  離れてる → LINE に終電アラート
```

## コスト

| サービス | 費用 |
|---------|------|
| MacroDroid | 無料（マクロ5個まで） |
| LINE Messaging API | 無料（200通/月） |
| Google Maps Directions API | 実質無料（月$200クレジット内） |
| Railway | 無料枠で収まる |

---

## セットアップ手順

### 1. LINE Messaging API の設定

1. [LINE Developers](https://developers.line.biz/) にアクセス → LINE アカウントでログイン
2. **新しい Provider を作成**（名前は何でも可）
3. **「Messaging API」チャネルを作成**
4. 「**Messaging API 設定**」タブ → **チャネルアクセストークン（長期）** を発行 → コピー
5. **自分の LINE User ID を取得**
   - コンソール右上のアイコン → **「Your user ID」**（`U` で始まる文字列）
6. 作成したボットを **LINE で友だち追加**（チャネル設定ページの QR コードから）

```
LINE_CHANNEL_TOKEN = 手順4のトークン
LINE_USER_ID       = 手順5のUser ID
```

---

### 2. Google Maps API の設定（任意）

設定しない場合は Google マップのリンクのみ送信されます。  
設定すると **出発・到着時刻・乗換路線** も通知に含まれます。

1. [Google Cloud Console](https://console.cloud.google.com/) でプロジェクト作成
2. 「Directions API」を有効化
3. 「認証情報」→「APIキーを作成」
4. 請求先アカウントを設定（月 $200 無料枠があるので実際には無料）

```
GOOGLE_MAPS_KEY = 作成した API キー
```

---

### 3. 自宅座標の確認

Google マップで自宅を長押し → 緯度・経度をコピー

```
HOME_LAT = 35.XXXX
HOME_LON = 139.XXXX
```

---

### 4. SECRET_TOKEN を決める

MacroDroid からのリクエストを認証するための文字列です。  
英数字でランダムな文字列を自分で決めてください（例: `abc123xyz`）。

```
SECRET_TOKEN = 自分で決めた文字列
```

---

### 5. Railway へのデプロイ

1. [Railway](https://railway.app/) に GitHub アカウントでサインアップ
2. 「New Project」→「Deploy from GitHub repo」→ このリポジトリを選択
3. 「**Root Directory**」を `notifier` に設定
4. 「**Variables**」タブで環境変数を設定（`.env.example` を参考に）
5. デプロイ完了後、「**Settings**」→「**Public Networking**」でドメインを発行
   - 例: `https://your-app.railway.app`

---

### 6. MacroDroid の設定

[MacroDroid](https://play.google.com/store/apps/details?id=com.arlosoft.macrodroid) をインストール。

**事前準備：位置情報の権限設定**

Android 設定 → アプリ → MacroDroid → 権限 → 位置情報 → **「常に許可」**

---

**① 新しいマクロを作成**

右下の「＋」→「マクロを追加」

**② トリガー**

「トリガーを追加」→「時計/カレンダー」→「指定時刻」→ **23:00 / 毎日**

**③ アクション 1：現在地を取得**

「アクションを追加」→「位置情報」→「現在地の座標を取得」

- 緯度が `{latitude}`、経度が `{longitude}` に自動保存される

**④ アクション 2：HTTP リクエスト**

「アクションを追加」→「接続性」→「HTTP リクエスト」

| 項目 | 値 |
|------|-----|
| URL | `https://your-app.railway.app/notify` |
| メソッド | `POST` |
| ヘッダー | `Content-Type: application/json` |
| 本文 | 下記参照 |

本文（コピー＆ペースト）:
```
{"token": "your_secret_token_here", "lat": {latitude}, "lon": {longitude}}
```
> `your_secret_token_here` の部分は手順4で決めた SECRET_TOKEN に書き換えてください

**⑤ 保存・ON にする**

マクロ一覧でマクロを長押し →「実行」で即時テストできます。

---

## ローカルでのテスト

```bash
cd notifier
pip install -r requirements.txt
cp .env.example .env
# .env を実際の値で編集

python app.py
```

別ターミナルでテスト:

```bash
# 自宅から離れた場所（通知が来るはず）
curl -X POST http://localhost:5000/notify \
  -H "Content-Type: application/json" \
  -d '{"token": "your_secret_token_here", "lat": 35.6812, "lon": 139.7671}'

# 自宅付近（通知が来ないはず）
curl -X POST http://localhost:5000/notify \
  -H "Content-Type: application/json" \
  -d '{"token": "your_secret_token_here", "lat": 35.6762, "lon": 139.6503}'
```

---

## 通知例

```
【終電アラート】
自宅まで約 8.3km

出発: 23:12
到着: 00:04 (52分)
経路: 23:12 渋谷→新宿(山手線) / 23:28 新宿→○○(中央線)

https://www.google.com/maps/dir/?...
```

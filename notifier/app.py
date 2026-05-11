import base64
import hashlib
import hmac
import math
import os

import requests
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from flask import Flask, request, jsonify
import pytz

app = Flask(__name__)

HOME_LAT = float(os.environ["HOME_LAT"])
HOME_LON = float(os.environ["HOME_LON"])
HOME_RADIUS_KM = float(os.environ.get("HOME_RADIUS_KM", "0.5"))
LINE_CHANNEL_TOKEN = os.environ["LINE_CHANNEL_TOKEN"]
LINE_CHANNEL_SECRET = os.environ["LINE_CHANNEL_SECRET"]
LINE_USER_ID = os.environ["LINE_USER_ID"]
GOOGLE_MAPS_KEY = os.environ.get("GOOGLE_MAPS_KEY", "")

JST = pytz.timezone("Asia/Tokyo")


# ── ユーティリティ ─────────────────────────────────────────

def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(d_lon / 2) ** 2
    )
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def verify_line_signature(body_bytes: bytes, signature: str) -> bool:
    digest = hmac.new(
        LINE_CHANNEL_SECRET.encode(), body_bytes, hashlib.sha256
    ).digest()
    return base64.b64encode(digest).decode() == signature


def build_maps_url(lat, lon):
    return (
        f"https://www.google.com/maps/dir/?api=1"
        f"&origin={lat},{lon}"
        f"&destination={HOME_LAT},{HOME_LON}"
        f"&travelmode=transit"
    )


# ── Google Maps ────────────────────────────────────────────

def fetch_transit_route(origin_lat, origin_lon):
    if not GOOGLE_MAPS_KEY:
        return None
    try:
        resp = requests.get(
            "https://maps.googleapis.com/maps/api/directions/json",
            params={
                "origin": f"{origin_lat},{origin_lon}",
                "destination": f"{HOME_LAT},{HOME_LON}",
                "mode": "transit",
                "departure_time": "now",
                "language": "ja",
                "key": GOOGLE_MAPS_KEY,
            },
            timeout=10,
        )
        data = resp.json()
    except requests.RequestException:
        return None

    if data.get("status") != "OK" or not data.get("routes"):
        return None

    leg = data["routes"][0]["legs"][0]
    steps = [
        (
            f"{s['transit_details']['departure_time']['text']} "
            f"{s['transit_details']['departure_stop']['name']}"
            f"→{s['transit_details']['arrival_stop']['name']}"
            f"({s['transit_details']['line'].get('short_name') or s['transit_details']['line']['name']})"
        )
        for s in leg.get("steps", [])
        if s.get("travel_mode") == "TRANSIT"
    ]
    return {
        "departure": leg["departure_time"]["text"],
        "arrival": leg["arrival_time"]["text"],
        "duration": leg["duration"]["text"],
        "steps": " / ".join(steps) if steps else "",
    }


# ── LINE メッセージ送受信 ──────────────────────────────────

def push_line_message(text):
    requests.post(
        "https://api.line.me/v2/bot/message/push",
        headers={
            "Authorization": f"Bearer {LINE_CHANNEL_TOKEN}",
            "Content-Type": "application/json",
        },
        json={"to": LINE_USER_ID, "messages": [{"type": "text", "text": text}]},
        timeout=10,
    ).raise_for_status()


def reply_line_message(reply_token, text):
    requests.post(
        "https://api.line.me/v2/bot/message/reply",
        headers={
            "Authorization": f"Bearer {LINE_CHANNEL_TOKEN}",
            "Content-Type": "application/json",
        },
        json={"replyToken": reply_token, "messages": [{"type": "text", "text": text}]},
        timeout=10,
    ).raise_for_status()


# ── 終電情報メッセージ生成 ────────────────────────────────

def build_train_message(lat, lon):
    distance = haversine_km(lat, lon, HOME_LAT, HOME_LON)
    maps_url = build_maps_url(lat, lon)

    if distance <= HOME_RADIUS_KM:
        return None  # 自宅付近 → 通知不要

    route = fetch_transit_route(lat, lon)
    if route:
        steps_line = f"\n経路: {route['steps']}" if route["steps"] else ""
        return (
            f"【終電アラート】\n"
            f"自宅まで約 {distance:.1f}km\n\n"
            f"出発: {route['departure']}\n"
            f"到着: {route['arrival']} ({route['duration']})"
            f"{steps_line}\n\n"
            f"{maps_url}"
        )
    return (
        f"【終電アラート】\n"
        f"自宅まで約 {distance:.1f}km\n\n"
        f"早めに帰宅手段を確認してください！\n\n"
        f"{maps_url}"
    )


# ── スケジューラー（23:00 に現在地リクエストを送信）──────

def request_location():
    push_line_message(
        "終電チェック 🚃\n"
        "現在地を送ってください📍\n\n"
        "LINE の「＋」ボタン →「位置情報」をタップ"
    )


scheduler = BackgroundScheduler(timezone=JST)
scheduler.add_job(request_location, CronTrigger(hour=23, minute=0, timezone=JST))
scheduler.start()


# ── エンドポイント ────────────────────────────────────────

@app.route("/webhook", methods=["POST"])
def webhook():
    signature = request.headers.get("X-Line-Signature", "")
    if not verify_line_signature(request.data, signature):
        return jsonify({"error": "invalid signature"}), 403

    body = request.get_json(force=True, silent=True) or {}
    for event in body.get("events", []):
        if event.get("type") != "message":
            continue
        msg = event.get("message", {})
        if msg.get("type") != "location":
            continue

        lat = msg["latitude"]
        lon = msg["longitude"]
        reply_token = event["replyToken"]

        train_msg = build_train_message(lat, lon)
        if train_msg:
            reply_line_message(reply_token, train_msg)
        else:
            reply_line_message(reply_token, "自宅付近です。おつかれさまでした！")

    return jsonify({"status": "ok"})


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

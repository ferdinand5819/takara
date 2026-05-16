import math
import os

import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

HOME_LAT = float(os.environ["HOME_LAT"])
HOME_LON = float(os.environ["HOME_LON"])
HOME_RADIUS_KM = float(os.environ.get("HOME_RADIUS_KM", "0.5"))
LINE_CHANNEL_TOKEN = os.environ["LINE_CHANNEL_TOKEN"]
LINE_USER_ID = os.environ["LINE_USER_ID"]
GOOGLE_MAPS_KEY = os.environ.get("GOOGLE_MAPS_KEY", "")
SECRET_TOKEN = os.environ["SECRET_TOKEN"]


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


def build_maps_url(lat, lon):
    return (
        f"https://www.google.com/maps/dir/?api=1"
        f"&origin={lat},{lon}"
        f"&destination={HOME_LAT},{HOME_LON}"
        f"&travelmode=transit"
    )


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


@app.route("/notify", methods=["POST"])
def notify():
    body = request.get_json(force=True, silent=True) or {}

    if body.get("token") != SECRET_TOKEN:
        return jsonify({"error": "unauthorized"}), 401

    try:
        lat = float(body["lat"])
        lon = float(body["lon"])
    except (KeyError, ValueError):
        return jsonify({"error": "lat と lon が必要です", "received": body}), 400

    distance = haversine_km(lat, lon, HOME_LAT, HOME_LON)

    if distance <= HOME_RADIUS_KM:
        return jsonify({"status": "home", "distance_km": round(distance, 2)})

    maps_url = build_maps_url(lat, lon)
    route = fetch_transit_route(lat, lon)

    if route:
        steps_line = f"\n経路: {route['steps']}" if route["steps"] else ""
        msg = (
            f"【終電アラート】\n"
            f"自宅まで約 {distance:.1f}km\n\n"
            f"出発: {route['departure']}\n"
            f"到着: {route['arrival']} ({route['duration']})"
            f"{steps_line}\n\n"
            f"{maps_url}"
        )
    else:
        msg = (
            f"【終電アラート】\n"
            f"自宅まで約 {distance:.1f}km\n\n"
            f"早めに帰宅手段を確認してください！\n\n"
            f"{maps_url}"
        )

    push_line_message(msg)
    return jsonify({"status": "notified", "distance_km": round(distance, 2)})


_stored_uid = None


@app.route("/webhook", methods=["POST"])
def webhook():
    """LINE User ID 取得用（設定完了後に削除可）"""
    global _stored_uid
    body = request.get_json(force=True, silent=True) or {}
    for event in body.get("events", []):
        uid = event.get("source", {}).get("userId")
        if uid:
            _stored_uid = uid
    return jsonify({"status": "ok"})


@app.route("/uid")
def get_uid():
    """取得した User ID を表示する（設定完了後に削除可）"""
    if _stored_uid:
        return jsonify({"user_id": _stored_uid})
    return jsonify({"user_id": None, "message": "まだ受信していません。LINEでメッセージを送ってください。"})


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

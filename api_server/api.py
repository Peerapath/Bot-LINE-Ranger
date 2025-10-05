from flask import Flask, request, jsonify
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
import os

app = Flask(__name__)

# ✅ เชื่อมต่อ Firestore
cred = credentials.Certificate("botranger-firebase-adminsdk-fbsvc-0ead8853b0.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

@app.route("/check-subscription", methods=["POST"])
def check_subscription():
    data = request.get_json()
    username = data.get("username")
    service_id = data.get("service_id")

    if not username or not service_id:
        return jsonify({"message": "ข้อมูลไม่ครบ", "status": "error"}), 400

    # 🔍 ดึงข้อมูลผู้ใช้จาก users/{username}
    user_ref = db.collection("users").document(username)
    user_doc = user_ref.get()
    if not user_doc.exists:
        return jsonify({"message": "ไม่พบผู้ใช้", "status": "error"}), 404

    user_data = user_doc.to_dict()
    email = user_data.get("email")
    if not email:
        return jsonify({"message": "ผู้ใช้นี้ไม่มี email", "status": "error"}), 400

    if user_data.get("status") == "banned":
        return jsonify({"message": "บัญชีถูกระงับการใช้งาน", "status": "banned"}), 403

    # 🔍 ตรวจสอบว่าผู้ใช้มี subscription ที่ยัง active หรือไม่
    subs_ref = db.collection("subscriptions")
    subs_query = subs_ref.where("email", "==", email).where("service_id", "==", service_id).get()

    if not subs_query:
        return jsonify({"message": "ไม่พบข้อมูลการเช่า", "status": "error"}), 404

    # ✅ ตรวจสอบวันหมดอายุ
    sub_data = subs_query[0].to_dict()
    end_date = sub_data["end_date"].replace(tzinfo=None)
    now = datetime.utcnow()

    if sub_data["status"] != "active" or now > end_date:
        return jsonify({
            "message": "การเช่าหมดอายุแล้ว",
            "status": "expired",
            "end_date": end_date.strftime("%Y-%m-%d")
        }), 403

    return jsonify({
        "message": "ยืนยันสิทธิ์สำเร็จ",
        "status": "ok",
        "start_date": sub_data["start_date"].strftime("%Y-%m-%d"),
        "end_date": sub_data["end_date"].strftime("%Y-%m-%d")
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

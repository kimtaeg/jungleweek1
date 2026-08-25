from flask import Flask, render_template, request, jsonify, session
from dotenv import load_dotenv
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timezone
import os
app = Flask(__name__)

load_dotenv()
app.secret_key = os.getenv("SECRET_KEY", "dev-secret-key-change-me")
client = MongoClient(os.getenv("MONGO_URI"))
db = client.dbjungle

@app.route('/')
def login():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login_submit():
    data = request.get_json(silent=True) or {}
    login_id = (data.get('login_id') or '').strip()
    user_pwd = data.get('user_pwd') or ''

    if not login_id or not user_pwd:
        return jsonify({"message": "아이디와 비밀번호를 입력해주세요"}), 400

    user = db.user.find_one({"login_id": login_id})
    if not user or not check_password_hash(user['user_pwd'], user_pwd):
        return jsonify({"message": "아이디 또는 비밀번호가 올바르지 않습니다"}), 401

    session['user_id'] = str(user['_id'])
    session['login_id'] = user['login_id']
    return jsonify({"message": "로그인되었습니다"}), 200

@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({"message": "로그아웃되었습니다"}), 200

@app.route('/check_id')
def check_id():
    login_id = (request.args.get('login_id') or '').strip()
    if not login_id:
        return jsonify({"message": "아이디를 입력해주세요"}), 400

    exists = db.user.find_one({"login_id": login_id}) is not None
    if exists:
        return jsonify({"available": False, "message": "이미 사용 중인 아이디입니다"})
    return jsonify({"available": True, "message": "사용 가능한 아이디입니다"})

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'GET':
        return render_template('signup.html')

    data = request.get_json(silent=True) or {}
    login_id = (data.get('login_id') or '').strip()
    username = (data.get('username') or '').strip()
    user_pwd = data.get('user_pwd') or ''

    if not login_id or not username or not user_pwd:
        return jsonify({"message": "모든 항목을 입력해주세요"}), 400

    if db.user.find_one({"login_id": login_id}):
        return jsonify({"message": "이미 사용 중인 아이디입니다"}), 409

    db.user.insert_one({
        "login_id": login_id,
        "username": username,
        "user_pwd": generate_password_hash(user_pwd),
        "created_at": datetime.now(timezone.utc)
    })
    return jsonify({"message": "회원가입이 완료되었습니다"}), 200

@app.route('/post_detail')
def postDetail():
    return render_template('post_detail.html')
if __name__ == '__main__':
    app.run(debug=True, port=5001)
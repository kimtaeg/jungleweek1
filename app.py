from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from dotenv import load_dotenv
from pymongo import MongoClient
from bson import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timezone
import api.blog as blog_api
import api.guestbook as guestbook_api
import api.neighbor as neighbor_api
import os
import re


app = Flask(__name__)

DEFAULT_PROFILE_COLOR = "#E68485"
DEFAULT_PROFILE_DESC = "오늘도 몽글몽글하게:)"
COLOR_RE = re.compile(r'^#[0-9A-Fa-f]{6}$')

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

#중복확인
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

@app.route('/post_detail/<post_id>')
def post_detail(post_id):
    post = db.blog.find_one({"_id": ObjectId(post_id)})
    if not post:
        return jsonify({"message": "게시글을 찾을 수 없습니다"}), 404

    user_id = session.get('user_id')
    liked = bool(user_id) and user_id in post.get('liked_by', [])

    return render_template(
        'post_detail.html',
        title=post['title'],
        content=post['content'],
        likes=post.get('likes', 0),
        created_at=post['created_at'],
        post_id=str(post['_id']),
        liked=liked
    )

@app.route('/posts/<post_id>/like', methods=['POST'])
def like_post(post_id):
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"message": "로그인이 필요합니다"}), 401

    post = db.blog.find_one({"_id": ObjectId(post_id)})
    if not post:
        return jsonify({"message": "게시글을 찾을 수 없습니다"}), 404

    likes = post.get("likes", 0)
    if user_id not in post.get("liked_by", []):
        db.blog.update_one(
            {"_id": ObjectId(post_id)},
            {"$inc": {"likes": 1}, "$addToSet": {"liked_by": user_id}}
        )
        likes += 1

    return jsonify({"likes": likes, "liked": True}), 200

#좋아요 취소
@app.route('/posts/<post_id>/unlike', methods=['POST'])
def unlike_post(post_id):
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"message": "로그인이 필요합니다"}), 401

    post = db.blog.find_one({"_id": ObjectId(post_id)})
    if not post:
        return jsonify({"message": "게시글을 찾을 수 없습니다"}), 404

    likes = post.get("likes", 0)
    if user_id in post.get("liked_by", []):
        db.blog.update_one(
            {"_id": ObjectId(post_id)},
            {"$inc": {"likes": -1}, "$pull": {"liked_by": user_id}}
        )
        likes -= 1

    return jsonify({"likes": likes, "liked": False}), 200

@app.route('/blog_post')
def blogPost():
    user = None
    user_id = session.get('user_id')
    if user_id:
        user = db.user.find_one({"_id": ObjectId(user_id)})

    username = user['username'] if user else '몽글몽글'
    profile_color = (user or {}).get('profile_color', DEFAULT_PROFILE_COLOR)
    profile_desc = (user or {}).get('profile_desc', DEFAULT_PROFILE_DESC)

    neighbor_count = neighbor_api.count_neighbors(user_id) if user_id else 0
    all_users = neighbor_api.get_all_users(user_id) if user_id else []
    neighbor_list = neighbor_api.get_neighbors(user_id) if user_id else []
    stats = {"posts": db.blog.count_documents({}), "neighbors": neighbor_count, "visitors": 0}

    # /api/blog.py의 get_blogs 함수 호출 (db에서 블로그 불러오기)
    posted_blogs = blog_api.get_blogs()
    guestbook_entries = guestbook_api.get_guestbooks()[:3]

    return render_template(
        'blog_post.html',
        stats=stats,
        posts=posted_blogs,  # blog_post.html에 블로그 전달
        guestbook_entries=guestbook_entries,
        is_neighbor=False,
        all_users=all_users,
        neighbor_list=neighbor_list,
        username=username,
        profile_color=profile_color,
        profile_desc=profile_desc,
        active_page='blog'
    )

@app.route('/profile/update', methods=['POST'])
def update_profile():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"message": "로그인이 필요합니다"}), 401

    data = request.get_json(silent=True) or {}
    username = (data.get('username') or '').strip()
    description = (data.get('description') or '').strip()
    color = (data.get('color') or '').strip()

    if not username or not description or not COLOR_RE.match(color):
        return jsonify({"message": "입력값을 확인해주세요"}), 400

    db.user.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {
            "username": username,
            "profile_desc": description,
            "profile_color": color
        }}
    )

    return jsonify({
        "message": "저장되었습니다",
        "username": username,
        "profile_desc": description,
        "profile_color": color
    }), 200

@app.route('/writing')
def writing():
    return render_template('writing.html')

@app.route('/add_neighbor', methods=['POST'])
def add_neighbor():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"message": "로그인이 필요합니다"}), 401

    data = request.get_json(silent=True) or {}
    target_id = data.get('target_id')
    if not target_id:
        return jsonify({"message": "대상 회원이 없습니다"}), 400

    neighbor_api.add_neighbor(user_id, target_id)
    return jsonify({
        "message": "이웃으로 추가되었습니다",
        "neighbor_count": neighbor_api.count_neighbors(user_id)
    }), 200

@app.route('/guestbook')
def guestbook():
    user = None
    user_id = session.get('user_id')
    if user_id:
        user = db.user.find_one({"_id": ObjectId(user_id)})

    username = user['username'] if user else '몽글몽글'
    profile_color = (user or {}).get('profile_color', DEFAULT_PROFILE_COLOR)
    profile_desc = (user or {}).get('profile_desc', DEFAULT_PROFILE_DESC)

    neighbor_count = neighbor_api.count_neighbors(user_id) if user_id else 0
    all_users = neighbor_api.get_all_users(user_id) if user_id else []
    neighbor_list = neighbor_api.get_neighbors(user_id) if user_id else []
    stats = {"posts": db.blog.count_documents({}), "neighbors": neighbor_count, "visitors": 0}
    entries = guestbook_api.get_guestbooks()

    return render_template(
        'guestbook.html',
        stats=stats,
        is_neighbor=False,
        all_users=all_users,
        neighbor_list=neighbor_list,
        username=username,
        profile_color=profile_color,
        profile_desc=profile_desc,
        active_page='guestbook',
        entries=entries
    )

@app.route('/guestbook/create', methods=['POST'])
def create_guestbook():
    guestbook_api.create_guestbook()
    return redirect(url_for('guestbook'))

@app.route('/create_post', methods=['POST'])
def create_post():
    return blog_api.create_blog()

@app.route('/update_post/<post_id>', methods=['GET'])
def update_post(post_id):
    post = db.blog.find_one({"_id": ObjectId(post_id)})
    return render_template('update_blog.html',post = post)

@app.route('/update_post/<post_id>', methods=['POST'])
def update_post_submit(post_id):
    return blog_api.update_blog(post_id)

@app.route('/delte_post/<post_id>', methods=['GET'])
def delete_post(post_id):
    db.blog.delete_one({'_id': ObjectId(post_id)})
    return redirect(url_for('blogPost'))


if __name__ == '__main__':
    app.run(debug=True, port=5001)

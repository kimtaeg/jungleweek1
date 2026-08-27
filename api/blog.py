from flask import Flask, request, render_template, redirect, session, url_for
from pymongo import MongoClient, DESCENDING
from datetime import datetime, timezone
from bson import ObjectId
import os
import json


app = Flask(__name__)

app.secret_key = os.getenv("SECRET_KEY", "dev-secret-key-change-me")
client = MongoClient(os.getenv("MONGO_URI"))
db = client.dbjungle


# # 게시글 crud
# # 1. 게시글 조회 (read)
@app.route("/blogs", methods=['GET'])
def get_blogs(user_id=None):
    # 로그인한 사람의 글만 불러오기 (가장 최신 네 개)
    query = {"author_id": ObjectId(user_id)} if user_id else {}
    blogs = list(db.blog.find(query).sort('created_at', DESCENDING).limit(4))

    return blogs

# 2. 게시글 생성 (create)
# 2-1. 블로그 생성
@app.route("/blogs", methods=['POST'])
def create_blog():
    author_id = ObjectId(session.get('user_id'))
    created_at = datetime.now().strftime('%Y-%m-%d %H:%M')
    # blog_post.html에서 받은 폼 - 제목
    title = request.form.get('title')
    # blog_post.html에서 받은 폼 - 내용
    content = request.form.get('content')
    likes= 0
    
    result = db.blog.insert_one({
        "author_id": author_id,
        "created_at": created_at,
        "title" : title,
        "content" : content,
        "likes": likes,
    })

    return redirect(url_for('post_detail', post_id=result.inserted_id))


# 3. 게시글 수정 (update)
# <form> 태그는 GET/POST만 지원하며, PUT이나 PATCH 메서드를 지원하지 않아서 POST로 대체
def update_blog(post_id):
    # update_blog.html에서 받은 폼 - 새 제목
    new_title = request.form.get('title')
    # update_blog.html에서 받은 폼 - 새 내용
    new_content = request.form.get('content')

    # db 업데이트
    db.blog.update_one(
        {'_id': ObjectId(post_id)},
        {'$set': {'title': new_title, 'content': new_content}}
    )

    return redirect(url_for('post_detail', post_id=post_id))

# 4. 게시글 삭제 (delete)
def delete_blog(blog_id):
    db.blog.delete_one({'_id': ObjectId(blog_id)})
    return
    


if __name__=="__main__":
    app.run(debug=True, port=5000)

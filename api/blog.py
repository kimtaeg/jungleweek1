from flask import Flask, request, render_template, redirect
from pymongo import MongoClient, DESCENDING
from datetime import datetime, timezone
import json


username = "root"
password = "1234"

uri = f"mongodb://{username}:{password}@localhost:27017/?authSource=admin"
client = MongoClient(uri)
db = client.admin

user_collection = db.user
blog_collection = db.blog


app = Flask(__name__)


# # 게시글 crud
# # 1. 게시글 조회 (read)
@app.route("/blogs", methods=['GET'])
def get_blogs():
    # db에서 가장 최신 블로그 네 개 불러오기
    blogs = list(blog_collection.find({}.sort('created_at', DESCENDING).limit(4)))

    # ssr: blog_post.html에 posts라는 이름으로 게시글 전달 후 렌더링
    return render_template('templates/blog_post.html', posts=blogs)

# 2. 게시글 생성 (create)
@app.route("/blogs", methods=['POST'])
def post_blog():
    authour_id = user_collection['_id']
    created_at = datetime.now()
    # blog_post.html에서 받은 폼 - 제목
    title = request.form.get('ttile')
    # blog_post.html에서 받은 폼 - 내용
    content = request.form.get('content')
    likes= 0
    
    blog_collection.insert_one({
        "authour_id": authour_id,
        "created_at": created_at,
        "title" : title,
        "content" : content,
        "likes": likes,
    })

    return redirect('/blogs')

# 3. 게시글 수정 (update)
# <form> 태그는 GET/POST만 지원하며, PUT이나 PATCH 메서드를 지원하지 않아서 POST로 대체
@app.route("/blogs", methods=['POST'])
def update_blog(blog_id):
    # blog_post.html에서 받은 폼 - 새 제목
    new_title = request.form.get('title')
    # blog_post.html에서 받은 폼 - 새 내용
    new_content = request.form.get('content')

    # db 업데이트
    blog_collection.update_one({
        {'_id': blog_id},
        {"title" : new_title},
        {"content" : new_content},
    })

    return redirect('/blogs')

# 4. 게시글 삭제 (delete)
# <form> 태그는 GET/POST만 지원하며, PUT이나 PATCH 메서드를 지원하지 않아서 POST로 대체
@app.rout("/blogs", methods=['POST'])
def delete_blog(blog_id):
    blog_collection.delete_one({'_id': blog_id})


if __name__=="__main__":
    app.run(debug=True, port=5000)
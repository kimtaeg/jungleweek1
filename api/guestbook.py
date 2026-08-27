from flask import request, session
from pymongo import MongoClient, DESCENDING
from datetime import datetime, timezone
from bson import ObjectId
import os


client = MongoClient(os.getenv("MONGO_URI"))
db = client.dbjungle


def format_time_ago(created_at):
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    diff = datetime.now(timezone.utc) - created_at
    seconds = int(diff.total_seconds())

    if seconds < 60:
        return "방금 전"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes}분 전"
    hours = minutes // 60
    if hours < 24:
        return f"{hours}시간 전"
    days = hours // 24
    return f"{days}일 전"


# 방명록 조회 (read)
def get_guestbooks(user_id=None):
    query = {"writer_id": ObjectId(user_id)} if user_id else {}
    entries = list(db.guestbook.find(query).sort('created_at', DESCENDING).limit(20))

    for e in entries:
        writer = db.user.find_one({"_id": e.get('writer_id')}) if e.get('writer_id') else None
        e['writer_name'] = writer['username'] if writer else '익명'
        e['writer_color'] = (writer or {}).get('profile_color', '#E68485')
        e['time_ago'] = format_time_ago(e['created_at'])

    return entries


# 방명록 생성 (create)
def create_guestbook():
    writer_id = session.get('user_id')
    content = (request.form.get('content') or '').strip()

    if content and writer_id:
        db.guestbook.insert_one({
            "writer_id": ObjectId(writer_id),
            "content": content,
            "created_at": datetime.now(timezone.utc),
        })

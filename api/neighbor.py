from pymongo import MongoClient
from datetime import datetime, timezone
from bson import ObjectId
import os


client = MongoClient(os.getenv("MONGO_URI"))
db = client.dbjungle


# 나(user_id)를 제외한 전체 회원 목록 (이미 이웃 추가한 사람은 is_added 표시)
def get_all_users(user_id):
    added_ids = {
        doc['neighbor_id']
        for doc in db.neighbor.find({"user_id": ObjectId(user_id)})
    }

    users = list(db.user.find({"_id": {"$ne": ObjectId(user_id)}}))
    for u in users:
        u['is_added'] = u['_id'] in added_ids

    return users


# 내가 추가한 이웃 목록
def get_neighbors(user_id):
    docs = list(db.neighbor.find({"user_id": ObjectId(user_id)}))
    neighbors = []
    for doc in docs:
        neighbor_user = db.user.find_one({"_id": doc['neighbor_id']})
        if neighbor_user:
            neighbors.append(neighbor_user)

    return neighbors


def count_neighbors(user_id):
    return db.neighbor.count_documents({"user_id": ObjectId(user_id)})


def add_neighbor(user_id, target_id):
    if user_id == target_id:
        return False

    db.neighbor.update_one(
        {"user_id": ObjectId(user_id), "neighbor_id": ObjectId(target_id)},
        {"$setOnInsert": {"created_at": datetime.now(timezone.utc)}},
        upsert=True
    )
    return True

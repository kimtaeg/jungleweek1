from flask import Flask, render_template
from dotenv import load_dotenv
from pymongo import MongoClient
import os
app = Flask(__name__)

load_dotenv()
client = MongoClient(os.getenv("MONGO_URI"))
db = client.dbjungle

@app.route('/signup')
def signup():
    return render_template('signup.html')
if __name__ == '__main__':
    app.run(debug=True, port=5001)
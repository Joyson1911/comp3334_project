from flask import Flask
from common.config import Config

app = Flask(__name__)

@app.route('/')
def home():
    return {"message": "Server is running!"}

if __name__ == "__main__":
    Config.add_conf()
    app.run(host="0.0.0.0", port=8800, debug=True)   # only for local dev
from flask import Flask
from flask_cors import CORS
import redis
from config import REDIS_URL
import routes

def create_app():
    app = Flask(__name__)
    CORS(app)

    # Connect to Redis
    try:
        r = redis.from_url(REDIS_URL, decode_responses=True)
        r.ping() # Check connection
        print("Successfully connected to Redis.")
    except redis.exceptions.ConnectionError as e:
        print(f"Could not connect to Redis: {e}")
        r = None

    # Initialize routes
    routes.init_app(app, r)

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(port=5001, debug=True)

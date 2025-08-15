import os
from flask import Flask
from flask_cors import CORS
import redis
from extensions import db
from dotenv import load_dotenv

load_dotenv() # Load environment variables from .env file BEFORE importing routes

import routes

def create_app():
    app = Flask(__name__)
    CORS(app)

    # Configure the database from the environment variable
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        raise RuntimeError("DATABASE_URL is not set. Please create a .env file or set the environment variable.")
    
    # Heroku/Render use postgres://, but SQLAlchemy needs postgresql://
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)

    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Initialize the database with the app
    db.init_app(app)

    # Connect to Redis from the environment variable
    redis_url = os.environ.get('REDIS_URL')
    try:
        r = redis.from_url(redis_url, decode_responses=True)
        r.ping() # Check connection
        print("Successfully connected to Redis.")
    except (redis.exceptions.ConnectionError, TypeError) as e:
        print(f"Could not connect to Redis: {e}")
        r = None

    # Initialize routes
    routes.init_app(app, r, db)

    # Create database tables if they don't exist
    with app.app_context():
        db.create_all()

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(port=5001, debug=True)

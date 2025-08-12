from flask import Flask
from flask_cors import CORS
import redis
from config import REDIS_URL
import routes
from extensions import db
import os

def create_app():
    app = Flask(__name__)
    CORS(app)

    # Configure the database
    # Use an absolute path for the database file to avoid ambiguity
    project_dir = os.path.dirname(os.path.abspath(__file__))
    database_path = os.path.join(project_dir, 'instance', 'interviews.db')
    os.makedirs(os.path.dirname(database_path), exist_ok=True) # Ensure the 'instance' directory exists
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{database_path}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Initialize the database with the app
    db.init_app(app)

    # Connect to Redis
    try:
        r = redis.from_url(REDIS_URL, decode_responses=True)
        r.ping() # Check connection
        print("Successfully connected to Redis.")
    except redis.exceptions.ConnectionError as e:
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

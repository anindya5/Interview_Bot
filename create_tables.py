import os
from app import create_app, db
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Create a Flask app instance to establish an application context
app = create_app()

# The 'with app.app_context()' is crucial. It sets up the necessary
# context for Flask-SQLAlchemy to know which database to connect to.
with app.app_context():
    print("Initializing database and creating tables...")
    
    # This command creates all tables defined in your models.py
    # It will not re-create tables that already exist.
    db.create_all()
    
    print("Database tables created successfully!")

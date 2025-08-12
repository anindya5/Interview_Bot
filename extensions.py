from flask_sqlalchemy import SQLAlchemy

# This shared db object can be imported by models, app, and other modules
db = SQLAlchemy()

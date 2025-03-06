from flask import Flask, request, jsonify, send_file, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import pandas as pd
import os
import json
from datetime import datetime
import dotenv

# Load environment variables
dotenv.load_dotenv()

app = Flask(__name__, static_folder=".", static_url_path="")
CORS(app)  # Enable CORS for all routes

# Use environment variables for database configuration
db_user = os.getenv("DB_USER", "postgres")
db_password = os.getenv("DB_PASSWORD", "postgres")
db_host = os.getenv("DB_HOST", "localhost")
db_port = os.getenv("DB_PORT", "5432")
db_name = os.getenv("DB_NAME", "time_motion_study")

# Configure SQLAlchemy for PostgreSQL or SQLite based on environment
if os.getenv("DATABASE_URL"):
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL")
else:
    # Use SQLite for development if PostgreSQL is not configured
    app.config['SQLALCHEMY_DATABASE_URI'] = f'postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}'
    
    # Fallback to SQLite if PostgreSQL is not available
    try:
        import psycopg2
    except ImportError:
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///time_motion_study.db'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Define the Project Model
class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    data = db.Column(db.Text, nullable=False)  # JSON data
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# Create the database tables
@app.before_first_request
def create_tables():
    db.create_all()

# Serve index.html at root
@app.route('/')
def home():
    return app.send_static_file('index.html')

# API endpoint to save project
@app.route('/api/save-project', methods=['POST'])
def save_project():
    try:
        data = request.json
        project_name = data.get('projectName', 'Untitled Project')
        
        # Check if project exists
        existing_project = Project.query.filter_by(name=project_name).first()
        
        if existing_project:
            # Update existing project
            existing_project.data = json.dumps(data)
            existing_project.updated_at = datetime.utcnow()
            db.session.commit()
            return jsonify({"message": "Project updated successfully", "id": existing_project.id})
        else:
            # Create new project
            new_project = Project(
                name=project_name,
                data=json.dumps(data)
            )
            db.session.add(new_project)
            db.session.commit()
            return jsonify({"message": "Project saved successfully", "id": new_project.id})
            
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# API endpoint to list all projects
@app.route('/api/projects', methods=['GET'])
def list_projects():
    try:
        projects = Project.query.all()
        projects_list = [{"id": p.id, "name": p.name, "updated_at": p.updated_at.isoformat()} for p in projects]
        return jsonify({"projects": projects_list})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# API endpoint to load a project
@app.route('/api/projects/<int:project_id>', methods=['GET'])
def get_project(project_id):
    try:
        project = Project.query.get(project_id)
        if not project:
            return jsonify({"error": "Project not found"}), 404
            
        return jsonify({
            "id": project.id,
            "name": project.name,
            "data": json.loads(project.data),
            "created_at": project.created_at.isoformat(),
            "updated_at": project.updated_at.isoformat()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# API endpoint to delete a project
@app.route('/api/projects/<int:project_id>', methods=['DELETE'])
def delete_project(project_id):
    try:
        project = Project.query.get(project_id)
        if not project:
            return jsonify({"error": "Project not found"}), 404
            
        db.session.delete(project)
        db.session.commit()
        return jsonify({"message": "Project deleted successfully"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# Error handlers
@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Resource not found"}), 404

@app.errorhandler(500)
def server_error(e):
    return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=os.environ.get("FLASK_DEBUG", "False").lower() == "true")
import os
import secrets

basedir = os.path.abspath(os.path.dirname(__file__))
project_root = os.path.dirname(basedir)

# Ensure instance directory exists
#instance_dir = os.path.join(project_root, 'instance')
#os.makedirs(instance_dir, exist_ok=True)


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or secrets.token_hex(32)
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') 
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = "/tmp/uploads"
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5 MB max upload
    ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx'}

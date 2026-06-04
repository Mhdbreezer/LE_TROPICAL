import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'cle-secrete-senegal-sgrdms-2026'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///sgrdms.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

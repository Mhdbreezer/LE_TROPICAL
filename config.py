import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'cle-secrete-senegal-sgrdms-2026'
    
    # URL de base de données fournie par Vercel (Neon/Postgres)
    db_url = os.environ.get('POSTGRES_URL') or os.environ.get('DATABASE_URL')
    
    if db_url:
        # Correction pour SQLAlchemy qui exige 'postgresql://' au lieu de 'postgres://'
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://", 1)
        SQLALCHEMY_DATABASE_URI = db_url
    else:
        # En local, on garde SQLite
        SQLALCHEMY_DATABASE_URI = 'sqlite:///sgrdms.db'
        
    SQLALCHEMY_TRACK_MODIFICATIONS = False

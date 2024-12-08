from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

username = "root"
password = "theantoncruz"
print(f"Database Username: {username}, Password: {password}")
URL_DATABASE = f"mysql+pymysql://{username}:{password}@localhost:3306/eclass"

engine = create_engine(URL_DATABASE)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

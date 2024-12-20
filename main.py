from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy import create_engine, Column, Integer, String, Table, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from pydantic import BaseModel, validator
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import logging
from dotenv import load_dotenv
import os

load_dotenv()  # Load environment variables from the .env file

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL is not set in the environment or .env file")

# Setup basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

html = """
<!DOCTYPE html>
<html>
    <head>
        <title>FastAPI on Vercel</title>
        <link rel="icon" href="/static/favicon.ico" type="image/x-icon" />
    </head>
    <body>
        <div class="bg-gray-200 p-4 rounded-lg shadow-lg">
            <h1>Hello from FastAPI</h1>
            <ul>
                <li><a href="/docs">/docs</a></li>
            </ul>
            <p>Powered by <a href="https://facebook.com" target="_blank">Facebook</a></p>
        </div>
    </body>
</html>
"""

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Many-to-many relationship table
user_medicine = Table(
    "user_medicine",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id"), primary_key=True),
    Column("medicine_id", Integer, ForeignKey("medicines.id"), primary_key=True),
)

# Medicine model
class Medicine(Base):
    __tablename__ = "medicines"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    users = relationship("User", secondary=user_medicine, back_populates="medicines")

# User model
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    medicines = relationship("Medicine", secondary=user_medicine, back_populates="users")

# Create database tables
Base.metadata.create_all(bind=engine)

# Dependency to get the database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Pydantic model for UserMedicineRequest
class UserMedicineRequest(BaseModel):
    user_id: int
    medicine_names: list[str]

    @validator("medicine_names")
    def validate_medicine_names(cls, value):
        if not value:
            raise ValueError("medicine_names must not be empty")
        return value

@app.get("/")
async def root():
    return HTMLResponse(html)

@app.post("/user/add_medicines")
def add_medicines_to_user(request: UserMedicineRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == request.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    medicines = db.query(Medicine).filter(Medicine.name.in_(request.medicine_names)).all()
    if not medicines:
        raise HTTPException(status_code=404, detail="One or more medicines not found")
    
    existing_medicines = {m.id for m in user.medicines}
    new_medicines = [m for m in medicines if m.id not in existing_medicines]
    
    if new_medicines:
        user.medicines.extend(new_medicines)
        db.commit()
        logger.info(f"Added medicines {', '.join([m.name for m in new_medicines])} to user {user.name}")
    return {"user_id": user.id, "medicines": [m.name for m in user.medicines]}

@app.post("/user/buy_medicines")
def buy_medicines(request: UserMedicineRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == request.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    medicines = db.query(Medicine).filter(Medicine.name.in_(request.medicine_names)).all()
    if not medicines:
        raise HTTPException(status_code=404, detail="One or more medicines not found")
    
    new_medicines = []
    for medicine in medicines:
        if medicine not in user.medicines:
            user.medicines.append(medicine)
            new_medicines.append(medicine)
    
    if new_medicines:
        db.commit()
        logger.info(f"User {user.name} bought medicines {', '.join([m.name for m in new_medicines])}")
    
    return {"user_id": user.id, "bought_medicines": [m.name for m in new_medicines]}

# Initialize sample data
def init_db():
    db = SessionLocal()
    if not db.query(Medicine).first():
        medicines = [
            Medicine(name="Paracetamol"),
            Medicine(name="Broufen"),
            Medicine(name="Panadol"),
            Medicine(name="Alp"),
            Medicine(name="Calpol"),
        ]
        db.add_all(medicines)
        db.commit()
        logger.info("Sample medicines added to the database.")
    if not db.query(User).first():
        users = [
            User(name="John Doe"),
            User(name="Jane Smith"),
            User(name="Bjorn"),
            User(name="Ali"),
        ]
        db.add_all(users)
        db.commit()
        logger.info("Sample users added to the database.")
    db.close()

# Uncomment the following line to initialize the database (use only in development)
init_db()
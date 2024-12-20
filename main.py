from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy import create_engine, Column, Integer, String, Table, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from pydantic import BaseModel
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse


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
            <p>Powered by <a href="https://vercel.com" target="_blank">Vercel</a></p>
        </div>
    </body>
</html>
"""

DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Many-to-many thats why we are using two foreign keys
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

Base.metadata.create_all(bind=engine)

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
    if not db.query(User).first():
        users = [
            User(name="John Doe"),
            User(name="Jane Smith"),
            User(name="Bjorn"),
            User(name="Ali"),
        ]
        db.add_all(users)
        db.commit()
    db.close()

init_db()

# Dependency to get database session
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
    user.medicines.extend(medicines)
    db.commit()
    return {"user_id": user.id, "medicines": [m.name for m in user.medicines]}

@app.post("/user/buy_medicines")
def buy_medicines(request: UserMedicineRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == request.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    medicines = db.query(Medicine).filter(Medicine.name.in_(request.medicine_names)).all()
    if not medicines:
        raise HTTPException(status_code=404, detail="One or more medicines not found")
    for medicine in medicines:
        if medicine not in user.medicines:
            user.medicines.append(medicine)
    db.commit()
    return {"user_id": user.id, "bought_medicines": [m.name for m in medicines]}



# from mangum import Mangum
# handler = Mangum(app)

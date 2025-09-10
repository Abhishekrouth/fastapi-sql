from fastapi import FastAPI, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from typing import List
import uvicorn
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware


SQLALCHEMY_DATABASE_URL = "mysql+pymysql://root:1234@localhost:3306/mydatabase"

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Item(Base):
    __tablename__ = "items"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    item_name = Column(String(100), index=True, nullable=False)
    price = Column(Integer, index=True, nullable=False)
    description = Column(String(255), index=True)

class ItemBase(BaseModel):
    item_name: str
    price: int
    description: str

class ItemCreate(ItemBase):
    pass

class ItemResponse(ItemBase):
    id: int

    class Config:
        from_attributes = True

class ItemNotFoundException(Exception):
    def __init__(self, id: int):
        self.id = id
        self.message = f"Item with id {id} not found"
        self.status_code = 404
        super().__init__(self.message)

class CustomResponse(BaseModel):
    id: int
    name: str
    price: float
    message: str

class ItemResponseV1(BaseModel):
    id: int
    item_name: str
    
class ItemResponseV2(BaseModel):
    id: int
    item_name: str
    price: float
    description: str



Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="CRUD using SQL and FastAPI",
    description="A simple CRUD API for managing items",
    version="1.0.0"
)

v1= FastAPI()
v2= FastAPI()

origins = [
    "http://localhost",
    "http://localhost:8080",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db = SessionLocal()
    try:
        yield db 
    finally:
        db.close()

@app.post("/items/", response_model=ItemResponse, status_code=201)
def create_item(item: ItemCreate, db: Session = Depends(get_db)):
    db_item = Item(
        item_name=item.item_name, 
        price=item.price, 
        description=item.description
    )
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

@app.get("/items/", response_model=List[ItemResponse])
def read_items(db: Session = Depends(get_db)):
    return db.query(Item).all()

@app.put("/items/{id}", response_model=CustomResponse)
def update_item(id: int, item: ItemCreate, db: Session = Depends(get_db)):
    db_item = db.query(Item).filter(Item.id == id).first()
    if not db_item:
        raise ItemNotFoundException(id)
    db_item.item_name = item.item_name
    db_item.price = item.price
    db_item.description = item.description
    db.commit()
    db.refresh(db_item)

    return{ "id": db_item.id,"name": db_item.item_name,"price": db_item.price, "message": "Item details fetched successfully"} 

@app.delete("/items/{id}")
def delete_item(id: int, db: Session = Depends(get_db)):
    db_item = db.query(Item).filter(Item.id == id).first()
    if not db_item:
         raise ItemNotFoundException(id)
    db.delete(db_item)
    db.commit()
    return {"message": f"Item {id} deleted successfully"}

@app.exception_handler(ItemNotFoundException)
async def item_not_found_handler(request: Request, exc: ItemNotFoundException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.message},
    )

@v1.get("/v1/items", response_model=List[ItemResponseV1])
def read_items_v1(db: Session = Depends(get_db)):
    items= db.query(Item).all()
    return [{"id": i.id, "item_name": i.item_name} for i in items]

@v2.get("/v2/items", response_model=List[ItemResponseV2])
def read_items_v2(db: Session = Depends(get_db)):
    items = db.query(Item).all()
    return [
        { "id": i.id,"item_name": i.item_name,"price": i.price,"description": i.description} for i in items]


app.mount("/v1/items", v1)
app.mount("/v2/items", v2)

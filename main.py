from fastapi import FastAPI, Body, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, JSONResponse
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field
from bson import ObjectId
from typing import Optional, List
import motor.motor_asyncio
import uvicorn

# Initializing FastAPI server
app = FastAPI()

# Setup CORS policy
origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Connect MongoDB
client = motor.motor_asyncio.AsyncIOMotorClient("mongodb+srv://hatatwit:pass123@cluster0.ydwrobg.mongodb.net/?retryWrites=true&w=majority")
db = client.bunnyFoodDB

# Convert ObjectIds to strings before storing them as the _id
class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid objectid")
        return ObjectId(v)

    @classmethod
    def __modify_schema__(cls, field_schema):
        field_schema.update(type="string")

# Structure Food Model
class Food(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    food: str = Field(...)
    quantity: str = Field(...)
    imgURL: str = Field(...)

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
        schema_extra = {
            "example": {
                "food": "acorn",
                "quantity": "none",
                "imgURL": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d8/Acorns_small_to_large.jpg/330px-Acorns_small_to_large.jpg"
            }
        }

class UpdateFood(BaseModel):
    food: Optional[str]
    quantity: Optional[str]
    imgURL: Optional[str]

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
        schema_extra = {
            "example": {
                "food": "acorn",
                "quantity": "none",
                "imgURL": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d8/Acorns_small_to_large.jpg/330px-Acorns_small_to_large.jpg"
            }
        }

# Setup Home route
@app.get("/")
async def root():
    return {"message": "Welcome to Bunny Expert API, where you will get a list of edible and inedible foods for rabbits."}

# Create new food in the foods collection in MongoDB
@app.post("/", response_description="Add new food", response_model=Food)
async def create_food(food: Food = Body(...)):
    food = jsonable_encoder(food)
    new_food = await db["foods"].insert_one(food)
    created_food = await db["foods"].find_one({"_id": new_food.inserted_id})
    return JSONResponse(status_code=status.HTTP_201_CREATED, content=created_food)

# Get all food in foods collection in MongoDB
@app.get("/foods", response_description="List all foods", response_model=List[Food])
async def list_foods():
    foods = await db["foods"].find().to_list(1000)
    return foods

# Get specific food by name
@app.get("/{inputFood}", response_description="Get specifc food by name", response_model=Food)
async def get_food(inputFood: str):
    if (food := await db["foods"].find_one({"food": inputFood})) is not None:
        return food

    raise HTTPException(status_code=404, detail=f"Food {inputFood} not found")

# Update food in foods collection in MongoDB
@app.put("/{id}", response_description="Update specific food by id", response_model=Food)
async def update_food(id: str, food: UpdateFood = Body(...)):
    food = {k: v for k, v in food.dict().items() if v is not None}

    if len(food) >= 1:
        update_result = await db["foods"].update_one({"_id": id}, {"$set": food})

        if update_result.modified_count == 1:
            if (
                updated_food := await db["foods"].find_one({"_id": id})
            ) is not None:
                return updated_food

    if (existing_food := await db["foods"].find_one({"_id": id})) is not None:
        return existing_food

    raise HTTPException(status_code=404, detail=f"Food {id} not found")

# Delete food from foods collection in MongoDB
@app.delete("/{id}", response_description="Delete specific food by id")
async def delete_food(id: str):
    delete_result = await db["foods"].delete_one({"_id": id})

    if delete_result.deleted_count == 1:
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    raise HTTPException(status_code=404, detail=f"Food {id} not found")

# if __name__ == "__main__":
#     uvicorn.run(app, port=8080, host="localhost")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import os

from src.api.cbse_routes import router as cbse_router

load_dotenv()

app = FastAPI(title="Vidyalaya-Saathi API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup MongoDB
MONGO_URI = os.getenv("MONGO_URI", "mongodb://127.0.0.1:27017/vidyalaya_saathi")
PORT = int(os.getenv("PORT", 5000))

# Global DB client
db_client = None

@app.on_event("startup")
async def startup_db_client():
    global db_client
    try:
        import certifi
        db_client = AsyncIOMotorClient(MONGO_URI, tlsCAFile=certifi.where())
        # Attempt to get server info to verify connection
        await db_client.server_info()
        print("Connected successfully to MongoDB!")
    except Exception as e:
        print(f"Database connection error: {e}")

@app.on_event("shutdown")
async def shutdown_db_client():
    global db_client
    if db_client:
        db_client.close()

# Include routes
app.include_router(cbse_router, prefix="/api/cbse", tags=["CBSE"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=True)

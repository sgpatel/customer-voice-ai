# app/main.py
from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.core.config import settings, logger
# --- Import CORS Middleware ---
from starlette.middleware.cors import CORSMiddleware

from app.api.v1.endpoints import mentions # Import your router
from app.db.database import init_db # Import DB init function

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Actions on startup
    logger.info("Application startup...")
    await init_db() # Initialize the database (create tables)
    logger.info("Database initialized.")
    yield
    # Actions on shutdown
    logger.info("Application shutdown...")

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan # Use the lifespan context manager
)


# --- Add CORS Middleware ---
# Define the origins allowed to connect.
# Adjust these URLs based on where your React app will run during development.
origins = [
    "http://localhost:3000", # Default Create React App port
    "http://localhost:5173", # Default Vite React port
    "http://127.0.0.1:5173", # Another way Vite might be accessed
    # Add your frontend's deployed URL in production
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins, # List of allowed origins
    allow_credentials=True, # Allows cookies (important if you add authentication)
    allow_methods=["*"], # Allow all standard HTTP methods
    allow_headers=["*"], # Allow all headers
)
# --- End CORS Middleware ---
# Include your API router
app.include_router(mentions.router, prefix=settings.API_V1_STR + "/mentions", tags=["mentions"])

@app.get("/")
async def read_root():
    return {"message": "Welcome to the Mention Analyzer API"}

# You might want a health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "ok"}
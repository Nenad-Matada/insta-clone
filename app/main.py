from fastapi import FastAPI
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base
from app.routers import auth, stories, posts, follows, users, feed
import datetime

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables on startup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Cleanup on shutdown if needed

app = FastAPI(
    title="Instagram Clone API",
    description="Backend API for Instagram clone project",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware (frontend integration)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Must be configured
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# routers
app.include_router(auth.router)
app.include_router(stories.router)
app.include_router(posts.router)
app.include_router(follows.router)
app.include_router(users.router)
app.include_router(feed.router)

@app.get("/")
async def root():
    return {
        "message": "Instagram Clone API is running!",
        "version": "1.0.0",
        "endpoints": {
            "auth": "/auth",
            "users": "/users",
            "posts": "/posts",
            "stories": "/stories",
            "follows": "/follows",
            "feed": "/feed"
        },
        "docs": "/docs"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow()}
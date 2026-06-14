from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.database import engine, Base
from app.routers import auth, stories, posts, follows

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield

app = FastAPI(lifespan=lifespan)

# Routers
app.include_router(auth.router)
app.include_router(stories.router)
app.include_router(posts.router)
app.include_router(follows.router)

@app.get("/")
async def root():
    return {"message": "Instagram Clone API - Stage 4 Ready"}
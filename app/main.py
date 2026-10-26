from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.chats import router as chats_router
from app.database.connection import initialize_database


@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize_database()
    yield


app = FastAPI(
    title="AI Chatbot API",
    lifespan=lifespan,
)

app.include_router(chats_router)


@app.get("/")
def root():
    return {"message": "AI Chatbot API is running"}


@app.get("/health")
def health():
    return {"status": "healthy"}
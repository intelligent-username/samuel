from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import auth, generate, github, history, resume


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(title="Samuel API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(github.router)
app.include_router(resume.router)
app.include_router(generate.router)
app.include_router(history.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
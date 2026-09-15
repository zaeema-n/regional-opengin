from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI

load_dotenv()

from routers import opengin_router
from utils import http_client


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await http_client.start()
    try:
        yield
    finally:
        await http_client.close()


app = FastAPI(
    title="OpenGIN Service",
    description="API adapter to OpenGIN",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(opengin_router)


@app.get("/health")
async def health():
    return {"status": "ok"}

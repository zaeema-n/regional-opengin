from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

from routers import opengin_router, regions_router
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
    # If you really need to call an endpoint which returns geojson in the Swagger UI, 
    # you can disable syntax highlighting below - note it still may fail to render due to the size of geojson
    # swagger_ui_parameters={"syntaxHighlight": False},
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(opengin_router)
app.include_router(regions_router)


@app.get("/health")
async def health():
    return {"status": "ok"}

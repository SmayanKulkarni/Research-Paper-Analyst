from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import uploads, analyze

settings = get_settings()

app = FastAPI(title=settings.PROJECT_NAME)

# CORS (adjust origins as needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(uploads.router)
app.include_router(analyze.router)


@app.get("/")
async def root():
    return {"message": "Research Paper Analyzer backend is running"}

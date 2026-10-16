from dotenv import load_dotenv
from fastapi import FastAPI
import uvicorn


load_dotenv()

app = FastAPI(title="Proyecto final API")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


def main() -> None:
    uvicorn.run("proyecto_final:app", host="127.0.0.1", port=8000, reload=True)

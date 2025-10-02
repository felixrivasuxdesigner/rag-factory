# Placeholder for the FastAPI application.

from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "API for vector-doc-ingestion is running."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
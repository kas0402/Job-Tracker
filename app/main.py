from fastapi import FastAPI
app = FastAPI(title = "Job Tracker API")

@app.get("/health")
def health_check():
    return {"status": "ok"}


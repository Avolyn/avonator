"""
Simple FastAPI app for testing
"""

from fastapi import FastAPI

app = FastAPI(title="Simple Guardrails Test", version="1.0.0")

@app.get("/")
async def root():
    return {"message": "Simple FastAPI Guardrails Service is working!"}

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "simple-guardrails"}

@app.get("/test")
async def test():
    return {"test": "success", "message": "This is a simple test endpoint"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

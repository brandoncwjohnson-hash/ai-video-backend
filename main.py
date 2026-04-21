from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def home():
    return {"status": "AI Video Server Running"}

@app.get("/test")
def test():
    return {"message": "Your API is working!"}

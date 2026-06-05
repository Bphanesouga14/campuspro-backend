from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def lire_racine():
    return {"Bienvenue": "Bienvenue sur mon API FastAPI!"}

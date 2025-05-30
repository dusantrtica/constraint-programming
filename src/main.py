from fastapi import FastAPI
from src.routers.product_mix import product_mix_router
import uvicorn # type: ignore

app = FastAPI()


@app.get("/")
async def read_main():
    return {"msg": "Hello World"}

app.include_router(product_mix_router, prefix="/product-mix")

if __name__ == "__main__":    
    config = uvicorn.Config(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
        reload=True
    )
    server = uvicorn.Server(config)
    server.run()

from fastapi import FastAPI

from app.api.routes.netlist import router as netlist_router

app = FastAPI(title="netlist-checker")


@app.get("/")
def health():
    return {"status": "ok", "name": "netlist-checker"}


app.include_router(netlist_router)

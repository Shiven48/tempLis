from fastapi import FastAPI, Body
from pydantic import BaseModel
from typing import Annotated

app = FastAPI(title="Dummy Remote API")

class ProcessedData(BaseModel):
    source_id: str
    content: dict
    status: str

@app.post("/v1/data")
async def receive_data(payload: Annotated[ProcessedData, Body()]):
    """
    This endpoint simulates receiving processed data from the middleware.
    """
    print(f"Received data from {payload.source_id}: {payload.content}")
    # In a real scenario, this would interact with a GCP service.
    return {"message": "Data received successfully", "status": "processed"}

#!/usr/bin/env python3

import logging as log
import os
import sys
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, Response, Security, status
from fastapi.security import APIKeyHeader
from google.cloud import storage
from pydantic import BaseModel, Field

LOGLEVEL = os.environ.get("LOGLEVEL", "DEBUG").upper()
log.basicConfig(stream=sys.stdout, level=LOGLEVEL)

api_key = os.environ.get("API_KEY")
api_key_header_scheme = APIKeyHeader(name="x-api-key", auto_error=False)

project_id = os.environ.get("PROJECT_ID")
bucket_name = os.environ.get("BUCKET")

# Initialize Storage client
storage_client = storage.Client(project=project_id)
bucket = storage_client.bucket(bucket_name)


async def api_key_auth(api_key_header: str = Security(api_key_header_scheme)):
    if api_key_header != api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Forbidden",
        )


app = FastAPI()


# Define Pydantic model for event
class Event(BaseModel):
    specversion: Optional[str] = "1.0"
    id: str
    source: Optional[str] = "https://emqx.io/endpoint"
    type: Optional[str] = "io.emqx.iot.message"
    datacontenttype: Optional[str] = "application/json"
    subject: str
    time: datetime = Field(alias="timestamp")
    data: str
    application: str
    device: str
    partitionkey: str


@app.post("/", status_code=201, dependencies=[Security(api_key_auth)])
async def create_item(event: Event):
    blob_name = f"application={event.application}/sender={event.device}/dt={event.time:%Y-%m-%d}/{event.id}"
    log.debug("blob name: %s", blob_name)

    json_event = event.json()
    log.debug("writing event json: %s", json_event)

    blob = bucket.blob(blob_name)
    blob.upload_from_string(json_event)

    return {"message": "Item created"}


@app.get("/liveness/", status_code=200)
def liveness_check():
    return {"message": "Liveness check succeeded."}
#!/usr/bin/env python3

import logging as log
import os
import sys
from datetime import datetime
from typing import Any, Dict, List

from fastapi import FastAPI, HTTPException, Response, Security, status
from fastapi.security import APIKeyHeader
from google.cloud import bigquery
from pydantic import BaseModel

LOGLEVEL = os.environ.get("LOGLEVEL", "DEBUG").upper()
log.basicConfig(stream=sys.stdout, level=LOGLEVEL)

api_key = os.environ.get("API_KEY")
api_key_header_scheme = APIKeyHeader(name="x-api-key", auto_error=False)

project_id = os.environ.get("PROJECT_ID")
table_id = os.environ.get("TABLE")

# Initialize BigQuery client only if project_id is set to avoid errors during build/test if not needed immediately
# or we can assume it's always needed. The original code initialized it globally.
# We'll keep it global but wrap in try/except or just let it fail if credentials aren't there?
# For now, keeping it as is but assuming environment variables are set.
bq_client = bigquery.Client(project=project_id)


async def api_key_auth(api_key_header: str = Security(api_key_header_scheme)):
    if api_key_header != api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Forbidden",
        )


class Event(BaseModel):
    instance: str
    application: str
    device: str
    sender: str
    event_id: str
    points: Dict[str, Any]
    measured_at: datetime
    ingressed_at: datetime


app = FastAPI()


@app.post("/", status_code=201, dependencies=[Security(api_key_auth)])
async def create_item(event: Event, response: Response):
    rows_to_insert: List[Dict[str, Any]] = []
    for key, point_data in event.points.items():
        # point_data is expected to be a dict with "present_value"
        if not isinstance(point_data, dict) or "present_value" not in point_data:
            log.warning("Invalid point data for key %s: %s", key, point_data)
            continue

        present_value = point_data["present_value"]
        try:
            present_value = round(float(present_value), 7)
        except (ValueError, TypeError) as e:
            log.warning("Error converting present_value for key %s: %s", key, e)
            continue

        row_to_insert = {
            "instance": event.instance,
            "application": event.application,
            "applicationuid": "",
            "device": event.device,
            "deviceuid": "",
            "sender": event.sender,
            "eventid": event.event_id,
            "ingress": event.ingressed_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "section": "",
            "timestamp": event.measured_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "pointname": key,
            "presentvalue": present_value,
        }

        log.debug("adding row: %s", row_to_insert)
        rows_to_insert.append(row_to_insert)

    # Write data to bigquery
    if rows_to_insert:
        errors = bq_client.insert_rows_json(table_id, rows_to_insert)
        if not errors:
            msg = "New rows have been added."
            log.debug(msg)
            return {"message": msg}
        else:
            msg = f"Encountered errors while inserting rows: {errors}"
            log.warning(msg)
            response.status_code = 500
            return {"error": msg}
    else:
        msg = "No rows to insert."
        log.warning(msg)
        response.status_code = 204
        return {"message": msg}


@app.get("/liveness/", status_code=200)
def liveness_check():
    return {"message": "Liveness check succeeded."}

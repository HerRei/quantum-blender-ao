import asyncio
import uuid
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import uvicorn

app = FastAPI()
mode = "normal"

@app.post("/lighting/estimate")
async def estimate(request: Request):
    global mode
    body = await request.json()
    req_id = body.get("request_id", str(uuid.uuid4()))
    
    base_res = {
        "schema_version": "1.0",
        "request_id": req_id,
        "backend": "mock",
        "estimate": 1.0,
        "oracle_calls": 1,
        "initialization_ms": 1.0,
        "simulation_ms": 1.0,
        "end_to_end_ms": 1.0,
        "warnings": [], "hardware": {}, "software": {}, "metadata": {}
    }
    
    if mode == "missing_request_id":
        del base_res["request_id"]
        return base_res
    elif mode == "missing_visibility":
        del base_res["estimate"]
        return base_res
    elif mode == "visibility_out_of_bounds":
        base_res["estimate"] = 1.5
        return base_res
    elif mode == "wrong_schema_version":
        base_res["schema_version"] = "2.0"
        return base_res
    elif mode == "unknown_backend":
        base_res["backend"] = "magic_backend_42"
        return base_res
    elif mode == "negative_time":
        base_res["end_to_end_ms"] = -5.0
        return base_res
    elif mode == "old_request_id":
        base_res["request_id"] = str(uuid.uuid4())
        return base_res
    else:
        return base_res

@app.get("/set_mode/{new_mode}")
def set_mode(new_mode: str):
    global mode
    mode = new_mode
    return {"mode": mode}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8080)

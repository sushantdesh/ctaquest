#create a template file for fastapi api endpoints and testing

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Optional
import aiohttp
import logging
import asyncio
from geopy.distance import geodesic
import time  # Import the time module for timing
from pathlib import Path 

from pydantic_extra_types.coordinate import Latitude, Longitude
app = FastAPI()
logger = logging.getLogger(__name__)

# Configure logging
logging.basicConfig(
    level=logging.INFO,  # Set the logging level to INFO
    format="%(asctime)s - %(levelname)s - %(message)s",  # Format for log messages
)

class Coordinates(BaseModel):
    x: Latitude
    y: Longitude


class AllBusStopCoors(BaseModel):
    coors: Coordinates
    bus_id: str

class BusIdToCoorsMapping(BaseModel):
    bus_stop: str
    coordinates: list[tuple[Coordinates]]


allStopCoors: dict[AllBusStopCoors] = []
busToStopMapping: dict[BusIdToCoorsMapping] = {}

@app.get("/", response_class=HTMLResponse)
async def render_html():
    html_path = Path("templates/index.html")  # Path to the HTML file
    if not html_path.exists():
        raise HTTPException(status_code=500, detail="HTML file not found")
    return html_path.read_text()  # Read and return the file content



@app.get("/update/cta_stop_xfers")
async def read_data_from_cta():
    url = "https://www.transitchicago.com/downloads/sch_data/CTA_STOP_XFERS.txt"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            data = await response.text()
            #TODO: maybe store this in file with timestamp and read from there to avoid multiple requests to cta servers 
            data = data.split("\n")
            global allStopCoors, busToStopMapping
            for row in data:
                columns = row.split(',')
                if len(columns) < 6:
                    continue
                busId, stopId, x, y = columns[0], columns[3], columns[4], columns[5]
                try:
                    stopCoors: Coordinates = Coordinates(x=Latitude(float(x)), y=Longitude(float(y)))
                except ValueError:
                    continue 
                allStopCoors.append(AllBusStopCoors(coors=stopCoors, bus_id=busId))
                if busId in busToStopMapping:
                    busToStopMapping[busId].append(stopCoors)
                else:
                    busToStopMapping[busId] = [stopCoors]

    return {"allStopCoors": len(allStopCoors), "busToStopMapping": busToStopMapping["146"]}




@app.post("/data/")
async def get_places(coordinates: Coordinates):
    logging.info(f"coordinates: {coordinates}")
    
    # Start timing
    start_time = time.time()
    
    if not allStopCoors or not busToStopMapping:
        logging.info("Fetching data from CTA")
        await read_data_from_cta()

    x, y = coordinates.x, coordinates.y
    origin = (x, y)  # Create a tuple for the origin coordinates
    busIds = set()

    # Use Geopy's geodesic method for distance calculation
    for stops in allStopCoors:
        stop_coords = (stops.coors.x, stops.coors.y)
        if geodesic(origin, stop_coords).meters < 500:
            busIds.add(stops.bus_id)  # Use `add` instead of `append` for a set
    

    # End timing
    end_time = time.time()
    elapsed_time = end_time - start_time
    logging.info(f"Time taken to process get_places: {elapsed_time:.4f} seconds")

    return {"x": x, "y": y, "busIds": list(busIds)}


# @app.put("/items/{item_id}")
# async def update_item(item_id: int, item: Item):
#     return {"item_name": item.name, "item_id": item_id}

# @app.delete("/items/{item_id}")
# async def delete_item(item_id: int):
#     return {"item_id": item_id}

# to run the app

# uvicorn main:app --reload
# http://
# http://
# http://

# to test the app
# http://localhost:8000/docs
# http://localhost:8000/redoc
# http://localhost:8000/items/5?q=somequery
# http://localhost:8000/items/5
# http://localhost:8000/items/
# http://localhost:8000/items/5

# to test the app using curl
# curl -X POST "http://localhost:8000/items/" -H  "accept: application/json" -H  "Content-Type: application/json" -d "{\"name\":\"string\",\"description\":\"string\",\"price\":0,\"tax\":0}"
# curl -X GET "http://localhost:8000/items/5?q=somequery" -H  "accept: application/json"
# curl -X GET "http://localhost:8000/items/5" -H  "accept: application/json"

# to test the app using python requests
# import requests

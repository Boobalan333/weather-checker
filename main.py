
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from openai import OpenAI
from mcp.server.fastmcp import FastMCP

import httpx
import os
import uvicorn

# ─────────────────────────────────────────────────────────────
# LOAD ENV
# ─────────────────────────────────────────────────────────────

load_dotenv()

OWM_KEY = os.getenv("OWM_KEY")
GROQ_KEY = os.getenv("GROQ_KEY")

# ─────────────────────────────────────────────────────────────
# FASTAPI APP
# ─────────────────────────────────────────────────────────────

app = FastAPI(title="WeatherMind MCP AI")

# ─────────────────────────────────────────────────────────────
# MCP SERVER
# ─────────────────────────────────────────────────────────────

mcp = FastMCP("WeatherMind MCP Server")

# ─────────────────────────────────────────────────────────────
# GROQ CLIENT
# ─────────────────────────────────────────────────────────────

groq_client = OpenAI(
    api_key=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,
    base_url="https://api.groq.com/openai/v1"
)

# ─────────────────────────────────────────────────────────────
# REQUEST MODEL
# ─────────────────────────────────────────────────────────────

class WeatherRequest(BaseModel):
    place: str

# ─────────────────────────────────────────────────────────────
# MCP WEATHER TOOL
# ─────────────────────────────────────────────────────────────

@mcp.tool()
async def get_weather(place: str):

    try:

        # STEP 1 → PLACE → LAT/LON

        geo_url = (
            f"https://api.openweathermap.org/geo/1.0/direct"
            f"?q={place}&limit=1&appid={OWM_KEY}"
        )

        async with httpx.AsyncClient(timeout=10) as client:
            geo_res = await client.get(geo_url)

        geo_data = geo_res.json()

        print("Geo Data:", geo_data)

        # PLACE NOT FOUND

        if not geo_data:
            return {
                "error": f"Place '{place}' not found"
            }

        location = geo_data[0]

        lat = location["lat"]
        lon = location["lon"]

        # STEP 2 → WEATHER API

        weather_url = (
            f"https://api.openweathermap.org/data/2.5/weather"
            f"?lat={lat}&lon={lon}&appid={OWM_KEY}&units=metric"
        )

        async with httpx.AsyncClient(timeout=10) as client:
            weather_res = await client.get(weather_url)

        weather_data = weather_res.json()

        print("Weather Data:", weather_data)

        # INVALID API KEY

        if str(weather_data.get("cod")) == "401":
            return {
                "error": "Invalid OpenWeather API Key"
            }

        # FINAL WEATHER DATA

        return {
            "place": location.get("name"),
            "country": location.get("country"),
            "temperature": weather_data["main"]["temp"],
            "humidity": weather_data["main"]["humidity"],
            "weather": weather_data["weather"][0]["description"],
            "wind_speed": weather_data["wind"]["speed"]
        }

    except Exception as e:

        return {
            "error": str(e)
        }

# ─────────────────────────────────────────────────────────────
# WEATHER ROUTE
# ─────────────────────────────────────────────────────────────

@app.post("/weather")
async def weather_api(req: WeatherRequest):

    weather = await get_weather(req.place)

    return weather

# ─────────────────────────────────────────────────────────────
# AI ROUTE
# ─────────────────────────────────────────────────────────────

@app.post("/ai")
async def ai_api(req: WeatherRequest):

    # GET WEATHER USING MCP TOOL

    weather = await get_weather(req.place)

    # IF ERROR

    if "error" in weather:
        return {
            "text": weather["error"]
        }

    # AI PROMPT

    prompt = f"""
    Weather Details:

    Place: {weather['place']}
    Country: {weather['country']}
    Temperature: {weather['temperature']}°C
    Humidity: {weather['humidity']}%
    Condition: {weather['weather']}
    Wind Speed: {weather['wind_speed']} m/s

    Explain the weather in a friendly way.
    Give one useful tip.
    End with a weather emoji.
    """

    # GROQ AI CALL

    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are WeatherMind AI, "
                    "a friendly weather assistant."
                )
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        max_tokens=180
    )

    ai_text = response.choices[0].message.content

    return {
        "text": ai_text,
        "weather": weather
    }

# ─────────────────────────────────────────────────────────────
# STATIC FILES
# ─────────────────────────────────────────────────────────────

app.mount(
    "/static",
    StaticFiles(directory="static"),
    name="static"
)

# ─────────────────────────────────────────────────────────────
# ROOT ROUTE
# ─────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    return FileResponse("static/index.html")

# ─────────────────────────────────────────────────────────────
# RUN SERVER
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":

    uvicorn.run(
        app,
        host="127.0.0.1",
        port=9001
    )

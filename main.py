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
OWM_KEY="1641613698e93ff0b66295c681e18210"
GROQ_KEY="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"

# ─────────────────────────────
# LOAD ENV
# ─────────────────────────────

load_dotenv()

OWM_KEY = os.getenv("OWM_KEY")
GROQ_KEY = os.getenv("GROQ_KEY")

# ─────────────────────────────
# FASTAPI APP
# ─────────────────────────────

app = FastAPI(title="WeatherMind MCP AI")

# ─────────────────────────────
# MCP SERVER
# ─────────────────────────────

mcp = FastMCP("WeatherMind MCP Server")

# ─────────────────────────────
# SAFE VALIDATION (DON'T CRASH IMPORT)
# ─────────────────────────────

def require_env(var, name):
    if not var:
        raise RuntimeError(f"{name} is missing in environment variables")

# ─────────────────────────────
# GROQ CLIENT (SAFE INIT)
# ─────────────────────────────

require_env(GROQ_KEY, "GROQ_KEY")

groq_client = OpenAI(
    api_key=GROQ_KEY,
    base_url="https://api.groq.com/openai/v1"
)

# ─────────────────────────────
# REQUEST MODEL
# ─────────────────────────────

class WeatherRequest(BaseModel):
    place: str

# ─────────────────────────────
# WEATHER TOOL
# ─────────────────────────────

@mcp.tool()
async def get_weather(place: str):

    if not OWM_KEY:
        return {"error": "OWM_KEY missing"}

    try:
        geo_url = (
            f"https://api.openweathermap.org/geo/1.0/direct"
            f"?q={place}&limit=1&appid={OWM_KEY}"
        )

        async with httpx.AsyncClient(timeout=10) as client:
            geo_res = await client.get(geo_url)

        geo_data = geo_res.json()

        if not geo_data:
            return {"error": f"Place '{place}' not found"}

        location = geo_data[0]

        lat, lon = location["lat"], location["lon"]

        weather_url = (
            f"https://api.openweathermap.org/data/2.5/weather"
            f"?lat={lat}&lon={lon}&appid={OWM_KEY}&units=metric"
        )

        async with httpx.AsyncClient(timeout=10) as client:
            weather_res = await client.get(weather_url)

        weather_data = weather_res.json()

        if str(weather_data.get("cod")) == "401":
            return {"error": "Invalid OpenWeather API Key"}

        return {
            "place": location.get("name"),
            "country": location.get("country"),
            "temperature": weather_data["main"]["temp"],
            "humidity": weather_data["main"]["humidity"],
            "weather": weather_data["weather"][0]["description"],
            "wind_speed": weather_data["wind"]["speed"]
        }

    except Exception as e:
        return {"error": str(e)}

# ─────────────────────────────
# WEATHER API
# ─────────────────────────────

@app.post("/weather")
async def weather_api(req: WeatherRequest):
    return await get_weather(req.place)

# ─────────────────────────────
# AI API
# ─────────────────────────────

@app.post("/ai")
async def ai_api(req: WeatherRequest):

    weather = await get_weather(req.place)

    if "error" in weather:
        return {"text": weather["error"]}

    prompt = f"""
Weather Details:

Place: {weather['place']}
Country: {weather['country']}
Temperature: {weather['temperature']}°C
Humidity: {weather['humidity']}%
Condition: {weather['weather']}
Wind Speed: {weather['wind_speed']} m/s

Explain simply + give tip + emoji.
"""

    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": "You are WeatherMind AI assistant."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=180
    )

    return {
        "text": response.choices[0].message.content,
        "weather": weather
    }

# ─────────────────────────────
# STATIC FILES
# ─────────────────────────────



if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")
# ─────────────────────────────
# ROOT
# ─────────────────────────────

@app.get("/")
async def root():
    return FileResponse("static/index.html")

# ─────────────────────────────
# LOCAL RUN ONLY
# ─────────────────────────────

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=9001)

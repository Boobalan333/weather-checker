**WeatherMind AI**
User → FastAPI → MCP Tool → OpenWeather API → Groq AI → Response

**Tech Stack**
- Python 
- FastAPI 
- OpenWeather API 
- Groq AI 
- MCP (Model Context Protocol / Tool Layer)
- HTTPX

**Setup & Run Commands:**
Create virtual environment : python -m venv venv
Activate environment : venv\Scripts\activate
Install dependencies  :  pip install fastapi uvicorn httpx python-dotenv openai mcp
Run server:  uvicorn app:app --reload --port 9001   (or) python main.py
open in browser : http://127.0.0.1:9001

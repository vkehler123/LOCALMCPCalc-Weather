print("Server started and running MCP...")

import math
import requests
import os
import sqlite3
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

load_dotenv()
API_KEY = os.getenv("WEATHER_API_KEY") or ""

mcp = FastMCP("Weather and Calculator")

# ---------------------------
# SQLite Setup
# ---------------------------

DB_PATH = "calculator.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS calculations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            operation TEXT,
            operand1 REAL,
            operand2 REAL,
            result REAL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def log_calc(operation, a, b, result):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        INSERT INTO calculations (operation, operand1, operand2, result)
        VALUES (?, ?, ?, ?)
    ''', (operation, a, b, result))
    conn.commit()
    conn.close()

@mcp.tool()
def get_recent_calculations(n: int = 5) -> list:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        SELECT operation, operand1, operand2, result, timestamp
        FROM calculations
        ORDER BY timestamp DESC
        LIMIT ?
    ''', (n,))
    rows = c.fetchall()
    conn.close()
    return [
        {
            "operation": op,
            "a": a,
            "b": b,
            "result": result,
            "timestamp": ts
        }
        for (op, a, b, result, ts) in rows
    ]

# ---------------------------
# Ollama Chat Tool (async)
# ---------------------------
@mcp.tool()
async def ollama_chat(prompt: str) -> str:
    import json
    import httpx

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:11434/api/chat",
                json={
                    "model": "gemma:2b",
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": False
                },
                timeout=30.0,
            )

        if response.status_code == 200:
            raw = response.text
            try:
                data = json.loads(raw.strip().split('\n')[0])
                return data.get("message", {}).get("content", "[No content]")
            except Exception as e:
                return f"Error parsing Ollama response: {e}\nRaw: {raw}"

        return f"Error from Ollama: {response.status_code} - {response.text}"
    except Exception as e:
        return f"Exception during Ollama call: {e}"


# ---------------------------
# Calculator Tools
# ---------------------------
@mcp.tool()
def add(a: int, b: int) -> int:
    result = a + b
    log_calc("add", a, b, result)
    return result

@mcp.tool()
def subtract(a: int, b: int) -> int:
    result = a - b
    log_calc("subtract", a, b, result)
    return result

@mcp.tool()
def multiply(a: int, b: int) -> int:
    result = a * b
    log_calc("multiply", a, b, result)
    return result

@mcp.tool()
def divide(a: int, b: int) -> float:
    result = a / b
    log_calc("divide", a, b, result)
    return result

@mcp.tool()
def power(a: int, b: int) -> int:
    result = a ** b
    log_calc("power", a, b, result)
    return result

@mcp.tool()
def sqrt(a: int) -> float:
    result = math.sqrt(a)
    log_calc("sqrt", a, 0, result)
    return result

@mcp.tool()
def cosine(a: int) -> float:
    result = math.cos(a)
    log_calc("cosine", a, 0, result)
    return result

@mcp.tool()
def sine(a: int) -> float:
    result = math.sin(a)
    log_calc("sine", a, 0, result)
    return result

@mcp.tool()
def tangent(a: int) -> float:
    result = math.tan(a)
    log_calc("tangent", a, 0, result)
    return result

@mcp.tool()
def acos(a: float) -> float:
    result = math.acos(a)
    log_calc("acos", a, 0, result)
    return result

@mcp.tool()
def asin(a: float) -> float:
    result = math.asin(a)
    log_calc("asin", a, 0, result)
    return result

# ---------------------------
# Weather Tools
# ---------------------------
def get_coordinates(city_name: str):
    url = "http://api.openweathermap.org/geo/1.0/direct"
    params = {"q": city_name, "limit": 1, "appid": API_KEY}
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        if not data:
            return None, None
        return data[0]["lat"], data[0]["lon"]
    except Exception:
        return None, None

@mcp.tool()
def get_weather_forecast(city_name: str) -> dict:
    city_name = city_name.replace(",", "").strip()

    lat, lon = get_coordinates(city_name)
    if lat is None or lon is None:
        return {"error": f"Could not find location for '{city_name}'."}

    current_url = "https://api.openweathermap.org/data/2.5/weather"
    current_params = {
        "lat": lat,
        "lon": lon,
        "units": "imperial",
        "appid": API_KEY,
    }
    current_data = requests.get(current_url, params=current_params).json()

    forecast_url = "https://api.openweathermap.org/data/2.5/forecast"
    forecast_params = {
        "lat": lat,
        "lon": lon,
        "units": "imperial",
        "appid": API_KEY,
    }
    forecast_data = requests.get(forecast_url, params=forecast_params).json()

    current_temp = round(current_data.get("main", {}).get("temp", 0))
    current_condition = current_data.get("weather", [{}])[0].get("description", "Unknown").capitalize()

    daily_forecast = []
    seen_dates = set()
    for item in forecast_data.get("list", []):
        dt_txt = item["dt_txt"]
        if "12:00:00" in dt_txt:
            date = dt_txt.split(" ")[0]
            if date not in seen_dates:
                seen_dates.add(date)
                temp = round(item["main"]["temp"])
                desc = item["weather"][0]["description"].capitalize()
                daily_forecast.append({"date": date, "temp": temp, "condition": desc})
        if len(daily_forecast) >= 5:
            break

    return {
        "city": city_name,
        "current_temp": f"{current_temp}°F",
        "current_condition": current_condition,
        "5_day_forecast": daily_forecast,
    }

# ---------------------------
# Run the server
# ---------------------------
if __name__ == "__main__":
    init_db()
    mcp.run()

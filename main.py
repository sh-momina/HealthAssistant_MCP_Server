from fastmcp import FastMCP
import requests
import os
import json
from dotenv import load_dotenv

from pathlib import Path
env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path)

# Initialize MCP server
app = FastMCP("SmartRoute_MCP_Server", version="1.0.0")

# 🌍 Get location
@app.tool()
def get_location():
    """Get user's approximate location using IP-based geolocation."""
    try:
        response = requests.get("https://ipapi.co/json/", timeout=5)
        if response.status_code != 200:
            return {"error": f"HTTP {response.status_code}", "text": response.text}
        data = response.json()
        return {
            "city": data.get("city", "Unknown"),
            "lat": data.get("latitude", 0),
            "lon": data.get("longitude", 0)
        }
    except Exception as e:
        return {"error": str(e)}


# 🌦️ Get weather (Open-Meteo)
@app.tool()
def get_weather(lat: float, lon: float):
    """Get current weather using Open-Meteo API (no API key required)."""
    try:
        url = (
            f"https://api.open-meteo.com/v1/forecast?"
            f"latitude={lat}&longitude={lon}"
            f"&current=temperature_2m,relative_humidity_2m,wind_speed_10m"
        )
        data = requests.get(url, timeout=5).json()
        current = data.get("current", {})
        if not current:
            return {"error": "No weather data returned", "raw": data}
        return {
            "temperature": current.get("temperature_2m", "N/A"),
            "humidity": current.get("relative_humidity_2m", "N/A"),
            "wind_speed": current.get("wind_speed_10m", "N/A")
        }
    except Exception as e:
        return {"error": str(e)}


# 🌫️ Get air quality (OpenAQ)
@app.tool
def get_air_quality(city: str):
    """
    Get air quality using OpenAQ v3 API (lat/lon-based).
    Falls back to Open-Meteo modeled air-quality if no station data is found.
    """

    # --- Load .env safely ---
    env_path = Path(__file__).resolve().parent / ".env"
    load_dotenv(dotenv_path=env_path)
    api_key = os.getenv("OPENAQ_API_KEY")
    if not api_key:
        return {"error": "Missing OpenAQ API key. Please set OPENAQ_API_KEY in .env"}

    # --- Step 1: Geocode city name (Open-Meteo) ---
    try:
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1&language=en&format=json"
        geo_res = requests.get(geo_url, timeout=10)
        geo_res.raise_for_status()
        geo_data = geo_res.json()
        if "results" not in geo_data or not geo_data["results"]:
            return {"error": f"Could not geocode city '{city}'"}
        lat = geo_data["results"][0]["latitude"]
        lon = geo_data["results"][0]["longitude"]
    except Exception as e:
        return {"error": f"Geocoding failed for {city}: {e}"}

    # --- Step 2: Query OpenAQ for nearby monitoring stations ---
    try:
        aq_url = f"https://api.openaq.org/v3/locations?coordinates={lat},{lon}&radius=25000&limit=5"
        headers = {"X-API-Key": api_key}
        aq_res = requests.get(aq_url, headers=headers, timeout=10)
        aq_res.raise_for_status()
        aq_data = aq_res.json()
    except Exception as e:
        return {"error": f"OpenAQ location request failed: {e}"}

    # --- Step 3: If stations found, fetch latest PM2.5 or summary ---
    if aq_data.get("results"):
        stations = []
        for st in aq_data["results"]:
            stations.append({
                "name": st.get("name"),
                "city": st.get("city"),
                "country": st.get("country"),
                "coordinates": st.get("coordinates"),
                "parameters": [p.get("parameter") for p in st.get("parameters", [])]
            })
        return {
            "requested_city": city,
            "source": "OpenAQ Station Data",
            "stations_found": len(stations),
            "stations": stations
        }

    # --- Step 4: Fallback — Use modeled data from Open-Meteo ---
    try:
        model_url = (
            f"https://air-quality-api.open-meteo.com/v1/air-quality?"
            f"latitude={lat}&longitude={lon}&hourly=pm2_5,pm10,carbon_monoxide,ozone,nitrogen_dioxide,sulphur_dioxide"
        )
        model_res = requests.get(model_url, timeout=10)
        model_res.raise_for_status()
        model_data = model_res.json()

        hourly = model_data.get("hourly", {})
        if not hourly:
            return {"error": f"No air quality data available for {city}"}

        latest = {k: v[-1] for k, v in hourly.items() if isinstance(v, list) and v}
        return {
            "requested_city": city,
            "source": "Open-Meteo Modeled Data",
            "coordinates": {"latitude": lat, "longitude": lon},
            "measurements": latest
        }

    except Exception as e:
        return {"error": f"Fallback (Open-Meteo) failed: {e}"}


# 📊 Summarize environment
@app.tool()
def summarize_environment(city: str):
    """Summarize weather and air quality for a given city."""
    loc = get_location()
    if isinstance(loc, str):
        try:
            loc = json.loads(loc)
        except json.JSONDecodeError:
            loc = {"lat": 0, "lon": 0}

    weather = get_weather(loc.get("lat", 0), loc.get("lon", 0))
    air = get_air_quality(city)

    summary = (
        f"📍 City: {city}\n"
        f"🌡️ Temp: {weather.get('temperature', 'N/A')}°C\n"
        f"💨 Wind: {weather.get('wind_speed', 'N/A')} km/h\n"
        f"🫁 Air Quality: {air.get('nearest_city', 'N/A')}"
    )
    return {"summary": summary}


# Run the server
if __name__ == "__main__":
    app.run()
























# from fastmcp import FastMCP
# import requests
# import os
# from dotenv import load_dotenv

# load_dotenv()
# OPENAQ_API_KEY = os.getenv("OPENAQ_API_KEY")

# # ---------------------------------------------------
# # 🔹 Initialize MCP Server
# # ---------------------------------------------------
# app = FastMCP("SmartRoute_MCP_Server", version="1.0.0")

# # ---------------------------------------------------
# # 🔹 Firebase Lazy Initialization
# # ---------------------------------------------------
# db = None

# def get_db():
#     """Initialize Firebase only when first needed."""
#     global db
#     if db is None:
#         import firebase_admin
#         from firebase_admin import credentials, firestore

#         if not firebase_admin._apps:
#             cred = credentials.Certificate("key.json")
#             firebase_admin.initialize_app(cred)

#         db = firestore.client()
#     return db

# # ---------------------------------------------------
# # 🌍 Get Location
# # ---------------------------------------------------
# @app.tool()
# def get_location():
#     """Get user's approximate location using IP-based geolocation with fallback APIs."""
#     try:
#         # Try ipapi first
#         response = requests.get("https://ipapi.co/json/", timeout=5)
#         if response.status_code == 200:
#             data = response.json()
#             if data.get("city"):
#                 return {
#                     "source": "ipapi",
#                     "city": data.get("city", "Unknown"),
#                     "lat": data.get("latitude", 0),
#                     "lon": data.get("longitude", 0)
#                 }

#         # Fallback to ipinfo.io if ipapi fails or is inaccurate
#         response = requests.get("https://ipinfo.io/json", timeout=5)
#         data = response.json()
#         loc = data.get("loc", "0,0").split(",")
#         return {
#             "source": "ipinfo",
#             "city": data.get("city", "Unknown"),
#             "lat": float(loc[0]),
#             "lon": float(loc[1])
#         }

#     except Exception as e:
#         return {"error": str(e)}

# # ---------------------------------------------------
# # 🌦️ Get Weather
# # ---------------------------------------------------
# @app.tool()
# def get_weather(lat: float, lon: float):
#     """
#     Get current weather data using Open-Meteo API.
#     No API key or billing required.
#     """
#     try:
#         url = (
#             f"https://api.open-meteo.com/v1/forecast?"
#             f"latitude={lat}&longitude={lon}"
#             f"&current=temperature_2m,relative_humidity_2m,wind_speed_10m"
#         )
#         data = requests.get(url, timeout=5).json()
#         current = data.get("current", {})
#         if not current:
#             return {"error": "No weather data returned", "raw": data}
        
#         return {
#             "temperature": current.get("temperature_2m", "N/A"),
#             "humidity": current.get("relative_humidity_2m", "N/A"),
#             "wind_speed": current.get("wind_speed_10m", "N/A")
#         }
#     except Exception as e:
#         return {"error": str(e)}

# # ---------------------------------------------------
# # 🌫️ Get Air Quality (OpenAQ)
# # ---------------------------------------------------
# @app.tool()
# def get_air_quality(city: str = None):
#     """
#     Get air quality using OpenAQ v3 API (lat/lon-based).
#     Falls back to Open-Meteo geocoding if city lookup fails.
#     """
#     try:
#         import os
#         from dotenv import load_dotenv
#         load_dotenv()
#         OPENAQ_API_KEY = os.getenv("OPENAQ_API_KEY")

#         if not OPENAQ_API_KEY:
#             return {"error": "Missing OpenAQ API key"}

#         headers = {"X-API-Key": OPENAQ_API_KEY}

#         # 🌍 Step 1: Get coordinates using Open-Meteo Geocoding API
#         lat = lon = None
#         if city:
#             geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1"
#             geo_response = requests.get(geo_url, timeout=5)

#             if geo_response.status_code == 200 and geo_response.text.strip():
#                 try:
#                     geo_data = geo_response.json()
#                     if geo_data.get("results"):
#                         lat = geo_data["results"][0]["latitude"]
#                         lon = geo_data["results"][0]["longitude"]
#                 except Exception:
#                     pass

#         # Fallback if no city found
#         if not lat or not lon:
#             loc = get_location()
#             lat, lon = loc.get("lat"), loc.get("lon")

#         if not lat or not lon:
#             return {"error": f"Could not determine location for '{city}'"}

#         # 🛰️ Step 2: Find nearest station
#         aq_url = f"https://api.openaq.org/v3/locations?coordinates={lat},{lon}&radius=50000&limit=1"
#         aq_response = requests.get(aq_url, headers=headers, timeout=8)

#         if not aq_response.text.strip():
#             return {"error": f"Empty response from OpenAQ (locations): {aq_response.status_code}"}

#         try:
#             aq_data = aq_response.json()
#         except Exception:
#             return {"error": f"Non-JSON response from OpenAQ (locations): {aq_response.text[:200]}"}

#         results = aq_data.get("results", [])
#         if not results:
#             return {"error": f"No air quality stations near {city}"}

#         location_id = results[0]["id"]
#         nearest_city = results[0].get("city", "Unknown")

#         # 💨 Step 3: Get measurements
#         measure_url = f"https://api.openaq.org/v3/measurements?location_id={location_id}&limit=5"
#         measure_response = requests.get(measure_url, headers=headers, timeout=8)

#         if not measure_response.text.strip():
#             return {"error": "Empty response from OpenAQ (measurements)"}

#         try:
#             measure_data = measure_response.json()
#         except Exception:
#             return {"error": f"Invalid JSON from OpenAQ (measurements): {measure_response.text[:200]}"}

#         air_data = [
#             {
#                 "parameter": m.get("parameter"),
#                 "value": m.get("value"),
#                 "unit": m.get("unit"),
#                 "date": m.get("date", {}).get("utc")
#             }
#             for m in measure_data.get("results", [])
#         ]

#         if not air_data:
#             return {"error": f"No measurement data found for {city}"}

#         return {
#             "requested_city": city,
#             "nearest_city": nearest_city,
#             "latitude": lat,
#             "longitude": lon,
#             "measurements": air_data
#         }

#     except Exception as e:
#         return {"error": str(e)}

# # ---------------------------------------------------
# # 🧍 Save Health Report
# # ---------------------------------------------------
# @app.tool()
# def save_health_report(name: str, mood: str, activity: str, city: str):
#     """
#     Save a user's health report to Firestore.
#     """
#     db = get_db()
#     doc = {"name": name, "mood": mood, "activity": activity, "city": city}
#     db.collection("health_reports").add(doc)
#     return {"status": "saved", "data": doc}

# # ---------------------------------------------------
# # 📊 Summarize Environment
# # ---------------------------------------------------
# @app.tool()
# def summarize_environment(city: str):
#     """
#     Summarize weather and air quality for the given city.
#     """
#     loc = get_location()
#     weather = get_weather(loc["lat"], loc["lon"])
#     air = get_air_quality(city)

#     # Extract PM2.5 value if available
#     pm25 = "N/A"
#     if isinstance(air.get("measurements"), list):
#         for m in air["measurements"]:
#             if m.get("parameter") == "pm25":
#                 pm25 = m.get("value")
#                 break

#     summary = (
#         f"📍 City: {city}\n"
#         f"🌡️ Temp: {weather.get('temperature', 'N/A')}°C\n"
#         f"💨 Wind: {weather.get('wind_speed', 'N/A')} km/h\n"
#         f"🫁 Air Quality: PM2.5 = {pm25} µg/m³"
#     )
#     return {"summary": summary}

# # ---------------------------------------------------
# # 🚀 Run Server
# # ---------------------------------------------------
# if __name__ == "__main__":
#     app.run()

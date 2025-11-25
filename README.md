# HealthAssistant MCP Server  

Micro-service using FastMCP: location, weather, air-quality + optional health-report storage.

## Features  
- `get_location()` → approximate city & coordinates (IP-based).  
- `get_weather(lat, lon)` → current temperature, humidity, wind (via Open-Meteo).  
- `get_air_quality(city)` → air quality station data (via OpenAQ) or fallback modeled data.  
- `summarize_environment(city)` → combined weather & air quality summary.  

## Setup  
1. Clone the repository:  
   ```bash
   git clone https://github.com/sh-momina/HealthAssistant_MCP_Server.git
   cd SmartRoute_MCP_Server



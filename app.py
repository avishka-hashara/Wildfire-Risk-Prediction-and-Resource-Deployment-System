from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from models import TelemetryLog
from database import get_db, engine, Base
from fwi_calculator import calculate_fwi
import httpx
import uvicorn
import torch
import torch.nn as nn
import networkx as nx
import joblib
import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as ctrl

# ---------------------------------------------------------
# 1. API Configuration & CORS
# ---------------------------------------------------------
app = FastAPI(title="Wildfire Risk & Routing Engine")

@app.on_event("startup")
async def startup_event():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

INPUT_FEATURES = 10 

# ---------------------------------------------------------
# 2. Machine Learning Pipeline Setup (PyTorch & Scaler)
# ---------------------------------------------------------
print("Loading Scaler and PyTorch model into memory...")
scaler = joblib.load('wildfire_scaler.pkl')

class TunedWildfirePredictor(nn.Module):
    def __init__(self, input_size, hidden1, hidden2, dropout_rate):
        super(TunedWildfirePredictor, self).__init__()
        
        self.layer1 = nn.Linear(input_size, hidden1)
        self.dropout1 = nn.Dropout(dropout_rate) 
        self.relu1 = nn.ReLU()
        
        self.layer2 = nn.Linear(hidden1, hidden2)
        self.dropout2 = nn.Dropout(dropout_rate)
        self.relu2 = nn.ReLU()
        
        self.output_layer = nn.Linear(hidden2, 1)
        self.sigmoid = nn.Sigmoid()

    def forward(self, x):
        x = self.relu1(self.dropout1(self.layer1(x)))
        x = self.relu2(self.dropout2(self.layer2(x)))
        x = self.sigmoid(self.output_layer(x))
        return x

# Initialize and load model weights
model = TunedWildfirePredictor(input_size=INPUT_FEATURES, hidden1=32, hidden2=16, dropout_rate=0.0)
model.load_state_dict(torch.load('wildfire_production_model.pth', weights_only=True))
model.eval()

# ---------------------------------------------------------
# 3. Fuzzy Logic Expert System Setup
# ---------------------------------------------------------
print("Initializing Fuzzy Logic Engine...")
nn_prob = ctrl.Antecedent(np.arange(0, 1.01, 0.01), 'nn_probability')
wind = ctrl.Antecedent(np.arange(0, 45, 1), 'wind_speed')
risk_level = ctrl.Consequent(np.arange(0, 101, 1), 'risk_level')

nn_prob['low'] = fuzz.trimf(nn_prob.universe, [0, 0, 0.5])
nn_prob['medium'] = fuzz.trimf(nn_prob.universe, [0.25, 0.5, 0.75])
nn_prob['high'] = fuzz.trimf(nn_prob.universe, [0.5, 1.0, 1.0])

wind['calm'] = fuzz.trimf(wind.universe, [0, 0, 15])
wind['moderate'] = fuzz.trimf(wind.universe, [10, 20, 30])
wind['strong'] = fuzz.trimf(wind.universe, [25, 45, 45])

risk_level['safe'] = fuzz.trimf(risk_level.universe, [0, 0, 30])
risk_level['watch'] = fuzz.trimf(risk_level.universe, [20, 40, 60])
risk_level['alert'] = fuzz.trimf(risk_level.universe, [50, 75, 90])
risk_level['evacuate'] = fuzz.trimf(risk_level.universe, [80, 100, 100])

rule1 = ctrl.Rule(nn_prob['high'] & wind['strong'], risk_level['evacuate'])
rule2 = ctrl.Rule(nn_prob['high'] & wind['moderate'], risk_level['alert'])
rule3 = ctrl.Rule(nn_prob['high'] & wind['calm'], risk_level['watch'])
rule4 = ctrl.Rule(nn_prob['medium'] & wind['strong'], risk_level['alert'])
rule5 = ctrl.Rule(nn_prob['medium'] & wind['moderate'], risk_level['watch'])
rule6 = ctrl.Rule(nn_prob['medium'] & wind['calm'], risk_level['safe'])
rule7 = ctrl.Rule(nn_prob['low'] & wind['strong'], risk_level['watch'])
rule8 = ctrl.Rule(nn_prob['low'] & (wind['moderate'] | wind['calm']), risk_level['safe'])

risk_ctrl = ctrl.ControlSystem([rule1, rule2, rule3, rule4, rule5, rule6, rule7, rule8])

# ---------------------------------------------------------
# 4. Logistics & Graph Routing Setup
# ---------------------------------------------------------
print("Constructing routing map...")
city_map = nx.Graph()

# Reconstructing the 27-minute route path
city_map.add_edge('Fire Station Alpha', 'Highway Junction', weight=10)
city_map.add_edge('Highway Junction', 'Forest Edge', weight=10)
city_map.add_edge('Forest Edge', 'Active Fire Zone', weight=7)

# Adding an alternate, slower route for the Dijkstra algorithm to bypass
city_map.add_edge('Fire Station Alpha', 'Downtown', weight=15)
city_map.add_edge('Downtown', 'Active Fire Zone', weight=20) 

# ---------------------------------------------------------
# 5. Data Schemas
# ---------------------------------------------------------
class LocationPayload(BaseModel):
    latitude: float
    longitude: float       

# ---------------------------------------------------------
# 6. API Endpoints
# ---------------------------------------------------------
@app.get("/")
def read_root():
    return {"status": "online", "message": "Wildfire AI Backend is running."}

@app.post("/api/evaluate-risk")
async def evaluate_risk(data: LocationPayload, db: AsyncSession = Depends(get_db)):
    # 1. Fetch exact elevation to prevent temperature skew in mountainous terrain
    elevation_val = None
    elevation_param = ""
    elevation_url = f"https://api.open-meteo.com/v1/elevation?latitude={data.latitude}&longitude={data.longitude}"
    
    try:
        async with httpx.AsyncClient() as client:
            elev_resp = await client.get(elevation_url, timeout=5.0)
            elev_resp.raise_for_status()
            elev_data = elev_resp.json()
            if "elevation" in elev_data and len(elev_data["elevation"]) > 0:
                elevation_val = elev_data["elevation"][0]
                elevation_param = f"&elevation={elevation_val}"
    except Exception as e:
        print(f"Warning: Elevation fetch failed, falling back to default DEM: {e}")

    # 2. Fetch real-time data from Open-Meteo
    url = f"https://api.open-meteo.com/v1/forecast?latitude={data.latitude}&longitude={data.longitude}{elevation_param}&current=temperature_2m,relative_humidity_2m,wind_speed_10m,rain"
    
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, timeout=10.0)
            resp.raise_for_status()
            weather_data = resp.json()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch environmental data: {str(e)}")
        
    current = weather_data.get("current", {})
    
    # Extract values, gracefully handling missing data with defaults
    temp = current.get("temperature_2m", 40.5)
    rh = current.get("relative_humidity_2m", 15.0)
    ws = current.get("wind_speed_10m", 28.5)
    rain = current.get("rain", 0.0)
    
    # Query database for the most recent log at this exact location
    stmt = (
        select(TelemetryLog)
        .where(TelemetryLog.latitude == data.latitude)
        .where(TelemetryLog.longitude == data.longitude)
        .order_by(desc(TelemetryLog.timestamp))
        .limit(1)
    )
    result = await db.execute(stmt)
    prev_log = result.scalar_one_or_none()
    
    # If a previous log exists and has FWI data, pass them as previous day's metrics
    if prev_log and prev_log.ffmc is not None and prev_log.dmc is not None and prev_log.dc is not None:
        fwi_results = calculate_fwi(temp, rh, ws, rain, prev_ffmc=prev_log.ffmc, prev_dmc=prev_log.dmc, prev_dc=prev_log.dc)
    else:
        # Brand new location, use standard spring startup defaults
        fwi_results = calculate_fwi(temp, rh, ws, rain)
        
    ffmc = fwi_results["FFMC"]
    dmc = fwi_results["DMC"]
    dc = fwi_results["DC"]
    isi = fwi_results["ISI"]
    bui = fwi_results["BUI"]
    fwi = fwi_results["FWI"]

    # Extract raw values into a 2D numpy array in the exact order the model expects
    raw_values = np.array([[
        temp, rh, ws, rain, 
        ffmc, dmc, dc, isi, 
        bui, fwi
    ]])
    
    # Transform the raw values using the loaded scikit-learn scaler
    scaled_values = scaler.transform(raw_values)
    
    # Convert the scaled values to a PyTorch tensor
    input_data = torch.tensor(scaled_values, dtype=torch.float32)
    
    # 1. Run Neural Network Inference
    with torch.no_grad():
        nn_prediction = model(input_data).item()
        
    # 2. Evaluate Fuzzy Logic Rules
    risk_simulator = ctrl.ControlSystemSimulation(risk_ctrl)
    risk_simulator.input['nn_probability'] = nn_prediction
    risk_simulator.input['wind_speed'] = ws
    risk_simulator.compute()
    
    # 3. Calculate Final Actionable Score
    final_risk_score = risk_simulator.output['risk_level']
    needs_evacuation = final_risk_score >= 80
    
    response = {
        "risk_probability_percentage": round(final_risk_score, 2),
        "evacuation_required": bool(needs_evacuation),
        "environmental_data": {
            "Temperature": temp,
            "RH": rh,
            "Ws": ws,
            "Rain": rain,
            "FFMC": ffmc,
            "DMC": dmc,
            "DC": dc,
            "ISI": isi,
            "BUI": bui,
            "FWI": fwi
        },
        "payload_received": data.model_dump()
    }
    
    # 4. Conditionally execute routing logic if threshold is breached
    if needs_evacuation:
        route = nx.shortest_path(city_map, source='Fire Station Alpha', target='Active Fire Zone', weight='weight')
        travel_time = nx.shortest_path_length(city_map, source='Fire Station Alpha', target='Active Fire Zone', weight='weight')
        
        response["logistics"] = {
            "optimal_route": route,
            "estimated_time_mins": travel_time
        }
        
    # 5. Log the assessment to PostgreSQL
    new_log = TelemetryLog(
        latitude=data.latitude,
        longitude=data.longitude,
        elevation=elevation_val,
        temperature=temp,
        humidity=rh,
        wind_speed=ws,
        rain=rain,
        ffmc=ffmc,
        dmc=dmc,
        dc=dc,
        isi=isi,
        bui=bui,
        fwi=fwi,
        risk_probability=final_risk_score,
        evacuation_authorized=bool(needs_evacuation)
    )
    db.add(new_log)
    await db.commit()
    await db.refresh(new_log)
        
    return response

# ---------------------------------------------------------
# 7. Telemetry History API Endpoint
# ---------------------------------------------------------
@app.get("/api/telemetry-history")
async def get_telemetry_history(latitude: float, longitude: float, db: AsyncSession = Depends(get_db)):
    stmt = (
        select(TelemetryLog)
        .where(TelemetryLog.latitude == latitude)
        .where(TelemetryLog.longitude == longitude)
        .order_by(desc(TelemetryLog.timestamp))
        .limit(15)
    )
    result = await db.execute(stmt)
    logs = result.scalars().all()
    
    # Reverse to ensure chronological order (oldest to newest left-to-right on chart)
    history = []
    for log in reversed(logs):
        history.append({
            "timestamp": log.timestamp.isoformat(),
            "fwi": log.fwi,
            "dc": log.dc,
            "risk_probability": log.risk_probability
        })
        
    return history

# ---------------------------------------------------------
# 8. Server Execution
# ---------------------------------------------------------
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
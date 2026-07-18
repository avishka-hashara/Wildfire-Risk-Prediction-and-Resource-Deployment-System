from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import torch
import torch.nn as nn
import networkx as nx
import joblib
import numpy as np

# ---------------------------------------------------------
# 1. API Configuration & CORS
# ---------------------------------------------------------
app = FastAPI(title="Wildfire Risk & Routing Engine")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

INPUT_FEATURES = 10 

# ---------------------------------------------------------
# 2. Machine Learning Pipeline Setup
# ---------------------------------------------------------
print("Loading Scaler and PyTorch model into memory...")
# Load the scaler exported from your Jupyter Notebook
scaler = joblib.load('wildfire_scaler.pkl')

class TunedWildfirePredictor(nn.Module):
    def __init__(self, input_size, hidden1, hidden2, dropout_rate):
        super(TunedWildfirePredictor, self).__init__()
        self.layer1 = nn.Linear(input_size, hidden1)
        self.relu1 = nn.ReLU()
        self.dropout1 = nn.Dropout(dropout_rate)
        self.layer2 = nn.Linear(hidden1, hidden2)
        self.relu2 = nn.ReLU()
        self.dropout2 = nn.Dropout(dropout_rate)
        self.output = nn.Linear(hidden2, 1)
        self.sigmoid = nn.Sigmoid()

    def forward(self, x):
        x = self.relu1(self.layer1(x))
        x = self.dropout1(x)
        x = self.relu2(self.layer2(x))
        x = self.dropout2(x)
        x = self.sigmoid(self.output(x))
        return x

# Initialize and load model weights
model = TunedWildfirePredictor(input_size=INPUT_FEATURES, hidden1=32, hidden2=16, dropout_rate=0.0)
model.load_state_dict(torch.load('wildfire_production_model.pth', weights_only=True))
model.eval()

# ---------------------------------------------------------
# 3. Logistics & Graph Routing Setup
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
# 4. Data Schemas
# ---------------------------------------------------------
class EnvironmentalPayload(BaseModel):
    Temperature: float
    RH: float        
    Ws: float        
    Rain: float
    FFMC: float      
    DMC: float       
    DC: float        
    ISI: float       
    BUI: float       
    FWI: float       

# ---------------------------------------------------------
# 5. API Endpoints
# ---------------------------------------------------------
@app.get("/")
def read_root():
    return {"status": "online", "message": "Wildfire AI Backend is running."}

@app.post("/api/evaluate-risk")
def evaluate_risk(data: EnvironmentalPayload):
    # Extract raw values into a 2D numpy array in the exact order the model expects
    raw_values = np.array([[
        data.Temperature, data.RH, data.Ws, data.Rain, 
        data.FFMC, data.DMC, data.DC, data.ISI, 
        data.BUI, data.FWI
    ]])
    
    # Transform the raw values using the loaded scikit-learn scaler
    scaled_values = scaler.transform(raw_values)
    
    # Convert the scaled values to a PyTorch tensor
    input_data = torch.tensor(scaled_values, dtype=torch.float32)
    
    # Run inference
    with torch.no_grad():
        risk_prob = model(input_data).item()
        
    needs_evacuation = risk_prob > 0.85
    
    response = {
        "risk_probability_percentage": round(risk_prob * 100, 2),
        "evacuation_required": needs_evacuation,
        "payload_received": data.model_dump()
    }
    
    # Conditionally execute routing logic if threshold is breached
    if needs_evacuation:
        route = nx.shortest_path(city_map, source='Fire Station Alpha', target='Active Fire Zone', weight='weight')
        travel_time = nx.shortest_path_length(city_map, source='Fire Station Alpha', target='Active Fire Zone', weight='weight')
        
        response["logistics"] = {
            "optimal_route": route,
            "estimated_time_mins": travel_time
        }
        
    return response

# ---------------------------------------------------------
# 6. Server Execution
# ---------------------------------------------------------
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
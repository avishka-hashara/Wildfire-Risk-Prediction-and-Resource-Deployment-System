from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
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
# 6. API Endpoints
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
    
    # 1. Run Neural Network Inference
    with torch.no_grad():
        nn_prediction = model(input_data).item()
        
    # 2. Evaluate Fuzzy Logic Rules
    risk_simulator = ctrl.ControlSystemSimulation(risk_ctrl)
    risk_simulator.input['nn_probability'] = nn_prediction
    risk_simulator.input['wind_speed'] = data.Ws
    risk_simulator.compute()
    
    # 3. Calculate Final Actionable Score
    final_risk_score = risk_simulator.output['risk_level']
    needs_evacuation = final_risk_score >= 80
    
    response = {
        "risk_probability_percentage": round(final_risk_score, 2),
        "evacuation_required": bool(needs_evacuation),
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
        
    return response

# ---------------------------------------------------------
# 7. Server Execution
# ---------------------------------------------------------
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
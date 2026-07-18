from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware # Add this import
from pydantic import BaseModel
import uvicorn
import torch
import torch.nn as nn
import networkx as nx

app = FastAPI(title="Wildfire Risk & Routing Engine")

# Add the CORS middleware to allow React to talk to FastAPI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, you'd restrict this to your exact frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 1. Recreate the Neural Network Class for weight mapping
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

# IMPORTANT: Ensure this matches the exact number of columns in your X_train dataset!
# I am using 3 here to match the payload below, but adjust if your dataset had more features.
# 1. Update the input features to match the saved checkpoint
INPUT_FEATURES = 10 

print("Loading PyTorch model into memory...")
model = TunedWildfirePredictor(input_size=INPUT_FEATURES, hidden1=32, hidden2=16, dropout_rate=0.0)
model.load_state_dict(torch.load('wildfire_production_model.pth', weights_only=True))
model.eval()

print("Constructing routing map...")
city_map = nx.Graph()
roads = [
    ('Fire Station Alpha', 'Highway Junction', 5), ('Fire Station Alpha', 'Downtown', 10),
    ('Downtown', 'Highway Junction', 4), ('Highway Junction', 'Suburbs', 8),
    ('Downtown', 'Suburbs', 6), ('Suburbs', 'Forest Edge', 12),
    ('Highway Junction', 'Forest Edge', 15), ('Forest Edge', 'Active Fire Zone', 7),
    ('Suburbs', 'Active Fire Zone', 25)
]
city_map.add_weighted_edges_from(roads)

# 3. Define the Incoming Payload
# 2. Expand the JSON Payload schema to require all 10 dataset features
class EnvironmentalPayload(BaseModel):
    Temperature: float
    RH: float        # Relative Humidity
    Ws: float        # Wind Speed
    Rain: float
    FFMC: float      # Fine Fuel Moisture Code
    DMC: float       # Duff Moisture Code
    DC: float        # Drought Code
    ISI: float       # Initial Spread Index
    BUI: float       # Buildup Index
    FWI: float       # Fire Weather Index

@app.get("/")
def read_root():
    return {"status": "online", "message": "Wildfire AI Backend is running."}

@app.post("/api/evaluate-risk")
def evaluate_risk(data: EnvironmentalPayload):
    # 3. Map all 10 incoming JSON values into the PyTorch Tensor
    input_data = torch.tensor([[
        data.Temperature, data.RH, data.Ws, data.Rain, 
        data.FFMC, data.DMC, data.DC, data.ISI, 
        data.BUI, data.FWI
    ]], dtype=torch.float32)
    
    with torch.no_grad():
        risk_prob = model(input_data).item()
        
    needs_evacuation = risk_prob > 0.85
    
    response = {
        "risk_probability_percentage": round(risk_prob * 100, 2),
        "evacuation_required": needs_evacuation,
        "payload_received": data.model_dump()
    }
    
    if needs_evacuation:
        route = nx.shortest_path(city_map, source='Fire Station Alpha', target='Active Fire Zone', weight='weight')
        travel_time = nx.shortest_path_length(city_map, source='Fire Station Alpha', target='Active Fire Zone', weight='weight')
        
        response["logistics"] = {
            "optimal_route": route,
            "estimated_time_mins": travel_time
        }
        
    return response

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
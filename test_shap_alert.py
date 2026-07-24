import asyncio
import torch
import numpy as np
import networkx as nx
from skfuzzy import control as ctrl

import app
from telegram_alert import send_telegram_alert

async def force_alert():
    print("Forcing an extreme weather scenario to test SHAP Explainable AI...")
    
    # 1. Simulate extreme weather values
    # Test Case 2: Searing Heat & Bone-Dry Humidity
    # This should shift the SHAP driving factors away from Wind Speed and FWI
    # and towards Temperature and RH.
    raw_values = np.array([[
        40.0,  # Temp
        15.0,  # RH
        0.0,   # Wind Speed (Set to 0 for NN so it has no positive SHAP contribution)
        0.0,   # Rain
        90.0,  # FFMC
        350.0, # DMC (Extreme)
        1200.0,# DC (Extreme drought)
        10.0,  # ISI
        250.0, # BUI
        20.0   # FWI
    ]])
    
    # 2. Scale & Predict
    scaled_values = app.scaler.transform(raw_values)
    input_tensor = torch.tensor(scaled_values, dtype=torch.float32)
    
    with torch.no_grad():
        nn_prediction = app.model(input_tensor).item()
        
    print(f"Neural Network Probability: {nn_prediction:.2f}")
        
    # 3. Fuzzy Logic
    risk_simulator = ctrl.ControlSystemSimulation(app.risk_ctrl)
    risk_simulator.input['nn_probability'] = nn_prediction
    risk_simulator.input['wind_speed'] = 45.0  # Force high here to pass the 85.0% threshold
    risk_simulator.compute()
    
    final_risk_score = risk_simulator.output['risk_level']
    print(f"Fuzzy Logic Final Risk Score: {final_risk_score:.2f}%\n")
    
    # 4. SHAP Explanation & Alert
    if final_risk_score > 85.0:
        print("🚨 Threat level breached 85.0%! Calculating SHAP features...")
        driving_factors = "Cumulative Risk Factors"
        
        if app.explainer is not None:
            shap_vals = app.explainer.shap_values(input_tensor)
            # Robustly extract the 10 feature SHAP values
            vals = np.array(shap_vals).flatten()
            if vals.size >= 10:
                vals = vals[-10:]  # Get the 10 features (handles if SHAP returns 2 classes)
            
            top_indices = np.argsort(vals)[-2:][::-1]
            factors = [app.FEATURE_NAMES[int(idx)] for idx in top_indices if vals[int(idx)] > 0]
            if factors:
                driving_factors = " and ".join(factors)
                
        print(f"XAI Driving Factors Computed: {driving_factors}")
        print("Dispatching Telegram Alert...")
        
        # Dispatch Telegram
        route = nx.shortest_path(app.city_map, source='Fire Station Alpha', target='Active Fire Zone', weight='weight')
        travel_time = nx.shortest_path_length(app.city_map, source='Fire Station Alpha', target='Active Fire Zone', weight='weight')
        
        await send_telegram_alert(
            latitude=36.4613, # Death Valley Dummy Coordinates
            longitude=-116.8656, 
            risk_level=round(final_risk_score, 2), 
            route=route, 
            travel_time=travel_time, 
            driving_factors=driving_factors
        )
        print("✅ Alert dispatched! Check your Telegram.")
    else:
        print("Threat level didn't reach 85.0%.")

if __name__ == "__main__":
    asyncio.run(force_alert())

import asyncio
import httpx
import torch
import numpy as np
import networkx as nx
from sqlalchemy import select, desc
from skfuzzy import control as ctrl

from database import AsyncSessionLocal
from models import TelemetryLog
from fwi_calculator import calculate_fwi
from telegram_alert import send_telegram_alert

async def run_sentry_scan():
    # Import app locally to avoid circular imports during startup
    import app
    print("Starting Sentry Scan across all historical sectors...")
    
    async with AsyncSessionLocal() as session:
        # 3. Query the TelemetryLog table for a list of all UNIQUE latitude and longitude pairs
        stmt = select(TelemetryLog.latitude, TelemetryLog.longitude).distinct()
        result = await session.execute(stmt)
        unique_coords = result.all()
        
        if not unique_coords:
            print("No sectors currently tracked in the database. Sentry scan aborted.")
            return

        batch_tensors = []
        batch_coords = []
        batch_fwi_data = []

        # 4. Loop through each unique coordinate pair
        for lat, lng in unique_coords:
            print(f"Fetching data for sector: {lat}, {lng}...")
            
            # Fetch elevation
            elevation_val = None
            elevation_param = ""
            elevation_url = f"https://api.open-meteo.com/v1/elevation?latitude={lat}&longitude={lng}"
            try:
                async with httpx.AsyncClient() as client:
                    elev_resp = await client.get(elevation_url, timeout=5.0)
                    if elev_resp.status_code == 200:
                        elev_data = elev_resp.json()
                        if "elevation" in elev_data and len(elev_data["elevation"]) > 0:
                            elevation_val = elev_data["elevation"][0]
                            elevation_param = f"&elevation={elevation_val}"
            except Exception as e:
                print(f"  Warning: Elevation fetch failed for {lat}, {lng}: {e}")

            # Fetch live Open-Meteo weather data via httpx
            url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lng}{elevation_param}&current=temperature_2m,relative_humidity_2m,wind_speed_10m,rain"
            try:
                async with httpx.AsyncClient() as client:
                    resp = await client.get(url, timeout=10.0)
                    if resp.status_code != 200:
                        print(f"  Warning: Weather fetch failed for {lat}, {lng} with status {resp.status_code}")
                        continue
                    weather_data = resp.json()
            except Exception as e:
                print(f"  Warning: Weather request error for {lat}, {lng}: {e}")
                continue
                
            current = weather_data.get("current", {})
            temp = current.get("temperature_2m", 40.5)
            rh = current.get("relative_humidity_2m", 15.0)
            ws = current.get("wind_speed_10m", 28.5)
            rain = current.get("rain", 0.0)
            
            # Query the database for the most recent previous FWI log for this specific coordinate
            recent_stmt = (
                select(TelemetryLog)
                .where(TelemetryLog.latitude == lat)
                .where(TelemetryLog.longitude == lng)
                .order_by(desc(TelemetryLog.timestamp))
                .limit(1)
            )
            recent_result = await session.execute(recent_stmt)
            prev_log = recent_result.scalar_one_or_none()
            
            # Run calculate_fwi using the previous log's metrics
            if prev_log and prev_log.ffmc is not None and prev_log.dmc is not None and prev_log.dc is not None:
                fwi_results = calculate_fwi(temp, rh, ws, rain, prev_ffmc=prev_log.ffmc, prev_dmc=prev_log.dmc, prev_dc=prev_log.dc)
            else:
                fwi_results = calculate_fwi(temp, rh, ws, rain)
                
            ffmc = fwi_results["FFMC"]
            dmc = fwi_results["DMC"]
            dc = fwi_results["DC"]
            isi = fwi_results["ISI"]
            bui = fwi_results["BUI"]
            fwi = fwi_results["FWI"]

            # Convert to tensor and add to batch
            raw_values = np.array([[
                temp, rh, ws, rain, 
                ffmc, dmc, dc, isi, 
                bui, fwi
            ]])
            
            scaled_values = app.scaler.transform(raw_values)
            input_data = torch.tensor(scaled_values, dtype=torch.float32).squeeze(0)
            
            batch_tensors.append(input_data)
            batch_coords.append((lat, lng))
            batch_fwi_data.append({
                "elevation": elevation_val,
                "temp": temp, "rh": rh, "ws": ws, "rain": rain,
                "ffmc": ffmc, "dmc": dmc, "dc": dc, "isi": isi, "bui": bui, "fwi": fwi
            })

        if not batch_tensors:
            print("No valid data points fetched. Sentry scan aborted.")
            return

        # Stack into 2D tensor [batch_size, 10]
        batch_tensor = torch.stack(batch_tensors)
        
        try:
            # Move entire batch to GPU
            batch_tensor = batch_tensor.to('cuda')
            app.model.to('cuda')
            
            print(f"Running batch GPU inference on {len(batch_tensors)} sectors...")
            with torch.no_grad():
                predictions = app.model(batch_tensor)
                
            # Move results back to CPU for fuzzy logic
            predictions = predictions.cpu()
        finally:
            # Ensure memory is cleaned up and model returns to CPU
            app.model.to('cpu')
            if 'batch_tensor' in locals():
                del batch_tensor
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            
        new_logs = []
        for i in range(len(batch_coords)):
            lat, lng = batch_coords[i]
            data = batch_fwi_data[i]
            nn_prediction = predictions[i].item()
            
            risk_simulator = ctrl.ControlSystemSimulation(app.risk_ctrl)
            risk_simulator.input['nn_probability'] = nn_prediction
            risk_simulator.input['wind_speed'] = data["ws"]
            risk_simulator.compute()
            
            final_risk_score = risk_simulator.output['risk_level']
            needs_evacuation = final_risk_score >= 80

            print(f"  Sector {lat},{lng} Result: Threat Level {round(final_risk_score, 2)}%")

            # Alert Trigger
            if final_risk_score > 85.0:
                print(f"  🚨 Threat level breached 85.0%! Dispatching Telegram alert...")
                
                # SHAP Explanation
                driving_factors = "Cumulative Risk Factors"
                if app.explainer is not None:
                    try:
                        sector_tensor = batch_tensors[i].unsqueeze(0).to('cpu')
                        app.model.to('cpu')
                        
                        shap_vals = app.explainer.shap_values(sector_tensor)
                        vals = np.array(shap_vals).flatten()
                        if vals.size >= 10:
                            vals = vals[-10:]
                            
                        top_indices = np.argsort(vals)[-2:][::-1]
                        factors = [app.FEATURE_NAMES[int(idx)] for idx in top_indices if vals[int(idx)] > 0]
                        if factors:
                            driving_factors = " and ".join(factors)
                    except Exception as e:
                        print(f"  Warning: SHAP explanation failed: {e}")

                route = nx.shortest_path(app.city_map, source='Fire Station Alpha', target='Active Fire Zone', weight='weight')
                travel_time = nx.shortest_path_length(app.city_map, source='Fire Station Alpha', target='Active Fire Zone', weight='weight')
                await send_telegram_alert(lat, lng, round(final_risk_score, 2), route=route, travel_time=travel_time, driving_factors=driving_factors)

            # Prepare Bulk Insert
            new_log = TelemetryLog(
                latitude=lat,
                longitude=lng,
                elevation=data["elevation"],
                temperature=data["temp"],
                humidity=data["rh"],
                wind_speed=data["ws"],
                rain=data["rain"],
                ffmc=data["ffmc"],
                dmc=data["dmc"],
                dc=data["dc"],
                isi=data["isi"],
                bui=data["bui"],
                fwi=data["fwi"],
                risk_probability=final_risk_score,
                evacuation_authorized=bool(needs_evacuation)
            )
            new_logs.append(new_log)
            
        # Execute Bulk Insert
        session.add_all(new_logs)
        await session.commit()
            
        # End message
        print(f"\nSentry Scan Complete: Processed {len(batch_coords)} sectors via GPU batch inference.")

if __name__ == "__main__":
    asyncio.run(run_sentry_scan())

import asyncio
import httpx
import torch
import numpy as np
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

        # 4. Loop through each unique coordinate pair
        for lat, lng in unique_coords:
            print(f"Scanning sector: {lat}, {lng}...")
            
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

            # 5a. Fetch live Open-Meteo weather data via httpx
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
            
            # 5b. Query the database for the most recent previous FWI log for this specific coordinate
            recent_stmt = (
                select(TelemetryLog)
                .where(TelemetryLog.latitude == lat)
                .where(TelemetryLog.longitude == lng)
                .order_by(desc(TelemetryLog.timestamp))
                .limit(1)
            )
            recent_result = await session.execute(recent_stmt)
            prev_log = recent_result.scalar_one_or_none()
            
            # 5c. Run calculate_fwi using the previous log's metrics
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

            # 5d. Pass the 10-feature array through the PyTorch model
            raw_values = np.array([[
                temp, rh, ws, rain, 
                ffmc, dmc, dc, isi, 
                bui, fwi
            ]])
            
            scaled_values = app.scaler.transform(raw_values)
            input_data = torch.tensor(scaled_values, dtype=torch.float32)
            
            with torch.no_grad():
                nn_prediction = app.model(input_data).item()
                
            risk_simulator = ctrl.ControlSystemSimulation(app.risk_ctrl)
            risk_simulator.input['nn_probability'] = nn_prediction
            risk_simulator.input['wind_speed'] = ws
            risk_simulator.compute()
            
            final_risk_score = risk_simulator.output['risk_level']
            needs_evacuation = final_risk_score >= 80

            print(f"  Result: Threat Level {round(final_risk_score, 2)}%")

            # 6. The Alert Trigger
            if final_risk_score > 85.0:
                print(f"  🚨 Threat level breached 85.0%! Dispatching Telegram alert...")
                await send_telegram_alert(lat, lng, round(final_risk_score, 2))

            # 7. The Memory Update
            new_log = TelemetryLog(
                latitude=lat,
                longitude=lng,
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
            session.add(new_log)
            await session.commit()
            
        # 8. End message
        print(f"\nSentry Scan Complete: Monitored {len(unique_coords)} sectors.")

if __name__ == "__main__":
    asyncio.run(run_sentry_scan())

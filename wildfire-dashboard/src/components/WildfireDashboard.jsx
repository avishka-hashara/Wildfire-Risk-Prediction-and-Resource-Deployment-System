import React, { useState } from 'react';
import TacticalMap from './TacticalMap';
import HistoryChart from './HistoryChart';

const WildfireDashboard = () => {
    const [targetLocation, setTargetLocation] = useState({ lat: 6.40, lng: 80.45 });
    const [riskData, setRiskData] = useState(null);
    const [isLoading, setIsLoading] = useState(false);
    const [locationName, setLocationName] = useState("Unknown Location");
    const [historicalData, setHistoricalData] = useState([]);

    const runDiagnostic = async () => {
        setIsLoading(true);

        try {
            const geoRes = await fetch(`https://api.bigdatacloud.net/data/reverse-geocode-client?latitude=${targetLocation.lat}&longitude=${targetLocation.lng}&localityLanguage=en`);
            const geoData = await geoRes.json();
            const locName = [geoData.locality, geoData.principalSubdivision, geoData.countryName].filter(Boolean).join(", ");
            setLocationName(locName || "Unknown Location");
        } catch (error) {
            console.error("Geocoding failed:", error);
            setLocationName("Unknown Location");
        }

        // We are now sending coordinates instead of the 10 manual weather/FWI metrics
        const payload = {
            latitude: targetLocation.lat,
            longitude: targetLocation.lng
        };

        try {
            const response = await fetch('http://127.0.0.1:8000/api/evaluate-risk', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            
            if (!response.ok) {
                const errData = await response.json();
                throw new Error(errData.detail || 'API Error');
            }
            
            const data = await response.json();
            setRiskData(data);
            
            // Fetch historical telemetry data
            try {
                const historyRes = await fetch(`http://127.0.0.1:8000/api/telemetry-history?latitude=${targetLocation.lat}&longitude=${targetLocation.lng}`);
                if (historyRes.ok) {
                    const historyJson = await historyRes.json();
                    setHistoricalData(historyJson);
                } else {
                    console.error("Failed to fetch historical data");
                }
            } catch (historyErr) {
                console.error("History fetch failed:", historyErr);
            }
            
        } catch (error) {
            console.error("Diagnostic failed:", error);
            alert(`Diagnostic failed: ${error.message}`);
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="min-h-screen bg-[#0f172a] text-white p-8 font-sans">

            {/* Header Section */}
            <div className="mb-8">
                <h1 className="text-3xl font-extrabold tracking-wider">
                    <span className="text-red-600">WILDFIRE AI</span> COMMAND CENTER
                </h1>
                <p className="text-gray-400 mt-2 text-sm">Live Environmental Telemetry & Logistics Routing</p>
                <hr className="border-gray-700 mt-4" />
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">

                {/* Left Column: Tactical Map (Replaces the manual 10 inputs) */}
                <div className="bg-[#1e293b] rounded-xl p-6 border border-gray-700 shadow-2xl lg:col-span-1">
                    <h2 className="text-xl font-bold mb-4 text-gray-200">System Telemetry</h2>

                    <TacticalMap onLocationSelect={setTargetLocation} />

                    <button
                        onClick={runDiagnostic}
                        disabled={isLoading}
                        className={`w-full mt-6 font-bold py-3 px-4 rounded-lg transition-colors ${isLoading
                                ? 'bg-red-800 text-gray-400 cursor-not-allowed'
                                : 'bg-red-600 hover:bg-red-700 text-white'
                            }`}
                    >
                        {isLoading ? 'ANALYZING SECTOR...' : 'RUN AI DIAGNOSTIC'}
                    </button>
                </div>

                {/* Right Column: Results & Routing */}
                <div className="lg:col-span-2 flex flex-col gap-8">

                    {/* Threat Assessment UI */}
                    <div className={`rounded-xl p-6 border shadow-2xl ${riskData?.evacuation_required
                            ? 'bg-[#1e293b] border-red-600'
                            : 'bg-[#1e293b] border-gray-700'
                        }`}>
                        <h2 className="text-xl font-bold text-gray-200 mb-2">Threat Assessment</h2>

                        <div className="text-6xl font-extrabold mb-4">
                            {riskData ? `${riskData.risk_probability_percentage}%` : '---%'}
                        </div>

                        {riskData && (
                            <div className={`text-lg font-bold tracking-wide ${riskData.evacuation_required ? 'text-red-500' : 'text-emerald-500'
                                }`}>
                                {riskData.evacuation_required
                                    ? '🚨 CRITICAL RISK: EVACUATION AUTHORIZED'
                                    : '✅ RISK ACCEPTABLE: NO ACTION REQUIRED'}
                            </div>
                        )}
                    </div>

                    {/* Environmental Telemetry Panel */}
                    {riskData && riskData.environmental_data && (
                        <div className="bg-[#1e293b] rounded-xl p-6 border border-gray-700 shadow-2xl">
                            <h2 className="text-xl font-bold text-gray-200 mb-4">Live Telemetry Data</h2>
                            
                            <div className="mb-6 pb-4 border-b border-gray-700">
                                <div className="text-sm text-gray-400 mb-1">Target Sector</div>
                                <div className="text-lg font-bold text-white">{locationName}</div>
                                <div className="text-xs text-gray-500 font-mono mt-1">Lat: {targetLocation.lat.toFixed(4)} | Lng: {targetLocation.lng.toFixed(4)}</div>
                            </div>

                            <div className="grid grid-cols-2 gap-4">
                                <div className="bg-[#0f172a] p-4 rounded-lg border border-gray-700">
                                    <div className="text-xs text-gray-500 uppercase tracking-wider mb-1">Temperature</div>
                                    <div className="text-2xl font-bold text-orange-400">{riskData.environmental_data.Temperature} °C</div>
                                </div>
                                <div className="bg-[#0f172a] p-4 rounded-lg border border-gray-700">
                                    <div className="text-xs text-gray-500 uppercase tracking-wider mb-1">Humidity (RH)</div>
                                    <div className="text-2xl font-bold text-blue-400">{riskData.environmental_data.RH} %</div>
                                </div>
                                <div className="bg-[#0f172a] p-4 rounded-lg border border-gray-700">
                                    <div className="text-xs text-gray-500 uppercase tracking-wider mb-1">Wind Speed</div>
                                    <div className="text-2xl font-bold text-gray-300">{riskData.environmental_data.Ws} km/h</div>
                                </div>
                                <div className="bg-[#0f172a] p-4 rounded-lg border border-gray-700">
                                    <div className="text-xs text-gray-500 uppercase tracking-wider mb-1">Precipitation</div>
                                    <div className="text-2xl font-bold text-cyan-400">{riskData.environmental_data.Rain} mm</div>
                                </div>
                            </div>
                        </div>
                    )}

                    {/* Logistics Routing Engine (Conditionally Rendered) */}
                    {riskData?.evacuation_required && riskData?.logistics && (
                        <div className="bg-[#1e293b] rounded-xl p-6 border border-gray-700 shadow-2xl">
                            <h2 className="text-xl font-bold text-orange-500 mb-4">Logistics Routing Engine</h2>

                            <div className="mb-6">
                                <span className="text-gray-400 text-sm">Estimated Response Time: </span>
                                <span className="text-2xl font-bold">{riskData.logistics.estimated_time_mins} Minutes</span>
                            </div>

                            <div className="p-4 bg-[#0f172a] rounded-lg border border-gray-700">
                                <div className="text-xs text-gray-500 uppercase tracking-wider mb-3">Calculated Optimal Route</div>
                                <div className="flex flex-wrap items-center gap-3">
                                    {riskData.logistics.optimal_route.map((node, index) => (
                                        <React.Fragment key={index}>
                                            <div className="bg-[#334155] px-4 py-2 rounded text-sm font-semibold text-gray-200 shadow-md">
                                                {node}
                                            </div>
                                            {index < riskData.logistics.optimal_route.length - 1 && (
                                                <div className="text-gray-500 font-bold">➔</div>
                                            )}
                                        </React.Fragment>
                                    ))}
                                </div>
                            </div>
                        </div>
                    )}

                </div>
            </div>

            {/* Sector Microclimate History Section */}
            <div className="mt-8">
                <h2 className="text-xl font-bold text-gray-200 mb-4">Sector Microclimate History</h2>
                {historicalData && historicalData.length > 0 ? (
                    <HistoryChart data={historicalData} />
                ) : (
                    <div className="w-full h-64 bg-[#1e293b] rounded-lg p-4 border border-gray-700 flex items-center justify-center text-gray-500 italic">
                        No historical data available for this sector yet.
                    </div>
                )}
            </div>

        </div>
    );
};

export default WildfireDashboard;
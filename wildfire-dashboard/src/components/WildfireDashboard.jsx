import React, { useState } from 'react';
import TacticalMap from './TacticalMap';

const WildfireDashboard = () => {
    const [targetLocation, setTargetLocation] = useState({ lat: 6.40, lng: 80.45 });
    const [riskData, setRiskData] = useState(null);
    const [isLoading, setIsLoading] = useState(false);

    const runDiagnostic = async () => {
        setIsLoading(true);

        // We are now sending coordinates instead of the 10 manual weather/FWI metrics
        const payload = {
            latitude: targetLocation.lat,
            longitude: targetLocation.lng
        };

        try {
            const response = await fetch('http://localhost:8000/api/evaluate-risk', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await response.json();
            setRiskData(data);
        } catch (error) {
            console.error("Diagnostic failed:", error);
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
        </div>
    );
};

export default WildfireDashboard;
import { useState } from 'react';
import axios from 'axios';

const parameterDescriptions = {
  Temperature: 'Temperature in Celsius degrees',
  RH: 'Relative Humidity in %',
  Ws: 'Wind speed in km/h',
  Rain: 'Outside rain in mm/m2',
  FFMC: 'Fine Fuel Moisture Code index from the FWI system',
  DMC: 'Duff Moisture Code index from the FWI system',
  DC: 'Drought Code index from the FWI system',
  ISI: 'Initial Spread Index from the FWI system',
  BUI: 'Buildup Index from the FWI system',
  FWI: 'Fire Weather Index'
};

function App() {
  const [formData, setFormData] = useState({
    Temperature: 40.5,
    RH: 15.0,
    Ws: 28.5,
    Rain: 0.0,
    FFMC: 92.1,
    DMC: 55.3,
    DC: 120.5,
    ISI: 18.2,
    BUI: 60.1,
    FWI: 25.5
  });

  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: parseFloat(e.target.value) || 0 });
  };

  const analyzeThreat = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const response = await axios.post('http://127.0.0.1:8000/api/evaluate-risk', formData);
      setResult(response.data);
    } catch (error) {
      console.error("API Error:", error);
      alert("Failed to connect to the AI Engine. Is Uvicorn running?");
    }
    setLoading(false);
  };

  return (
    <div className="min-h-screen p-8 max-w-7xl mx-auto font-sans">
      <header className="mb-8 border-b border-slate-700 pb-4">
        <h1 className="text-3xl font-bold text-red-500 tracking-wider">WILDFIRE AI <span className="text-white">COMMAND CENTER</span></h1>
        <p className="text-slate-400 mt-2">Live Environmental Telemetry & Logistics Routing</p>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">

        <div className="bg-slate-800 p-6 rounded-lg shadow-lg border border-slate-700 h-fit">
          <h2 className="text-xl font-semibold mb-4 text-slate-200">System Telemetry</h2>
          <form onSubmit={analyzeThreat} className="grid grid-cols-2 gap-4">
            {Object.keys(formData).map((key) => (
              <div key={key} className="flex flex-col">
                <label className="text-xs text-slate-400 mb-1 flex items-center w-fit relative group">
                  {key}
                  <span className="ml-1 flex items-center justify-center w-3.5 h-3.5 rounded-full border border-slate-500 text-[10px] font-bold text-slate-400 cursor-help hover:text-white hover:border-white transition-colors">
                    !
                  </span>
                  <div className="absolute bottom-full left-0 mb-1 hidden group-hover:block w-48 bg-slate-700 text-slate-200 text-xs rounded p-2 shadow-xl border border-slate-600 z-10 whitespace-normal">
                    {parameterDescriptions[key]}
                  </div>
                </label>
                <input
                  type="number"
                  step="any"
                  name={key}
                  value={formData[key]}
                  onChange={handleChange}
                  className="bg-slate-900 border border-slate-600 rounded p-2 text-sm focus:outline-none focus:border-red-500 transition-colors"
                />
              </div>
            ))}
            <button
              type="submit"
              disabled={loading}
              className="col-span-2 mt-4 bg-red-600 hover:bg-red-700 text-white font-bold py-3 rounded transition-colors disabled:bg-slate-600"
            >
              {loading ? "ANALYZING..." : "RUN AI DIAGNOSTIC"}
            </button>
          </form>
        </div>

        <div className="lg:col-span-2 space-y-6">
          {!result && !loading && (
            <div className="h-full flex items-center justify-center border-2 border-dashed border-slate-700 rounded-lg p-12 text-slate-500">
              Awaiting telemetry data for risk analysis...
            </div>
          )}

          {result && (
            <>
              <div className={`p-6 rounded-lg border-2 ${result.evacuation_required ? 'bg-red-900/20 border-red-500' : 'bg-emerald-900/20 border-emerald-500'}`}>
                <h2 className="text-2xl font-bold mb-2">Threat Assessment</h2>
                <div className="text-6xl font-black mb-2">
                  {result.risk_probability_percentage}%
                </div>
                <div className={`text-lg font-bold tracking-widest uppercase ${result.evacuation_required ? 'text-red-400' : 'text-emerald-400'}`}>
                  {result.evacuation_required ? '🚨 CRITICAL RISK: EVACUATION AUTHORIZED' : '✅ RISK ACCEPTABLE: NO ACTION REQUIRED'}
                </div>
              </div>

              {result.evacuation_required && result.logistics && (
                <div className="bg-slate-800 p-6 rounded-lg shadow-lg border border-slate-700">
                  <h3 className="text-xl font-semibold mb-4 text-orange-400">Logistics Routing Engine</h3>
                  <div className="mb-4">
                    <span className="text-slate-400 text-sm">Estimated Response Time: </span>
                    <span className="text-2xl font-bold text-white">{result.logistics.estimated_time_mins} Minutes</span>
                  </div>

                  <div className="bg-slate-900 p-4 rounded border border-slate-700">
                    <div className="text-xs text-slate-500 mb-2 uppercase tracking-widest">Calculated Optimal Route</div>
                    <div className="flex flex-wrap items-center gap-2">
                      {result.logistics.optimal_route.map((node, index) => (
                        <div key={index} className="flex items-center">
                          <span className="bg-slate-700 px-3 py-1 rounded text-sm font-medium">{node}</span>
                          {index < result.logistics.optimal_route.length - 1 && (
                            <span className="mx-2 text-slate-500">➔</span>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}

export default App;
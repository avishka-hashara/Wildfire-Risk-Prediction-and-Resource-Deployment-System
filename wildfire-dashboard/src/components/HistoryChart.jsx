import React from 'react';
import {
    ResponsiveContainer,
    LineChart,
    Line,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
} from 'recharts';

const HistoryChart = ({ data }) => {
    // Helper to format ISO timestamp into a readable Day/Time string
    const formatXAxis = (tickItem) => {
        if (!tickItem) return "";
        const date = new Date(tickItem);
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        const hours = String(date.getHours()).padStart(2, '0');
        const mins = String(date.getMinutes()).padStart(2, '0');
        return `${month}/${day} ${hours}:${mins}`;
    };

    return (
        <div className="w-full h-64 bg-[#1e293b] rounded-lg p-4 border border-gray-700">
            <ResponsiveContainer width="100%" height="100%">
                <LineChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                    <CartesianGrid stroke="#334155" strokeDasharray="3 3" vertical={false} />
                    <XAxis 
                        dataKey="timestamp" 
                        tickFormatter={formatXAxis} 
                        stroke="#94a3b8" 
                        fontSize={12} 
                        tickMargin={10} 
                    />
                    <YAxis 
                        stroke="#94a3b8" 
                        fontSize={12} 
                        tickMargin={10} 
                    />
                    <Tooltip 
                        contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '0.5rem', color: '#f8fafc' }}
                        itemStyle={{ color: '#f8fafc' }}
                        labelFormatter={formatXAxis}
                    />
                    <Line 
                        type="monotone" 
                        dataKey="risk_probability" 
                        name="AI Threat Level" 
                        stroke="#ef4444" 
                        strokeWidth={2} 
                        dot={{ r: 3, fill: '#ef4444', strokeWidth: 0 }} 
                        activeDot={{ r: 5 }} 
                    />
                    <Line 
                        type="monotone" 
                        dataKey="fwi" 
                        name="Fire Weather Index" 
                        stroke="#f59e0b" 
                        strokeWidth={2} 
                        dot={{ r: 3, fill: '#f59e0b', strokeWidth: 0 }} 
                        activeDot={{ r: 5 }} 
                    />
                    <Line 
                        type="monotone" 
                        dataKey="dc" 
                        name="Drought Code" 
                        stroke="#3b82f6" 
                        strokeWidth={2} 
                        dot={{ r: 3, fill: '#3b82f6', strokeWidth: 0 }} 
                        activeDot={{ r: 5 }} 
                    />
                </LineChart>
            </ResponsiveContainer>
        </div>
    );
};

export default HistoryChart;

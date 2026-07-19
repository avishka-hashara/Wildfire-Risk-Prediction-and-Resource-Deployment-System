import React, { useState, useEffect } from 'react';
import { MapContainer, TileLayer, Marker, useMapEvents, useMap } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';

// Fix for default Leaflet marker icons in React
import icon from 'leaflet/dist/images/marker-icon.png';
import iconShadow from 'leaflet/dist/images/marker-shadow.png';

let DefaultIcon = L.icon({
    iconUrl: icon,
    shadowUrl: iconShadow,
    iconSize: [25, 41],
    iconAnchor: [12, 41]
});
L.Marker.prototype.options.icon = DefaultIcon;

// Component to handle map clicks
const LocationMarker = ({ position, setPosition }) => {
    useMapEvents({
        click(e) {
            setPosition([e.latlng.lat, e.latlng.lng]);
        },
    });

    return position === null ? null : (
        <Marker position={position}></Marker>
    );
};

// Component to programmatically fly map to a new position
const MapUpdater = ({ position }) => {
    const map = useMap();
    useEffect(() => {
        if (position) {
            map.flyTo(position, map.getZoom(), {
                animate: true,
                duration: 1.5
            });
        }
    }, [position, map]);
    return null;
};

const TacticalMap = ({ onLocationSelect }) => {
    // Defaulting to a dense forest region (Sinharaja Forest Reserve coordinates as a good baseline)
    const [position, setPosition] = useState([6.40, 80.45]);
    const [searchQuery, setSearchQuery] = useState("");
    const [isSearching, setIsSearching] = useState(false);

    // Ensure the parent component gets the default location on initial mount
    useEffect(() => {
        onLocationSelect({ lat: position[0], lng: position[1] });
    }, []);

    const handleLocationChange = (newPos) => {
        setPosition(newPos);
        onLocationSelect({ lat: newPos[0], lng: newPos[1] });
    };

    const handleSearch = async (e) => {
        e.preventDefault();
        if (!searchQuery.trim()) return;
        
        setIsSearching(true);
        try {
            const res = await fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(searchQuery)}`);
            const data = await res.json();
            if (data && data.length > 0) {
                const newPos = [parseFloat(data[0].lat), parseFloat(data[0].lon)];
                handleLocationChange(newPos);
            } else {
                alert("Location not found. Please try a different search term.");
            }
        } catch (error) {
            console.error("Search failed:", error);
            alert("Search failed. Please try again.");
        } finally {
            setIsSearching(false);
        }
    };

    return (
        <div className="w-full flex flex-col">
            {/* Location Search Bar */}
            <form onSubmit={handleSearch} className="flex gap-2 mb-3">
                <input 
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Search by city, region, or country..."
                    className="flex-1 bg-[#0f172a] border border-gray-700 rounded-lg px-4 py-2 text-sm text-gray-200 focus:outline-none focus:border-red-500 transition-colors"
                />
                <button 
                    type="submit" 
                    disabled={isSearching}
                    className="bg-red-600 hover:bg-red-700 disabled:bg-red-800 disabled:text-gray-400 text-white font-bold py-2 px-4 rounded-lg text-sm transition-colors"
                >
                    {isSearching ? 'SEARCHING...' : 'SEARCH'}
                </button>
            </form>

            <div className="w-full h-80 rounded-t-lg overflow-hidden border border-gray-700 shadow-lg relative z-0">
                <MapContainer
                    center={position}
                    zoom={9}
                    style={{ height: '100%', width: '100%' }}
                >
                    {/* Dark mode tactical map tiles to match the Command Center UI */}
                    <TileLayer
                        url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
                        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
                    />
                    <LocationMarker position={position} setPosition={handleLocationChange} />
                    <MapUpdater position={position} />
                </MapContainer>
            </div>

            <div className="p-3 bg-[#1e293b] text-sm text-gray-300 flex justify-between border border-t-0 border-gray-700 rounded-b-lg shadow-lg">
                <span><strong>Target Lat:</strong> {position[0].toFixed(4)}</span>
                <span><strong>Target Lng:</strong> {position[1].toFixed(4)}</span>
            </div>
        </div>
    );
};

export default TacticalMap;
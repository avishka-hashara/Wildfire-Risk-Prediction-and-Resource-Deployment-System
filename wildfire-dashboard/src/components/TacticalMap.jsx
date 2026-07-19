import React, { useState, useEffect } from 'react';
import { MapContainer, TileLayer, Marker, useMapEvents } from 'react-leaflet';
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

const TacticalMap = ({ onLocationSelect }) => {
    // Defaulting to a dense forest region (Sinharaja Forest Reserve coordinates as a good baseline)
    const [position, setPosition] = useState([6.40, 80.45]);

    // Ensure the parent component gets the default location on initial mount
    useEffect(() => {
        onLocationSelect({ lat: position[0], lng: position[1] });
    }, []);

    const handleLocationChange = (newPos) => {
        setPosition(newPos);
        onLocationSelect({ lat: newPos[0], lng: newPos[1] });
    };

    return (
        <div className="w-full flex flex-col">
            <div className="w-full h-80 rounded-t-lg overflow-hidden border border-gray-700 shadow-lg">
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
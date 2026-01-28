import React, { useEffect, useState } from 'react';
import { MapContainer, TileLayer, CircleMarker, Popup } from 'react-leaflet';
import { Globe, MapPin, RefreshCw } from 'lucide-react';
import { stats } from '../../services/api';
import 'leaflet/dist/leaflet.css';

const LiveMap = () => {
    const [mapData, setMapData] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    const fetchMapData = async () => {
        setLoading(true);
        setError(null);
        try {
            const data = await stats.getMapData();
            setMapData(data || []);
        } catch (err) {
            console.error('Failed to fetch map data:', err);
            setError('Failed to load map data');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchMapData();
        // Refresh every 60 seconds
        const interval = setInterval(fetchMapData, 60000);
        return () => clearInterval(interval);
    }, []);

    // Calculate bounds or use default world view
    const defaultCenter = [20, 0];
    const defaultZoom = 2;

    return (
        <div className="glass-card overflow-hidden">
            {/* Header */}
            <div className="flex items-center justify-between p-4 border-b border-white/10">
                <div className="flex items-center gap-3">
                    <div className="p-2 rounded-lg bg-gradient-to-br from-cyan-500/20 to-blue-500/20">
                        <Globe className="w-5 h-5 text-cyan-400" />
                    </div>
                    <div>
                        <h2 className="text-lg font-semibold text-white">Mission Control</h2>
                        <p className="text-xs text-slate-400">Live software activations worldwide</p>
                    </div>
                </div>
                <div className="flex items-center gap-3">
                    {mapData.length > 0 && (
                        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20">
                            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                            <span className="text-xs font-medium text-emerald-400">
                                {mapData.reduce((sum, loc) => sum + loc.count, 0)} Active
                            </span>
                        </div>
                    )}
                    <button
                        onClick={fetchMapData}
                        disabled={loading}
                        className="p-2 rounded-lg hover:bg-white/5 text-slate-400 hover:text-white transition-colors disabled:opacity-50"
                    >
                        <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
                    </button>
                </div>
            </div>

            {/* Map Container */}
            <div className="relative h-[350px] bg-gray-900/50">
                {error ? (
                    <div className="absolute inset-0 flex items-center justify-center">
                        <div className="text-center">
                            <MapPin className="w-12 h-12 text-slate-600 mx-auto mb-2" />
                            <p className="text-slate-400">{error}</p>
                            <button
                                onClick={fetchMapData}
                                className="mt-2 text-sm text-cyan-400 hover:text-cyan-300"
                            >
                                Try again
                            </button>
                        </div>
                    </div>
                ) : (
                    <MapContainer
                        center={defaultCenter}
                        zoom={defaultZoom}
                        style={{ height: '100%', width: '100%' }}
                        className="live-map"
                        scrollWheelZoom={false}
                        zoomControl={true}
                    >
                        {/* Dark themed map tiles - CartoDB Dark Matter */}
                        <TileLayer
                            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
                            url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
                        />

                        {/* Glowing markers for each location */}
                        {mapData.map((location, index) => (
                            <CircleMarker
                                key={`${location.lat}-${location.lng}-${index}`}
                                center={[location.lat, location.lng]}
                                radius={Math.min(8 + location.count * 2, 20)}
                                pathOptions={{
                                    color: '#06b6d4',
                                    fillColor: '#06b6d4',
                                    fillOpacity: 0.6,
                                    weight: 2,
                                    className: 'map-marker-glow'
                                }}
                            >
                                <Popup className="dark-popup">
                                    <div className="text-center">
                                        <p className="font-semibold text-sm">
                                            {location.city}, {location.country}
                                        </p>
                                        <p className="text-xs text-gray-500">
                                            {location.count} active {location.count === 1 ? 'device' : 'devices'}
                                        </p>
                                    </div>
                                </Popup>
                            </CircleMarker>
                        ))}
                    </MapContainer>
                )}

                {/* Overlay for loading state */}
                {loading && mapData.length === 0 && (
                    <div className="absolute inset-0 flex items-center justify-center bg-gray-900/80">
                        <div className="text-center">
                            <div className="w-8 h-8 border-2 border-cyan-500 border-t-transparent rounded-full animate-spin mx-auto mb-2" />
                            <p className="text-sm text-slate-400">Loading map data...</p>
                        </div>
                    </div>
                )}

                {/* Empty state */}
                {!loading && !error && mapData.length === 0 && (
                    <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                        <div className="text-center bg-gray-900/80 px-6 py-4 rounded-xl">
                            <Globe className="w-12 h-12 text-slate-600 mx-auto mb-2" />
                            <p className="text-slate-300 font-medium">No activity yet</p>
                            <p className="text-xs text-slate-500 mt-1">
                                Validations will appear here in real-time
                            </p>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
};

export default LiveMap;

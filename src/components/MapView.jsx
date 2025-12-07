import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import { Icon } from 'leaflet';
import { Button } from './ui/button';
import { Shield, MapPin } from 'lucide-react';

// Fix for default marker icon in React Leaflet
import markerIcon from 'leaflet/dist/images/marker-icon.png';
import markerIcon2x from 'leaflet/dist/images/marker-icon-2x.png';
import markerShadow from 'leaflet/dist/images/marker-shadow.png';

delete Icon.Default.prototype._getIconUrl;
Icon.Default.mergeOptions({
    iconUrl: markerIcon,
    iconRetinaUrl: markerIcon2x,
    shadowUrl: markerShadow,
});

const MapView = ({ officers, onOfficerClick }) => {
    // Default center (London)
    const defaultCenter = [51.5074, -0.1278];

    return (
        <div className="h-[calc(100vh-12rem)] w-full rounded-xl overflow-hidden shadow-lg border border-gray-200">
            <MapContainer
                center={defaultCenter}
                zoom={13}
                style={{ height: '100%', width: '100%' }}
            >
                <TileLayer
                    attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                    url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                />

                {officers.map((officer) => (
                    officer.latitude && officer.longitude ? (
                        <Marker
                            key={officer.id}
                            position={[officer.latitude, officer.longitude]}
                        >
                            <Popup>
                                <div className="min-w-[200px]">
                                    <div className="flex items-center gap-2 mb-2 font-bold">
                                        <Shield className="h-4 w-4 text-blue-600" />
                                        Officer #{officer.badgeNumber || 'Unknown'}
                                    </div>
                                    <div className="mb-2">
                                        <p className="text-sm text-gray-600">{officer.force}</p>
                                        <p className="text-sm text-gray-500 flex items-center gap-1">
                                            <MapPin className="h-3 w-3" />
                                            {officer.location}
                                        </p>
                                    </div>
                                    <Button
                                        size="sm"
                                        className="w-full h-8 text-xs"
                                        onClick={() => onOfficerClick(officer)}
                                    >
                                        View Profile
                                    </Button>
                                </div>
                            </Popup>
                        </Marker>
                    ) : null
                ))}
            </MapContainer>
        </div>
    );
};

export default MapView;

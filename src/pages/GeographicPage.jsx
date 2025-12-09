import { useState, useEffect, useCallback, useMemo, useRef, memo } from 'react';
import { Link } from 'react-router-dom';
import { MapContainer, TileLayer, Marker, Popup, Polyline, Circle, useMap } from 'react-leaflet';
import L from 'leaflet';
import {
  MapPin, Users, Calendar, RefreshCw, Eye, Shield, ChevronRight,
  Layers, Filter, Map as MapIcon, AlertTriangle, ExternalLink, ZoomIn
} from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { API_BASE, fetchWithErrorHandling } from '../utils/api';
import { withErrorBoundary } from '../components/ErrorBoundary';
import { MOVEMENT_COLORS, getMovementColor } from '../utils/constants';
import 'leaflet/dist/leaflet.css';

// Import marker icons from local leaflet package (no CDN dependency)
import markerIcon2x from 'leaflet/dist/images/marker-icon-2x.png';
import markerIcon from 'leaflet/dist/images/marker-icon.png';
import markerShadow from 'leaflet/dist/images/marker-shadow.png';

// Fix for default marker icons in React-Leaflet
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: markerIcon2x,
  iconUrl: markerIcon,
  shadowUrl: markerShadow,
});

// Cluster size thresholds
const CLUSTER_THRESHOLDS = {
  SMALL: 5,
  MEDIUM: 15,
  LARGE: 30
};

// Cluster sizes (pixels)
const CLUSTER_SIZES = {
  SMALL: 30,
  MEDIUM: 40,
  LARGE: 50,
  XLARGE: 60
};

// Custom marker icons based on officer count
const createClusterIcon = (count) => {
  // Validate and sanitize count - must be a non-negative integer
  const safeCount = typeof count === 'number' && Number.isFinite(count) && count >= 0
    ? Math.floor(count)
    : 0;

  const size = safeCount < CLUSTER_THRESHOLDS.SMALL ? CLUSTER_SIZES.SMALL :
               safeCount < CLUSTER_THRESHOLDS.MEDIUM ? CLUSTER_SIZES.MEDIUM :
               safeCount < CLUSTER_THRESHOLDS.LARGE ? CLUSTER_SIZES.LARGE :
               CLUSTER_SIZES.XLARGE;

  const color = safeCount < CLUSTER_THRESHOLDS.SMALL ? '#22c55e' :
                safeCount < CLUSTER_THRESHOLDS.MEDIUM ? '#eab308' :
                safeCount < CLUSTER_THRESHOLDS.LARGE ? '#f97316' :
                '#ef4444';

  // Create icon element safely without innerHTML XSS risk
  const div = document.createElement('div');
  div.style.cssText = `
    width: ${size}px;
    height: ${size}px;
    background: ${color};
    border: 3px solid white;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    font-weight: bold;
    font-size: ${size / 2.5}px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.3);
  `;
  div.textContent = String(safeCount);

  return L.divIcon({
    className: 'custom-cluster-marker',
    html: div.outerHTML,
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
    popupAnchor: [0, -size / 2]
  });
};

// Component to fit map bounds
const FitBounds = ({ protests }) => {
  const map = useMap();

  useEffect(() => {
    if (protests && protests.length > 0) {
      const bounds = protests
        .filter(p => p.latitude && p.longitude)
        .map(p => [p.latitude, p.longitude]);

      if (bounds.length > 0) {
        map.fitBounds(bounds, { padding: [50, 50], maxZoom: 12 });
      }
    }
  }, [protests, map]);

  return null;
};

// Stats Card
const StatsCard = ({ icon: Icon, label, value, color = 'green' }) => {
  const colors = {
    green: 'bg-green-50 text-green-600 border-green-200',
    blue: 'bg-blue-50 text-blue-600 border-blue-200',
    orange: 'bg-orange-50 text-orange-600 border-orange-200',
    red: 'bg-red-50 text-red-600 border-red-200'
  };

  return (
    <div className={`p-4 rounded-lg border ${colors[color]}`}>
      <div className="flex items-center gap-2 mb-1">
        <Icon className="h-4 w-4" />
        <span className="text-xs font-medium uppercase tracking-wider">{label}</span>
      </div>
      <div className="text-2xl font-bold">{value}</div>
    </div>
  );
};

// Officer Movement Panel - memoized to prevent re-renders on map interaction
const MovementPanel = memo(function MovementPanel({ movements, selectedOfficer, onSelectOfficer }) {
  if (!movements || movements.length === 0) {
    return (
      <Card className="p-4">
        <h3 className="font-semibold text-gray-900 mb-2 flex items-center gap-2">
          <Users className="h-5 w-5 text-purple-600" />
          Multi-Location Officers
        </h3>
        <p className="text-sm text-gray-500 italic">
          No officers found at multiple protest locations
        </p>
      </Card>
    );
  }

  return (
    <Card className="p-4">
      <h3 className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
        <Users className="h-5 w-5 text-purple-600" />
        Multi-Location Officers ({movements.length})
      </h3>
      <div className="space-y-2 max-h-64 overflow-y-auto">
        {movements.map((officer, idx) => (
          <button
            key={officer.officer_id}
            onClick={() => onSelectOfficer(
              selectedOfficer === officer.officer_id ? null : officer.officer_id
            )}
            className={`w-full text-left p-3 rounded-lg border transition-all ${
              selectedOfficer === officer.officer_id
                ? 'border-purple-500 bg-purple-50'
                : 'border-gray-200 hover:border-purple-300 bg-white'
            }`}
          >
            <div className="flex items-center gap-3">
              <div
                className="w-4 h-4 rounded-full flex-shrink-0"
                style={{ backgroundColor: getMovementColor(idx) }}
              />
              <div className="flex-1 min-w-0">
                <div className="font-medium text-gray-900 truncate">
                  {officer.badge_number || `Officer #${officer.officer_id}`}
                </div>
                <div className="text-xs text-gray-500">
                  {officer.protest_count} locations | {officer.force || 'Unknown Force'}
                </div>
              </div>
              <Link
                to={`/officer/${officer.officer_id}`}
                onClick={(e) => e.stopPropagation()}
                className="text-purple-600 hover:text-purple-800"
              >
                <ExternalLink className="h-4 w-4" />
              </Link>
            </div>
          </button>
        ))}
      </div>
    </Card>
  );
};

// Protest List Panel
const ProtestPanel = ({ protests, selectedProtest, onSelectProtest }) => {
  const sortedProtests = useMemo(() => {
    return [...protests].sort((a, b) => b.officer_count - a.officer_count);
  }, [protests]);

  return (
    <Card className="p-4">
      <h3 className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
        <MapPin className="h-5 w-5 text-green-600" />
        Protest Locations ({protests.length})
      </h3>
      <div className="space-y-2 max-h-64 overflow-y-auto">
        {sortedProtests.map((protest) => (
          <button
            key={protest.id}
            onClick={() => onSelectProtest(
              selectedProtest === protest.id ? null : protest.id
            )}
            className={`w-full text-left p-3 rounded-lg border transition-all ${
              selectedProtest === protest.id
                ? 'border-green-500 bg-green-50'
                : 'border-gray-200 hover:border-green-300 bg-white'
            }`}
          >
            <div className="flex items-start justify-between">
              <div className="flex-1 min-w-0">
                <div className="font-medium text-gray-900 truncate">{protest.name}</div>
                <div className="text-xs text-gray-500 truncate">{protest.location}</div>
                {protest.date && (
                  <div className="text-xs text-gray-400 mt-1">
                    {new Date(protest.date).toLocaleDateString()}
                  </div>
                )}
              </div>
              <div className="flex flex-col items-end gap-1 ml-2">
                <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                  protest.officer_count >= 20 ? 'bg-red-100 text-red-800' :
                  protest.officer_count >= 10 ? 'bg-orange-100 text-orange-800' :
                  protest.officer_count >= 5 ? 'bg-yellow-100 text-yellow-800' :
                  'bg-green-100 text-green-800'
                }`}>
                  {protest.officer_count} officers
                </span>
                <span className="text-xs text-gray-400">
                  {protest.media_count} media
                </span>
              </div>
            </div>
          </button>
        ))}
      </div>
    </Card>
  );
};

// Main Geographic Page
function GeographicPage() {
  const [geoData, setGeoData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedProtest, setSelectedProtest] = useState(null);
  const [selectedOfficer, setSelectedOfficer] = useState(null);
  const [showMovements, setShowMovements] = useState(true);
  const [showMarkers, setShowMarkers] = useState(true);

  const fetchGeoData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchWithErrorHandling(`${API_BASE}/stats/geographic`);
      setGeoData(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchGeoData();
  }, [fetchGeoData]);

  // Filter movements based on selected officer
  const visibleMovements = useMemo(() => {
    if (!geoData?.officer_movements) return [];
    if (selectedOfficer) {
      return geoData.officer_movements.filter(m => m.officer_id === selectedOfficer);
    }
    return geoData.officer_movements;
  }, [geoData, selectedOfficer]);

  // UK center coordinates
  const defaultCenter = [51.5074, -0.1278];
  const defaultZoom = 6;

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <RefreshCw className="h-12 w-12 animate-spin text-green-600 mx-auto mb-4" />
          <p className="text-gray-600">Loading geographic data...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <AlertTriangle className="h-12 w-12 text-red-500 mx-auto mb-4" />
          <h2 className="text-xl font-bold text-gray-900 mb-2">Error Loading Data</h2>
          <p className="text-red-500 mb-4">{error}</p>
          <Button onClick={fetchGeoData}>Try Again</Button>
        </div>
      </div>
    );
  }

  const protests = geoData?.protests || [];
  const hasGeoData = protests.some(p => p.latitude && p.longitude);

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b-2 border-green-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center justify-between flex-wrap gap-4">
            <div>
              <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
                <MapIcon className="h-7 w-7 text-green-600" />
                Geographic Analysis
              </h1>
              <p className="text-gray-600 mt-1">
                Map officer presence and movement patterns across protest locations
              </p>
            </div>
            <div className="flex items-center gap-3">
              <Button
                variant={showMovements ? "default" : "outline"}
                size="sm"
                onClick={() => setShowMovements(!showMovements)}
              >
                <Layers className="h-4 w-4 mr-2" />
                Movements
              </Button>
              <Button
                variant={showMarkers ? "default" : "outline"}
                size="sm"
                onClick={() => setShowMarkers(!showMarkers)}
              >
                <MapPin className="h-4 w-4 mr-2" />
                Markers
              </Button>
              <Button variant="outline" size="sm" onClick={fetchGeoData}>
                <RefreshCw className="h-4 w-4 mr-2" />
                Refresh
              </Button>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {/* Stats Row */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <StatsCard
            icon={MapPin}
            label="Locations"
            value={geoData?.total_protests_with_coords || 0}
            color="green"
          />
          <StatsCard
            icon={Users}
            label="Multi-Location Officers"
            value={geoData?.total_multi_location_officers || 0}
            color="purple"
          />
          <StatsCard
            icon={Eye}
            label="Total Officers"
            value={protests.reduce((sum, p) => sum + p.officer_count, 0)}
            color="blue"
          />
          <StatsCard
            icon={Calendar}
            label="Events Tracked"
            value={protests.length}
            color="orange"
          />
        </div>

        {!hasGeoData ? (
          <Card className="p-12 text-center">
            <MapPin className="h-16 w-16 text-gray-300 mx-auto mb-4" />
            <h2 className="text-xl font-bold text-gray-900 mb-2">No Geographic Data</h2>
            <p className="text-gray-600 mb-4">
              No protest locations have coordinates set. Add latitude and longitude to protests to enable geographic analysis.
            </p>
            <Link to="/admin">
              <Button>Go to Admin</Button>
            </Link>
          </Card>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
            {/* Map Container */}
            <div className="lg:col-span-3">
              <Card className="overflow-hidden">
                <div
                  className="h-[600px]"
                  role="application"
                  aria-label="Interactive map showing protest locations and officer movements across the UK"
                >
                  <MapContainer
                    center={defaultCenter}
                    zoom={defaultZoom}
                    style={{ height: '100%', width: '100%' }}
                    keyboard={true}
                    scrollWheelZoom={true}
                  >
                    <TileLayer
                      attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
                      url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                    />

                    <FitBounds protests={protests.filter(p => p.latitude && p.longitude)} />

                    {/* Protest Markers */}
                    {showMarkers && protests.filter(p => p.latitude && p.longitude).map((protest) => (
                      <Marker
                        key={protest.id}
                        position={[protest.latitude, protest.longitude]}
                        icon={createClusterIcon(protest.officer_count)}
                        eventHandlers={{
                          click: () => setSelectedProtest(
                            selectedProtest === protest.id ? null : protest.id
                          )
                        }}
                      >
                        <Popup>
                          <div className="min-w-[200px]">
                            <h3 className="font-bold text-gray-900">{protest.name}</h3>
                            <p className="text-sm text-gray-600">{protest.location}</p>
                            {protest.date && (
                              <p className="text-xs text-gray-400 mt-1">
                                {new Date(protest.date).toLocaleDateString()}
                              </p>
                            )}
                            <div className="mt-3 pt-2 border-t border-gray-200">
                              <div className="flex justify-between text-sm">
                                <span>Officers:</span>
                                <span className="font-medium">{protest.officer_count}</span>
                              </div>
                              <div className="flex justify-between text-sm">
                                <span>Media:</span>
                                <span className="font-medium">{protest.media_count}</span>
                              </div>
                            </div>
                            {protest.forces && protest.forces.length > 0 && (
                              <div className="mt-2 pt-2 border-t border-gray-200">
                                <p className="text-xs font-medium text-gray-600 mb-1">Forces:</p>
                                <div className="flex flex-wrap gap-1">
                                  {protest.forces.slice(0, 3).map((f, i) => (
                                    <span
                                      key={i}
                                      className="text-xs bg-blue-100 text-blue-800 px-1.5 py-0.5 rounded"
                                    >
                                      {f.force.split(' ').slice(0, 2).join(' ')} ({f.count})
                                    </span>
                                  ))}
                                </div>
                              </div>
                            )}
                          </div>
                        </Popup>
                      </Marker>
                    ))}

                    {/* Highlight circle for selected protest */}
                    {selectedProtest && (() => {
                      const protest = protests.find(p => p.id === selectedProtest);
                      if (protest?.latitude && protest?.longitude) {
                        return (
                          <Circle
                            center={[protest.latitude, protest.longitude]}
                            radius={5000}
                            pathOptions={{
                              color: '#22c55e',
                              fillColor: '#22c55e',
                              fillOpacity: 0.1
                            }}
                          />
                        );
                      }
                      return null;
                    })()}

                    {/* Officer Movement Lines */}
                    {showMovements && visibleMovements.map((movement, idx) => {
                      const positions = movement.locations
                        .filter(loc => loc.latitude && loc.longitude)
                        .map(loc => [loc.latitude, loc.longitude]);

                      if (positions.length < 2) return null;

                      return (
                        <Polyline
                          key={movement.officer_id}
                          positions={positions}
                          pathOptions={{
                            color: getMovementColor(idx),
                            weight: selectedOfficer === movement.officer_id ? 4 : 2,
                            opacity: selectedOfficer === movement.officer_id ? 1 : 0.6,
                            dashArray: '10, 5'
                          }}
                        >
                          <Popup>
                            <div className="min-w-[180px]">
                              <h3 className="font-bold text-gray-900">
                                {movement.badge_number || `Officer #${movement.officer_id}`}
                              </h3>
                              <p className="text-sm text-gray-600">{movement.force || 'Unknown Force'}</p>
                              <p className="text-sm mt-2">
                                <strong>{movement.protest_count}</strong> locations visited
                              </p>
                              <Link
                                to={`/officer/${movement.officer_id}`}
                                className="mt-2 inline-flex items-center text-sm text-green-600 hover:text-green-800"
                              >
                                View Profile <ChevronRight className="h-4 w-4" />
                              </Link>
                            </div>
                          </Popup>
                        </Polyline>
                      );
                    })}
                  </MapContainer>
                </div>
              </Card>

              {/* Legend - accessible with both color and text */}
              <div
                className="mt-4 flex flex-wrap items-center gap-6 text-sm text-gray-600"
                role="region"
                aria-label="Map legend"
              >
                <div className="flex items-center gap-2">
                  <span className="text-xs font-medium uppercase text-gray-500">Officer Count:</span>
                  <div className="flex items-center gap-3" role="list">
                    <span className="flex items-center gap-1" role="listitem">
                      <div className="w-3 h-3 rounded-full bg-green-500" aria-hidden="true" />
                      <span>1-4 <span className="sr-only">officers (green, low)</span></span>
                    </span>
                    <span className="flex items-center gap-1" role="listitem">
                      <div className="w-3 h-3 rounded-full bg-yellow-500" aria-hidden="true" />
                      <span>5-14 <span className="sr-only">officers (yellow, medium)</span></span>
                    </span>
                    <span className="flex items-center gap-1" role="listitem">
                      <div className="w-3 h-3 rounded-full bg-orange-500" aria-hidden="true" />
                      <span>15-29 <span className="sr-only">officers (orange, high)</span></span>
                    </span>
                    <span className="flex items-center gap-1" role="listitem">
                      <div className="w-3 h-3 rounded-full bg-red-500" aria-hidden="true" />
                      <span>30+ <span className="sr-only">officers (red, very high)</span></span>
                    </span>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-medium uppercase text-gray-500">Lines:</span>
                  <span>Officer movement between locations</span>
                </div>
              </div>
            </div>

            {/* Side Panels */}
            <div className="space-y-6">
              <ProtestPanel
                protests={protests}
                selectedProtest={selectedProtest}
                onSelectProtest={setSelectedProtest}
              />
              <MovementPanel
                movements={geoData?.officer_movements || []}
                selectedOfficer={selectedOfficer}
                onSelectOfficer={setSelectedOfficer}
              />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default withErrorBoundary(GeographicPage, 'An error occurred while loading the Geographic Analysis page. Please try again.');

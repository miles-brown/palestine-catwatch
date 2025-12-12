import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Calendar,
  MapPin,
  Users,
  Camera,
  Shield,
  Loader2,
  Search,
  Filter,
  ChevronDown,
  X,
  AlertCircle,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import ProtestCard from '@/components/ProtestCard';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// Event type filter options
const EVENT_TYPES = [
  { value: 'march', label: 'March' },
  { value: 'rally', label: 'Rally' },
  { value: 'vigil', label: 'Vigil' },
  { value: 'encampment', label: 'Encampment' },
  { value: 'demonstration', label: 'Demonstration' },
];

// Sort options
const SORT_OPTIONS = [
  { value: 'date', label: 'Most Recent' },
  { value: 'attendance', label: 'Largest Attendance' },
  { value: 'name', label: 'Name (A-Z)' },
  { value: 'city', label: 'City (A-Z)' },
];

/**
 * Format date for display.
 * @param {string} dateString - ISO date string
 * @returns {string} Formatted date
 */
const formatDate = (dateString) => {
  if (!dateString) return 'Date unknown';
  try {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-GB', {
      weekday: 'long',
      day: 'numeric',
      month: 'long',
      year: 'numeric',
    });
  } catch {
    return 'Date unknown';
  }
};

/**
 * Protest Detail Modal component.
 */
const ProtestDetailModal = ({ protest, onClose }) => {
  const [details, setDetails] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    const fetchDetails = async () => {
      try {
        const res = await fetch(`${API_BASE}/protests/${protest.id}`);
        if (!res.ok) throw new Error('Failed to fetch protest details');
        const data = await res.json();
        setDetails(data);
      } catch (e) {
        setError(e.message);
      } finally {
        setLoading(false);
      }
    };
    fetchDetails();
  }, [protest.id]);

  const handleViewOfficer = (officerId) => {
    onClose();
    navigate(`/officer/${officerId}`);
  };

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-xl max-w-4xl w-full max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="bg-slate-900 text-white p-6 relative">
          {protest.cover_image_url && (
            <div className="absolute inset-0 opacity-30">
              <img
                src={protest.cover_image_url}
                alt=""
                className="w-full h-full object-cover"
              />
            </div>
          )}
          <div className="relative z-10">
            <div className="flex items-start justify-between">
              <div>
                <h2 className="font-bold text-2xl mb-2">{protest.name}</h2>
                <div className="flex items-center gap-4 text-slate-300 text-sm">
                  <span className="flex items-center gap-1">
                    <Calendar className="h-4 w-4" />
                    {formatDate(protest.date)}
                  </span>
                  <span className="flex items-center gap-1">
                    <MapPin className="h-4 w-4" />
                    {protest.city || protest.location}
                  </span>
                </div>
              </div>
              <button
                onClick={onClose}
                className="p-2 hover:bg-white/20 rounded-lg transition-colors"
                aria-label="Close modal"
              >
                <X className="h-5 w-5" />
              </button>
            </div>
          </div>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto max-h-[60vh]">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-slate-400" />
            </div>
          ) : error ? (
            <div className="text-center py-12">
              <AlertCircle className="h-12 w-12 text-red-400 mx-auto mb-4" />
              <p className="text-red-600">Error loading details: {error}</p>
            </div>
          ) : details ? (
            <div className="space-y-6">
              {/* Stats Grid */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="bg-slate-50 rounded-lg p-4">
                  <div className="flex items-center gap-2 text-slate-600 mb-1">
                    <Users className="h-4 w-4" />
                    <span className="text-sm">Attendance</span>
                  </div>
                  <div className="text-2xl font-bold text-slate-900">
                    {details.estimated_attendance?.toLocaleString() || 'Unknown'}
                  </div>
                </div>
                <div className="bg-slate-50 rounded-lg p-4">
                  <div className="flex items-center gap-2 text-slate-600 mb-1">
                    <Camera className="h-4 w-4" />
                    <span className="text-sm">Media Files</span>
                  </div>
                  <div className="text-2xl font-bold text-slate-900">
                    {details.media_count || 0}
                  </div>
                </div>
                <div className="bg-slate-50 rounded-lg p-4">
                  <div className="flex items-center gap-2 text-slate-600 mb-1">
                    <Shield className="h-4 w-4" />
                    <span className="text-sm">Officers Documented</span>
                  </div>
                  <div className="text-2xl font-bold text-slate-900">
                    {details.officer_count || 0}
                  </div>
                </div>
                <div className="bg-slate-50 rounded-lg p-4">
                  <div className="flex items-center gap-2 text-slate-600 mb-1">
                    <Shield className="h-4 w-4" />
                    <span className="text-sm">Police Force</span>
                  </div>
                  <div className="text-lg font-bold text-slate-900 truncate">
                    {details.police_force || 'Unknown'}
                  </div>
                </div>
              </div>

              {/* Description */}
              {details.description && (
                <div>
                  <h3 className="font-semibold text-slate-900 mb-2">Description</h3>
                  <p className="text-slate-600">{details.description}</p>
                </div>
              )}

              {/* Event Details */}
              <div className="grid grid-cols-2 gap-4">
                {details.organizer && (
                  <div>
                    <h4 className="text-sm font-medium text-slate-500 mb-1">Organizer</h4>
                    <p className="text-slate-900">{details.organizer}</p>
                  </div>
                )}
                {details.event_type && (
                  <div>
                    <h4 className="text-sm font-medium text-slate-500 mb-1">Event Type</h4>
                    <p className="text-slate-900 capitalize">{details.event_type}</p>
                  </div>
                )}
                {details.location && (
                  <div>
                    <h4 className="text-sm font-medium text-slate-500 mb-1">Location</h4>
                    <p className="text-slate-900">{details.location}</p>
                  </div>
                )}
                {details.status && (
                  <div>
                    <h4 className="text-sm font-medium text-slate-500 mb-1">Status</h4>
                    <span className={`inline-flex px-2 py-1 rounded text-sm font-medium ${
                      details.status === 'verified'
                        ? 'bg-green-100 text-green-700'
                        : 'bg-slate-100 text-slate-700'
                    }`}>
                      {details.status}
                    </span>
                  </div>
                )}
              </div>

              {/* Officers Section */}
              {details.officers && details.officers.length > 0 && (
                <div>
                  <h3 className="font-semibold text-slate-900 mb-3">
                    Documented Officers ({details.officers.length})
                  </h3>
                  <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                    {details.officers.slice(0, 9).map((officer) => (
                      <button
                        key={officer.id}
                        onClick={() => handleViewOfficer(officer.id)}
                        className="flex items-center gap-2 p-2 bg-slate-50 rounded hover:bg-slate-100 transition-colors text-left"
                      >
                        <Shield className="h-4 w-4 text-slate-400" />
                        <div className="truncate">
                          <div className="font-mono text-sm font-medium text-slate-900">
                            {officer.badge_number || 'Unknown'}
                          </div>
                          <div className="text-xs text-slate-500 truncate">
                            {officer.force || 'Unknown Force'}
                          </div>
                        </div>
                      </button>
                    ))}
                    {details.officers.length > 9 && (
                      <div className="flex items-center justify-center p-2 bg-slate-50 rounded text-slate-500 text-sm">
                        +{details.officers.length - 9} more
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Media Section */}
              {details.media && details.media.length > 0 && (
                <div>
                  <h3 className="font-semibold text-slate-900 mb-3">
                    Evidence ({details.media.length} files)
                  </h3>
                  <div className="grid grid-cols-4 gap-2">
                    {details.media.slice(0, 8).map((media) => (
                      <div
                        key={media.id}
                        className="aspect-square bg-slate-100 rounded overflow-hidden"
                      >
                        {media.type === 'image' ? (
                          <img
                            src={media.url}
                            alt="Evidence"
                            className="w-full h-full object-cover"
                          />
                        ) : (
                          <div className="w-full h-full flex items-center justify-center text-slate-400">
                            <Camera className="h-6 w-6" />
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : null}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 bg-slate-50 border-t border-slate-200">
          <Button onClick={onClose} variant="outline" className="w-full">
            Close
          </Button>
        </div>
      </div>
    </div>
  );
};

const ProtestDatabasePage = () => {
  const [protests, setProtests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedProtest, setSelectedProtest] = useState(null);

  // Filter state
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCity, setSelectedCity] = useState('');
  const [selectedEventType, setSelectedEventType] = useState('');
  const [sortBy, setSortBy] = useState('date');
  const [showFilters, setShowFilters] = useState(false);

  // Available filter options from API
  const [cities, setCities] = useState([]);
  const [eventTypes, setEventTypes] = useState([]);
  const [totalCount, setTotalCount] = useState(0);

  const fetchProtests = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const params = new URLSearchParams();
      if (selectedCity) params.append('city', selectedCity);
      if (selectedEventType) params.append('event_type', selectedEventType);
      params.append('sort_by', sortBy);
      params.append('sort_order', sortBy === 'name' || sortBy === 'city' ? 'asc' : 'desc');

      const url = `${API_BASE}/protests?${params.toString()}`;
      const res = await fetch(url);

      if (!res.ok) throw new Error('Failed to fetch protests');

      const data = await res.json();
      setProtests(data.protests || []);
      setTotalCount(data.total || 0);
      setCities(data.cities || []);
      setEventTypes(data.event_types || []);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [selectedCity, selectedEventType, sortBy]);

  useEffect(() => {
    fetchProtests();
  }, [fetchProtests]);

  // Filter protests by search query (client-side)
  const filteredProtests = protests.filter((protest) => {
    if (!searchQuery) return true;
    const query = searchQuery.toLowerCase();
    return (
      protest.name?.toLowerCase().includes(query) ||
      protest.location?.toLowerCase().includes(query) ||
      protest.city?.toLowerCase().includes(query) ||
      protest.organizer?.toLowerCase().includes(query)
    );
  });

  // Calculate totals for stats
  const totalOfficers = protests.reduce((sum, p) => sum + (p.officer_count || 0), 0);
  const totalMedia = protests.reduce((sum, p) => sum + (p.media_count || 0), 0);

  const clearFilters = () => {
    setSelectedCity('');
    setSelectedEventType('');
    setSortBy('date');
    setSearchQuery('');
  };

  const hasActiveFilters = selectedCity || selectedEventType || searchQuery;

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-slate-900 mb-2">Protest Database</h1>
        <p className="text-slate-600">
          Documented protests and public assemblies with police accountability records.
          Click on any protest to view full details including documented officers and evidence.
        </p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <div className="bg-white rounded-lg border border-slate-200 p-4">
          <div className="text-2xl font-bold text-slate-900">{totalCount}</div>
          <div className="text-sm text-slate-500">Total Protests</div>
        </div>
        <div className="bg-white rounded-lg border border-slate-200 p-4">
          <div className="text-2xl font-bold text-slate-900">{cities.length}</div>
          <div className="text-sm text-slate-500">Cities</div>
        </div>
        <div className="bg-white rounded-lg border border-slate-200 p-4">
          <div className="text-2xl font-bold text-green-600">{totalOfficers}</div>
          <div className="text-sm text-slate-500">Officers Documented</div>
        </div>
        <div className="bg-white rounded-lg border border-slate-200 p-4">
          <div className="text-2xl font-bold text-blue-600">{totalMedia}</div>
          <div className="text-sm text-slate-500">Evidence Files</div>
        </div>
      </div>

      {/* Search and Filters */}
      <div className="mb-6 space-y-4">
        {/* Search Bar */}
        <div className="flex gap-3">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-slate-400" />
            <input
              type="text"
              placeholder="Search protests by name, location, or organizer..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2.5 border border-slate-300 rounded-lg focus:ring-2 focus:ring-slate-900 focus:border-slate-900 outline-none transition-colors"
            />
          </div>
          <Button
            variant="outline"
            onClick={() => setShowFilters(!showFilters)}
            className="flex items-center gap-2"
          >
            <Filter className="h-4 w-4" />
            Filters
            {hasActiveFilters && (
              <span className="bg-slate-900 text-white text-xs px-1.5 py-0.5 rounded-full">
                {[selectedCity, selectedEventType].filter(Boolean).length}
              </span>
            )}
            <ChevronDown className={`h-4 w-4 transition-transform ${showFilters ? 'rotate-180' : ''}`} />
          </Button>
        </div>

        {/* Filter Panel */}
        {showFilters && (
          <div className="bg-slate-50 border border-slate-200 rounded-lg p-4">
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              {/* City Filter */}
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">City</label>
                <select
                  value={selectedCity}
                  onChange={(e) => setSelectedCity(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-slate-900 focus:border-slate-900 outline-none"
                >
                  <option value="">All Cities</option>
                  {cities.map((city) => (
                    <option key={city} value={city}>{city}</option>
                  ))}
                </select>
              </div>

              {/* Event Type Filter */}
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Event Type</label>
                <select
                  value={selectedEventType}
                  onChange={(e) => setSelectedEventType(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-slate-900 focus:border-slate-900 outline-none"
                >
                  <option value="">All Types</option>
                  {EVENT_TYPES.map((type) => (
                    <option key={type.value} value={type.value}>{type.label}</option>
                  ))}
                </select>
              </div>

              {/* Sort By */}
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Sort By</label>
                <select
                  value={sortBy}
                  onChange={(e) => setSortBy(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-slate-900 focus:border-slate-900 outline-none"
                >
                  {SORT_OPTIONS.map((option) => (
                    <option key={option.value} value={option.value}>{option.label}</option>
                  ))}
                </select>
              </div>

              {/* Clear Filters */}
              <div className="flex items-end">
                <Button
                  variant="ghost"
                  onClick={clearFilters}
                  className="w-full"
                  disabled={!hasActiveFilters}
                >
                  <X className="h-4 w-4 mr-2" />
                  Clear Filters
                </Button>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Results Count */}
      {!loading && (
        <div className="mb-4 text-sm text-slate-600">
          Showing {filteredProtests.length} of {totalCount} protests
          {hasActiveFilters && ' (filtered)'}
        </div>
      )}

      {/* Loading State */}
      {loading ? (
        <div className="flex items-center justify-center py-16">
          <Loader2 className="h-8 w-8 animate-spin text-slate-400" />
        </div>
      ) : error ? (
        <div className="text-center py-16">
          <AlertCircle className="h-12 w-12 text-red-400 mx-auto mb-4" />
          <p className="text-red-600 mb-4">Error loading protests: {error}</p>
          <Button onClick={fetchProtests}>Try Again</Button>
        </div>
      ) : filteredProtests.length === 0 ? (
        <div className="text-center py-16">
          <Shield className="h-12 w-12 text-slate-300 mx-auto mb-4" />
          <p className="text-slate-500 mb-2">No protests found</p>
          {hasActiveFilters && (
            <Button variant="outline" onClick={clearFilters}>
              Clear Filters
            </Button>
          )}
        </div>
      ) : (
        /* Protest Grid */
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredProtests.map((protest) => (
            <ProtestCard
              key={protest.id}
              protest={protest}
              onClick={setSelectedProtest}
            />
          ))}
        </div>
      )}

      {/* Detail Modal */}
      {selectedProtest && (
        <ProtestDetailModal
          protest={selectedProtest}
          onClose={() => setSelectedProtest(null)}
        />
      )}
    </div>
  );
};

export default ProtestDatabasePage;

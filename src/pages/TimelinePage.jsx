import { useState, useEffect, useMemo } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import {
  Clock, Calendar, MapPin, User, Shield, AlertTriangle,
  ChevronDown, ChevronRight, Play, Image, Video,
  Filter, X, Users, Camera, TrendingUp
} from 'lucide-react';

let API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000';
if (!API_BASE.startsWith('http')) {
  API_BASE = `https://${API_BASE}`;
}

// Escalation indicators
const ESCALATION_EQUIPMENT = ['Shield', 'Long Shield', 'Baton', 'Taser', 'Ballistic Helmet'];

export default function TimelinePage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [protests, setProtests] = useState([]);
  const [selectedProtest, setSelectedProtest] = useState(null);
  const [timelineData, setTimelineData] = useState(null);
  const [globalTimeline, setGlobalTimeline] = useState(null);
  const [loading, setLoading] = useState(true);
  const [viewMode, setViewMode] = useState('global'); // 'global' or 'protest'

  // Filters
  const [showFilters, setShowFilters] = useState(false);
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [forceFilter, setForceFilter] = useState('');
  const [showEscalationOnly, setShowEscalationOnly] = useState(false);

  // Expanded time buckets
  const [expandedBuckets, setExpandedBuckets] = useState(new Set());

  // Fetch protests list
  useEffect(() => {
    const fetchProtests = async () => {
      try {
        const res = await fetch(`${API_BASE}/protests`);
        const data = await res.json();
        setProtests(data);
      } catch (err) {
        console.error('Failed to fetch protests:', err);
      }
    };
    fetchProtests();
  }, []);

  // Fetch global timeline
  useEffect(() => {
    if (viewMode !== 'global') return;

    const fetchGlobalTimeline = async () => {
      setLoading(true);
      try {
        const params = new URLSearchParams();
        if (dateFrom) params.append('start_date', dateFrom);
        if (dateTo) params.append('end_date', dateTo);
        params.append('limit', '200');

        const res = await fetch(`${API_BASE}/timeline?${params}`);
        const data = await res.json();
        setGlobalTimeline(data);
      } catch (err) {
        console.error('Failed to fetch global timeline:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchGlobalTimeline();
  }, [viewMode, dateFrom, dateTo]);

  // Fetch protest timeline when protest selected
  useEffect(() => {
    if (!selectedProtest || viewMode !== 'protest') return;

    const fetchProtestTimeline = async () => {
      setLoading(true);
      try {
        const res = await fetch(`${API_BASE}/protests/${selectedProtest.id}/timeline`);
        const data = await res.json();
        setTimelineData(data);
      } catch (err) {
        console.error('Failed to fetch protest timeline:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchProtestTimeline();
  }, [selectedProtest, viewMode]);

  // Group events by date for global view
  const groupedByDate = useMemo(() => {
    if (!globalTimeline?.events) return {};

    const groups = {};
    globalTimeline.events
      .filter(e => {
        if (forceFilter && e.officer?.force !== forceFilter) return false;
        if (showEscalationOnly && !e.high_escalation_equipment) return false;
        return true;
      })
      .forEach(event => {
        const date = event.timestamp?.split('T')[0] || 'Unknown Date';
        if (!groups[date]) groups[date] = [];
        groups[date].push(event);
      });

    return groups;
  }, [globalTimeline, forceFilter, showEscalationOnly]);

  // Available forces for filter
  const availableForces = useMemo(() => {
    const forces = new Set();
    if (globalTimeline?.events) {
      globalTimeline.events.forEach(e => {
        if (e.officer?.force) forces.add(e.officer.force);
      });
    }
    return Array.from(forces).sort();
  }, [globalTimeline]);

  const toggleBucket = (bucket) => {
    setExpandedBuckets(prev => {
      const next = new Set(prev);
      if (next.has(bucket)) {
        next.delete(bucket);
      } else {
        next.add(bucket);
      }
      return next;
    });
  };

  const formatTime = (timestamp) => {
    if (!timestamp) return 'Unknown time';
    try {
      const date = new Date(timestamp);
      return date.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' });
    } catch {
      return timestamp;
    }
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return 'Unknown date';
    try {
      const date = new Date(dateStr);
      return date.toLocaleDateString('en-GB', {
        weekday: 'long',
        day: 'numeric',
        month: 'long',
        year: 'numeric'
      });
    } catch {
      return dateStr;
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">Event Timeline</h1>
          <p className="text-gray-600">
            Chronological reconstruction of documented events across protests
          </p>
        </div>

        {/* View Mode Toggle & Filters */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4 mb-6">
          <div className="flex flex-wrap gap-4 items-center justify-between">
            {/* View Mode */}
            <div className="flex bg-gray-100 p-1 rounded-md">
              <button
                onClick={() => setViewMode('global')}
                className={`px-4 py-2 rounded text-sm font-medium ${
                  viewMode === 'global'
                    ? 'bg-white shadow-sm text-gray-900'
                    : 'text-gray-500 hover:text-gray-900'
                }`}
              >
                <Clock className="h-4 w-4 inline mr-2" />
                All Events
              </button>
              <button
                onClick={() => setViewMode('protest')}
                className={`px-4 py-2 rounded text-sm font-medium ${
                  viewMode === 'protest'
                    ? 'bg-white shadow-sm text-gray-900'
                    : 'text-gray-500 hover:text-gray-900'
                }`}
              >
                <MapPin className="h-4 w-4 inline mr-2" />
                By Protest
              </button>
            </div>

            {/* Filter Toggle */}
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowFilters(!showFilters)}
              className={showFilters ? 'bg-green-50 border-green-300' : ''}
            >
              <Filter className="h-4 w-4 mr-2" />
              Filters
              {(dateFrom || dateTo || forceFilter || showEscalationOnly) && (
                <span className="ml-2 px-1.5 py-0.5 text-xs bg-green-100 text-green-800 rounded-full">
                  Active
                </span>
              )}
            </Button>
          </div>

          {/* Filter Panel */}
          {showFilters && (
            <div className="mt-4 pt-4 border-t border-gray-200 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">From Date</label>
                <input
                  type="date"
                  value={dateFrom}
                  onChange={(e) => setDateFrom(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">To Date</label>
                <input
                  type="date"
                  value={dateTo}
                  onChange={(e) => setDateTo(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Force</label>
                <select
                  value={forceFilter}
                  onChange={(e) => setForceFilter(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md"
                >
                  <option value="">All Forces</option>
                  {availableForces.map(force => (
                    <option key={force} value={force}>{force}</option>
                  ))}
                </select>
              </div>
              <div className="flex items-end">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={showEscalationOnly}
                    onChange={(e) => setShowEscalationOnly(e.target.checked)}
                    className="w-4 h-4 text-red-600 rounded"
                  />
                  <span className="text-sm text-gray-700">Escalation only</span>
                  <AlertTriangle className="h-4 w-4 text-red-500" />
                </label>
              </div>
            </div>
          )}
        </div>

        {/* Protest Selector (when in protest view) */}
        {viewMode === 'protest' && (
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4 mb-6">
            <label className="block text-sm font-medium text-gray-700 mb-2">Select Protest</label>
            <select
              value={selectedProtest?.id || ''}
              onChange={(e) => {
                const protest = protests.find(p => p.id === parseInt(e.target.value));
                setSelectedProtest(protest);
              }}
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
            >
              <option value="">Choose a protest...</option>
              {protests.map(protest => (
                <option key={protest.id} value={protest.id}>
                  {protest.name} - {formatDate(protest.date)} @ {protest.location}
                </option>
              ))}
            </select>
          </div>
        )}

        {/* Stats Summary */}
        {viewMode === 'global' && globalTimeline && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <Card className="p-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-blue-100 rounded-full">
                  <Camera className="h-5 w-5 text-blue-600" />
                </div>
                <div>
                  <p className="text-2xl font-bold">{globalTimeline.total_events}</p>
                  <p className="text-sm text-gray-500">Total Events</p>
                </div>
              </div>
            </Card>
            <Card className="p-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-green-100 rounded-full">
                  <Users className="h-5 w-5 text-green-600" />
                </div>
                <div>
                  <p className="text-2xl font-bold">{globalTimeline.unique_officers}</p>
                  <p className="text-sm text-gray-500">Officers</p>
                </div>
              </div>
            </Card>
            <Card className="p-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-purple-100 rounded-full">
                  <MapPin className="h-5 w-5 text-purple-600" />
                </div>
                <div>
                  <p className="text-2xl font-bold">{globalTimeline.unique_protests}</p>
                  <p className="text-sm text-gray-500">Protests</p>
                </div>
              </div>
            </Card>
            <Card className="p-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-orange-100 rounded-full">
                  <TrendingUp className="h-5 w-5 text-orange-600" />
                </div>
                <div>
                  <p className="text-2xl font-bold">
                    {globalTimeline.date_range?.earliest?.split('T')[0] || '-'}
                  </p>
                  <p className="text-sm text-gray-500">Earliest Event</p>
                </div>
              </div>
            </Card>
          </div>
        )}

        {/* Protest Summary */}
        {viewMode === 'protest' && timelineData && (
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-6">
            <h2 className="text-xl font-bold mb-4">{timelineData.protest.name}</h2>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div>
                <p className="text-sm text-gray-500">Date</p>
                <p className="font-medium">{formatDate(timelineData.protest.date)}</p>
              </div>
              <div>
                <p className="text-sm text-gray-500">Location</p>
                <p className="font-medium">{timelineData.protest.location}</p>
              </div>
              <div>
                <p className="text-sm text-gray-500">Officers Documented</p>
                <p className="font-bold text-green-700">{timelineData.total_officers}</p>
              </div>
              <div>
                <p className="text-sm text-gray-500">Total Events</p>
                <p className="font-bold text-blue-700">{timelineData.total_events}</p>
              </div>
            </div>
          </div>
        )}

        {/* Loading */}
        {loading && (
          <div className="flex justify-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-green-600"></div>
          </div>
        )}

        {/* Global Timeline View */}
        {viewMode === 'global' && !loading && globalTimeline && (
          <div className="space-y-6">
            {Object.entries(groupedByDate).map(([date, events]) => (
              <div key={date} className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
                {/* Date Header */}
                <button
                  onClick={() => toggleBucket(date)}
                  className="w-full px-6 py-4 flex items-center justify-between bg-gray-50 hover:bg-gray-100 transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <Calendar className="h-5 w-5 text-gray-500" />
                    <span className="font-semibold text-gray-900">{formatDate(date)}</span>
                    <span className="text-sm text-gray-500">({events.length} events)</span>
                  </div>
                  {expandedBuckets.has(date) ? (
                    <ChevronDown className="h-5 w-5 text-gray-400" />
                  ) : (
                    <ChevronRight className="h-5 w-5 text-gray-400" />
                  )}
                </button>

                {/* Events */}
                {expandedBuckets.has(date) && (
                  <div className="divide-y divide-gray-100">
                    {events.map((event, idx) => (
                      <TimelineEvent key={event.id} event={event} index={idx} />
                    ))}
                  </div>
                )}
              </div>
            ))}

            {Object.keys(groupedByDate).length === 0 && (
              <div className="text-center py-12 text-gray-500">
                No events found matching your criteria.
              </div>
            )}
          </div>
        )}

        {/* Protest Timeline View */}
        {viewMode === 'protest' && !loading && timelineData && (
          <div className="space-y-4">
            {/* Time buckets */}
            {Object.entries(timelineData.time_buckets || {}).map(([bucket, events]) => (
              <div key={bucket} className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
                {/* Bucket Header */}
                <button
                  onClick={() => toggleBucket(bucket)}
                  className="w-full px-6 py-4 flex items-center justify-between bg-gray-50 hover:bg-gray-100 transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <Clock className="h-5 w-5 text-gray-500" />
                    <span className="font-semibold text-gray-900">{formatTime(bucket)}</span>
                    <span className="text-sm text-gray-500">({events.length} events)</span>
                    {events.some(e => e.equipment?.some(eq => ESCALATION_EQUIPMENT.includes(eq.name))) && (
                      <span className="px-2 py-0.5 text-xs bg-red-100 text-red-700 rounded-full flex items-center gap-1">
                        <AlertTriangle className="h-3 w-3" />
                        Escalation
                      </span>
                    )}
                  </div>
                  {expandedBuckets.has(bucket) ? (
                    <ChevronDown className="h-5 w-5 text-gray-400" />
                  ) : (
                    <ChevronRight className="h-5 w-5 text-gray-400" />
                  )}
                </button>

                {/* Events in bucket */}
                {expandedBuckets.has(bucket) && (
                  <div className="divide-y divide-gray-100">
                    {events.map((event, idx) => (
                      <TimelineEvent key={event.id} event={event} index={idx} detailed />
                    ))}
                  </div>
                )}
              </div>
            ))}

            {/* All events list if no time buckets */}
            {(!timelineData.time_buckets || Object.keys(timelineData.time_buckets).length === 0) && (
              <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
                <div className="px-6 py-4 bg-gray-50">
                  <span className="font-semibold text-gray-900">All Events</span>
                </div>
                <div className="divide-y divide-gray-100">
                  {timelineData.events.map((event, idx) => (
                    <TimelineEvent key={event.id} event={event} index={idx} detailed />
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* No protest selected */}
        {viewMode === 'protest' && !selectedProtest && !loading && (
          <div className="text-center py-12 text-gray-500">
            Select a protest above to view its timeline.
          </div>
        )}
      </div>
    </div>
  );
}

// Individual Timeline Event Component
function TimelineEvent({ event, index, detailed = false }) {
  const hasEscalation = event.high_escalation_equipment ||
    event.equipment?.some(eq => ['Shield', 'Long Shield', 'Baton', 'Taser', 'Ballistic Helmet'].includes(eq.name));

  let API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000';
  if (!API_BASE.startsWith('http')) {
    API_BASE = `https://${API_BASE}`;
  }

  return (
    <div className={`px-6 py-4 hover:bg-gray-50 ${hasEscalation ? 'border-l-4 border-red-500' : ''}`}>
      <div className="flex gap-4">
        {/* Timeline Indicator */}
        <div className="flex flex-col items-center">
          <div className={`w-3 h-3 rounded-full ${hasEscalation ? 'bg-red-500' : 'bg-green-500'}`} />
          <div className="w-0.5 flex-1 bg-gray-200" />
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-start gap-4">
            {/* Officer Image */}
            {event.crop_url && (
              <img
                src={event.crop_url.startsWith('http') ? event.crop_url : `${API_BASE}${event.crop_url}`}
                alt="Officer"
                className="w-16 h-16 rounded-lg object-cover border border-gray-200"
              />
            )}

            {/* Details */}
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-1">
                <Link
                  to={`/officer/${event.officer?.id}`}
                  className="font-medium text-gray-900 hover:text-green-700"
                >
                  {event.officer?.badge_number || `Officer #${event.officer?.id}`}
                </Link>
                {event.officer?.rank && (
                  <span className="text-xs px-2 py-0.5 bg-gray-100 text-gray-600 rounded">
                    {event.officer.rank}
                  </span>
                )}
                {event.officer?.force && (
                  <span className="text-xs text-gray-500">{event.officer.force}</span>
                )}
              </div>

              {/* Action */}
              {event.action && (
                <p className="text-sm text-gray-700 mb-2">{event.action}</p>
              )}

              {/* Role */}
              {event.role && (
                <span className="text-xs px-2 py-0.5 bg-blue-100 text-blue-700 rounded mr-2">
                  {event.role}
                </span>
              )}

              {/* Timestamp & Media */}
              <div className="flex items-center gap-3 text-xs text-gray-500 mt-2">
                {event.timestamp && (
                  <span className="flex items-center gap-1">
                    <Clock className="h-3 w-3" />
                    {new Date(event.timestamp).toLocaleTimeString('en-GB')}
                  </span>
                )}
                {event.video_timestamp && (
                  <span className="flex items-center gap-1">
                    <Play className="h-3 w-3" />
                    {event.video_timestamp}
                  </span>
                )}
                {event.media_type && (
                  <span className="flex items-center gap-1">
                    {event.media_type === 'video' ? <Video className="h-3 w-3" /> : <Image className="h-3 w-3" />}
                    {event.media_type}
                  </span>
                )}
                {event.protest && (
                  <span className="flex items-center gap-1">
                    <MapPin className="h-3 w-3" />
                    {event.protest.name || event.protest.location}
                  </span>
                )}
              </div>

              {/* Detailed Equipment List */}
              {detailed && event.equipment && event.equipment.length > 0 && (
                <div className="mt-3 flex flex-wrap gap-1">
                  {event.equipment.map((eq, i) => (
                    <span
                      key={i}
                      className={`text-xs px-2 py-0.5 rounded ${
                        ['Shield', 'Long Shield', 'Baton', 'Taser', 'Ballistic Helmet'].includes(eq.name)
                          ? 'bg-red-100 text-red-700'
                          : 'bg-gray-100 text-gray-600'
                      }`}
                    >
                      {eq.name}
                    </span>
                  ))}
                </div>
              )}

              {/* Uniform Info */}
              {detailed && event.uniform && (
                <div className="mt-2 text-xs text-gray-500">
                  {event.uniform.force && <span className="mr-2">Force: {event.uniform.force}</span>}
                  {event.uniform.unit_type && <span className="mr-2">Unit: {event.uniform.unit_type}</span>}
                  {event.uniform.shoulder_number && <span>SN: {event.uniform.shoulder_number}</span>}
                </div>
              )}

              {/* Equipment Count Badge */}
              {!detailed && event.equipment_count > 0 && (
                <span className={`mt-2 inline-flex items-center text-xs px-2 py-0.5 rounded ${
                  hasEscalation ? 'bg-red-100 text-red-700' : 'bg-gray-100 text-gray-600'
                }`}>
                  <Shield className="h-3 w-3 mr-1" />
                  {event.equipment_count} equipment
                  {hasEscalation && (
                    <>
                      <AlertTriangle className="h-3 w-3 ml-1" />
                    </>
                  )}
                </span>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

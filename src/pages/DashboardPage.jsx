import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  Users, Eye, FileVideo, Calendar, TrendingUp,
  RefreshCw, AlertTriangle, Network, ChevronRight,
  Download, FileJson, FileSpreadsheet
} from 'lucide-react';
import { Card } from '@/components/ui/card';
import { API_BASE, getMediaUrl, fetchWithErrorHandling } from '../utils/api';

const StatCard = ({ icon: Icon, label, value, subtext, color = "green" }) => {
  const colorClasses = {
    green: "border-green-200 text-green-700",
    red: "border-red-200 text-red-700",
    blue: "border-blue-200 text-blue-700",
    orange: "border-orange-200 text-orange-700",
    gray: "border-gray-200 text-gray-700"
  };

  return (
    <Card className={`p-6 border-2 ${colorClasses[color]}`}>
      <div className="flex items-center gap-3 mb-2">
        <Icon className="h-6 w-6" />
        <span className="text-sm font-medium text-gray-600">{label}</span>
      </div>
      <div className="text-3xl font-bold mb-1">{value}</div>
      {subtext && <div className="text-xs text-gray-500">{subtext}</div>}
    </Card>
  );
};

const OfficerRow = ({ officer, onViewNetwork }) => {
  const cropUrl = getMediaUrl(officer.crop_path);

  return (
    <tr className="border-b border-gray-100 hover:bg-gray-50 transition-colors">
      <td className="py-3 px-4">
        <div className="flex items-center gap-3">
          {cropUrl ? (
            <img
              src={cropUrl}
              alt="Officer"
              className="w-12 h-12 rounded-full object-cover border-2 border-gray-200"
            />
          ) : (
            <div className="w-12 h-12 rounded-full bg-gray-200 flex items-center justify-center">
              <Users className="h-6 w-6 text-gray-400" />
            </div>
          )}
          <div>
            <div className="font-medium text-gray-900">
              {officer.badge_number || `Officer #${officer.id}`}
            </div>
            <div className="text-sm text-gray-500">{officer.force || 'Unknown Force'}</div>
          </div>
        </div>
      </td>
      <td className="py-3 px-4 text-center">
        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
          {officer.total_appearances} sightings
        </span>
      </td>
      <td className="py-3 px-4 text-center">
        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-orange-100 text-orange-800">
          {officer.distinct_events} events
        </span>
      </td>
      <td className="py-3 px-4 text-right">
        <button
          onClick={() => onViewNetwork(officer.id)}
          className="text-sm text-blue-600 hover:text-blue-800 font-medium flex items-center gap-1 ml-auto"
        >
          <Network className="h-4 w-4" />
          Network
        </button>
      </td>
    </tr>
  );
};

const NetworkModal = ({ officerId, onClose }) => {
  const [network, setNetwork] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchNetwork = async () => {
      try {
        const response = await fetch(`${API_BASE}/officers/${officerId}/network`);
        const data = await response.json();
        setNetwork(data);
      } catch (error) {
        console.error("Failed to fetch network:", error);
      } finally {
        setLoading(false);
      }
    };
    fetchNetwork();
  }, [officerId]);

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[80vh] overflow-hidden">
        <div className="p-6 border-b border-gray-200">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold text-gray-900">
              Officer Network Analysis
            </h3>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600"
            >
              &times;
            </button>
          </div>
          <p className="text-sm text-gray-500 mt-1">
            Officers frequently seen together in the same media
          </p>
        </div>

        <div className="p-6 overflow-y-auto max-h-[60vh]">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <RefreshCw className="h-8 w-8 animate-spin text-gray-400" />
            </div>
          ) : network?.connections?.length > 0 ? (
            <div className="space-y-3">
              {network.connections.map((conn) => {
                const cropUrl = getMediaUrl(conn.crop_path);

                return (
                  <div
                    key={conn.id}
                    className="flex items-center gap-4 p-3 bg-gray-50 rounded-lg"
                  >
                    {cropUrl ? (
                      <img
                        src={cropUrl}
                        alt="Connected Officer"
                        className="w-10 h-10 rounded-full object-cover border border-gray-200"
                      />
                    ) : (
                      <div className="w-10 h-10 rounded-full bg-gray-200 flex items-center justify-center">
                        <Users className="h-5 w-5 text-gray-400" />
                      </div>
                    )}
                    <div className="flex-1">
                      <div className="font-medium text-gray-900">
                        {conn.badge_number || `Officer #${conn.id}`}
                      </div>
                      <div className="text-sm text-gray-500">{conn.force || 'Unknown Force'}</div>
                    </div>
                    <div className="text-right">
                      <span className="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-blue-100 text-blue-800">
                        {conn.shared_appearances} shared appearances
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="text-center py-12 text-gray-500">
              <Network className="h-12 w-12 mx-auto mb-3 opacity-50" />
              <p>No network connections found for this officer.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

const DashboardPage = () => {
  const [stats, setStats] = useState(null);
  const [officers, setOfficers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [networkOfficerId, setNetworkOfficerId] = useState(null);
  const [minAppearances, setMinAppearances] = useState(1);
  const [minEvents, setMinEvents] = useState(1);

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      try {
        const [statsRes, officersRes] = await Promise.all([
          fetch(`${API_BASE}/stats/overview`),
          fetch(`${API_BASE}/officers/repeat?min_appearances=${minAppearances}&min_events=${minEvents}`)
        ]);

        const statsData = await statsRes.json();
        const officersData = await officersRes.json();

        setStats(statsData);
        setOfficers(officersData.officers || []);
      } catch (error) {
        console.error("Failed to fetch dashboard data:", error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [minAppearances, minEvents]);

  const handleRefresh = () => {
    setLoading(true);
    // Re-trigger effect by changing a dependency
    setMinAppearances(prev => prev);
    window.location.reload();
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b-2 border-green-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">
                Re-identification Dashboard
              </h1>
              <p className="text-gray-600 mt-2">
                Track officers across multiple events and identify patterns
              </p>
            </div>
            <div className="flex items-center gap-3">
              <div className="relative group">
                <button className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">
                  <Download className="h-4 w-4" />
                  Export
                </button>
                <div className="absolute right-0 mt-2 w-48 bg-white rounded-lg shadow-lg border border-gray-200 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all z-10">
                  <a
                    href={`${API_BASE}/export/officers/csv`}
                    className="flex items-center gap-2 px-4 py-3 hover:bg-gray-50 rounded-t-lg"
                  >
                    <FileSpreadsheet className="h-4 w-4 text-green-600" />
                    Export as CSV
                  </a>
                  <a
                    href={`${API_BASE}/export/officers/json`}
                    className="flex items-center gap-2 px-4 py-3 hover:bg-gray-50 rounded-b-lg border-t"
                  >
                    <FileJson className="h-4 w-4 text-blue-600" />
                    Export as JSON
                  </a>
                </div>
              </div>
              <button
                onClick={handleRefresh}
                className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
              >
                <RefreshCw className="h-4 w-4" />
                Refresh
              </button>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {loading ? (
          <div className="flex items-center justify-center py-24">
            <RefreshCw className="h-12 w-12 animate-spin text-green-600" />
          </div>
        ) : (
          <>
            {/* Stats Grid */}
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 mb-8">
              <StatCard
                icon={Users}
                label="Total Officers"
                value={stats?.total_officers || 0}
                subtext="Documented individuals"
                color="green"
              />
              <StatCard
                icon={Eye}
                label="Total Appearances"
                value={stats?.total_appearances || 0}
                subtext="Across all media"
                color="blue"
              />
              <StatCard
                icon={FileVideo}
                label="Media Processed"
                value={stats?.total_media || 0}
                subtext="Images & videos"
                color="gray"
              />
              <StatCard
                icon={Calendar}
                label="Events Covered"
                value={stats?.total_protests || 0}
                subtext="Documented protests"
                color="orange"
              />
              <StatCard
                icon={TrendingUp}
                label="Repeat Officers"
                value={stats?.repeat_officers || 0}
                subtext="2+ appearances"
                color="red"
              />
              <StatCard
                icon={AlertTriangle}
                label="Multi-Event"
                value={stats?.multi_event_officers || 0}
                subtext="Across 2+ events"
                color="red"
              />
            </div>

            {/* Officers Section */}
            <div className="bg-white rounded-lg shadow-sm border border-gray-200">
              <div className="p-6 border-b border-gray-200">
                <div className="flex items-center justify-between flex-wrap gap-4">
                  <div>
                    <h2 className="text-xl font-semibold text-gray-900">
                      Officers Database
                    </h2>
                    <p className="text-sm text-gray-500 mt-1">
                      All documented officers across events
                    </p>
                  </div>

                  {/* Filters */}
                  <div className="flex items-center gap-4">
                    <div className="flex items-center gap-2">
                      <label className="text-sm text-gray-600">Min Appearances:</label>
                      <select
                        value={minAppearances}
                        onChange={(e) => setMinAppearances(Number(e.target.value))}
                        className="border border-gray-300 rounded px-2 py-1 text-sm"
                      >
                        <option value={1}>All</option>
                        <option value={2}>2+</option>
                        <option value={3}>3+</option>
                        <option value={5}>5+</option>
                        <option value={10}>10+</option>
                      </select>
                    </div>
                    <div className="flex items-center gap-2">
                      <label className="text-sm text-gray-600">Min Events:</label>
                      <select
                        value={minEvents}
                        onChange={(e) => setMinEvents(Number(e.target.value))}
                        className="border border-gray-300 rounded px-2 py-1 text-sm"
                      >
                        <option value={1}>1+</option>
                        <option value={2}>2+</option>
                        <option value={3}>3+</option>
                        <option value={5}>5+</option>
                      </select>
                    </div>
                  </div>
                </div>
              </div>

              {officers.length > 0 ? (
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="py-3 px-4 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Officer
                        </th>
                        <th className="py-3 px-4 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Appearances
                        </th>
                        <th className="py-3 px-4 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Events
                        </th>
                        <th className="py-3 px-4 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Actions
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {officers.map((officer) => (
                        <OfficerRow
                          key={officer.id}
                          officer={officer}
                          onViewNetwork={setNetworkOfficerId}
                        />
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="p-12 text-center text-gray-500">
                  <Users className="h-12 w-12 mx-auto mb-3 opacity-50" />
                  <p className="text-lg font-medium">No officers found</p>
                  <p className="text-sm mt-1">
                    {minAppearances > 1 || minEvents > 1
                      ? "Adjust filters or process more media to find matches"
                      : "Process media to start documenting officers"
                    }
                  </p>
                </div>
              )}
            </div>

            {/* Recent Activity */}
            {stats?.recent_media?.length > 0 && (
              <div className="mt-8 bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                <h2 className="text-xl font-semibold text-gray-900 mb-4">
                  Recently Processed Media
                </h2>
                <div className="space-y-3">
                  {stats.recent_media.map((media) => (
                    <Link
                      key={media.id}
                      to={`/report/${media.id}`}
                      className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
                    >
                      <FileVideo className="h-5 w-5 text-gray-400" />
                      <div className="flex-1">
                        <div className="text-sm font-medium text-gray-900">
                          {media.type === 'video' ? 'Video' : 'Image'} #{media.id}
                        </div>
                        <div className="text-xs text-gray-500">
                          {media.timestamp ? new Date(media.timestamp).toLocaleString() : 'Unknown date'}
                        </div>
                      </div>
                      <ChevronRight className="h-5 w-5 text-gray-400" />
                    </Link>
                  ))}
                </div>
              </div>
            )}
          </>
        )}
      </div>

      {/* Network Modal */}
      {networkOfficerId && (
        <NetworkModal
          officerId={networkOfficerId}
          onClose={() => setNetworkOfficerId(null)}
        />
      )}
    </div>
  );
};

export default DashboardPage;

import { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import {
  Shield, AlertTriangle, RefreshCw, TrendingUp, Link2, Calendar,
  ChevronRight, AlertCircle, CheckCircle, Info, Siren
} from 'lucide-react';
import { Skeleton } from '@/components/ui/skeleton';

let API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";
if (!API_BASE.startsWith("http")) {
  API_BASE = `https://${API_BASE}`;
}

// Category colors
const CATEGORY_COLORS = {
  defensive: { bg: 'bg-blue-100', text: 'text-blue-800', border: 'border-blue-300' },
  offensive: { bg: 'bg-red-100', text: 'text-red-800', border: 'border-red-300' },
  restraint: { bg: 'bg-orange-100', text: 'text-orange-800', border: 'border-orange-300' },
  identification: { bg: 'bg-green-100', text: 'text-green-800', border: 'border-green-300' },
  communication: { bg: 'bg-purple-100', text: 'text-purple-800', border: 'border-purple-300' },
  specialist: { bg: 'bg-gray-100', text: 'text-gray-800', border: 'border-gray-300' }
};

// Escalation score color
const getEscalationColor = (score) => {
  if (score >= 12) return { bg: 'bg-red-600', text: 'text-white', label: 'Critical' };
  if (score >= 8) return { bg: 'bg-red-500', text: 'text-white', label: 'High' };
  if (score >= 5) return { bg: 'bg-orange-500', text: 'text-white', label: 'Elevated' };
  if (score >= 3) return { bg: 'bg-yellow-500', text: 'text-black', label: 'Moderate' };
  return { bg: 'bg-green-500', text: 'text-white', label: 'Low' };
};

// Stats Card
const StatCard = ({ icon: Icon, label, value, subtext, color = 'blue' }) => {
  const colors = {
    blue: 'border-blue-200 text-blue-700',
    red: 'border-red-200 text-red-700',
    orange: 'border-orange-200 text-orange-700',
    green: 'border-green-200 text-green-700'
  };

  return (
    <Card className={`p-4 border-2 ${colors[color]}`}>
      <div className="flex items-center gap-2 mb-2">
        <Icon className="h-5 w-5" />
        <span className="text-sm font-medium text-gray-600">{label}</span>
      </div>
      <div className="text-2xl font-bold">{value}</div>
      {subtext && <div className="text-xs text-gray-500 mt-1">{subtext}</div>}
    </Card>
  );
};

// Co-occurrence visualization
const CoOccurrenceCard = ({ item1, item2, count }) => {
  return (
    <div className="flex items-center justify-between p-3 bg-white border rounded-lg">
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2">
          <span className="bg-gray-100 px-2 py-1 rounded text-sm font-medium">{item1}</span>
          <Link2 className="h-4 w-4 text-gray-400" />
          <span className="bg-gray-100 px-2 py-1 rounded text-sm font-medium">{item2}</span>
        </div>
      </div>
      <div className="text-sm font-bold text-gray-700">
        {count}x
      </div>
    </div>
  );
};

// Escalation Event Card
const EscalationEventCard = ({ event }) => {
  const escalationStyle = getEscalationColor(event.escalation_score);

  return (
    <Card className="overflow-hidden">
      {/* Header with escalation score */}
      <div className={`${escalationStyle.bg} ${escalationStyle.text} p-4`}>
        <div className="flex items-center justify-between">
          <div>
            <h3 className="font-bold text-lg">{event.protest_name}</h3>
            {event.date && (
              <p className="text-sm opacity-90 flex items-center gap-1 mt-1">
                <Calendar className="h-4 w-4" />
                {new Date(event.date).toLocaleDateString()}
              </p>
            )}
          </div>
          <div className="text-right">
            <div className="text-3xl font-black">{event.escalation_score}</div>
            <div className="text-xs uppercase tracking-wider opacity-90">
              {escalationStyle.label} Risk
            </div>
          </div>
        </div>
      </div>

      {/* Equipment breakdown */}
      <div className="p-4 space-y-4">
        {/* High risk equipment */}
        {event.high_risk_equipment.length > 0 && (
          <div>
            <div className="flex items-center gap-2 mb-2">
              <AlertTriangle className="h-4 w-4 text-red-500" />
              <span className="text-xs font-semibold text-red-700 uppercase">High Risk Equipment</span>
            </div>
            <div className="flex flex-wrap gap-2">
              {event.high_risk_equipment.map((eq, i) => (
                <span key={i} className="bg-red-100 text-red-800 text-xs px-2 py-1 rounded font-medium">
                  {eq}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Medium risk equipment */}
        {event.medium_risk_equipment.length > 0 && (
          <div>
            <div className="flex items-center gap-2 mb-2">
              <AlertCircle className="h-4 w-4 text-orange-500" />
              <span className="text-xs font-semibold text-orange-700 uppercase">Medium Risk Equipment</span>
            </div>
            <div className="flex flex-wrap gap-2">
              {event.medium_risk_equipment.map((eq, i) => (
                <span key={i} className="bg-orange-100 text-orange-800 text-xs px-2 py-1 rounded font-medium">
                  {eq}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Stats footer */}
        <div className="pt-3 border-t flex items-center justify-between text-sm text-gray-500">
          <span>{event.total_equipment_types} equipment types detected</span>
          <span>{event.media_count} media file{event.media_count !== 1 ? 's' : ''}</span>
        </div>

        {/* View details link */}
        <Link
          to={`/report/${event.protest_id}`}
          className="flex items-center justify-center gap-2 w-full py-2 bg-gray-100 rounded text-sm font-medium text-gray-700 hover:bg-gray-200 transition"
        >
          View Protest Details
          <ChevronRight className="h-4 w-4" />
        </Link>
      </div>
    </Card>
  );
};

// Category Distribution Bar
const CategoryDistribution = ({ distribution }) => {
  if (!distribution || Object.keys(distribution).length === 0) return null;

  const total = Object.values(distribution).reduce((a, b) => a + b, 0);
  const sortedCategories = Object.entries(distribution).sort((a, b) => b[1] - a[1]);

  return (
    <Card className="p-4">
      <h3 className="font-semibold text-gray-900 mb-4">Equipment by Category</h3>
      <div className="space-y-3">
        {sortedCategories.map(([category, count]) => {
          const percent = ((count / total) * 100).toFixed(1);
          const style = CATEGORY_COLORS[category] || CATEGORY_COLORS.specialist;

          return (
            <div key={category}>
              <div className="flex items-center justify-between text-sm mb-1">
                <span className={`capitalize ${style.text} font-medium`}>{category}</span>
                <span className="text-gray-500">{count} ({percent}%)</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                  className={`${style.bg} h-2 rounded-full transition-all`}
                  style={{ width: `${percent}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </Card>
  );
};

// Main Page
export default function EquipmentCorrelationPage() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE}/stats/equipment-correlation`);
      if (!response.ok) throw new Error('Failed to fetch correlation data');
      const result = await response.json();
      setData(result);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50">
        <div className="bg-white border-b-2 border-red-700">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
            <Skeleton className="h-8 w-64 mb-2" />
            <Skeleton className="h-4 w-96" />
          </div>
        </div>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-24" />
            ))}
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <Skeleton className="h-96" />
            <Skeleton className="h-96 lg:col-span-2" />
          </div>
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
          <Button onClick={fetchData}>Try Again</Button>
        </div>
      </div>
    );
  }

  const hasData = data && data.total_detections > 0;

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b-2 border-red-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center justify-between flex-wrap gap-4">
            <div>
              <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
                <Siren className="h-7 w-7 text-red-600" />
                Equipment Correlation Analysis
              </h1>
              <p className="text-gray-600 mt-1">
                Identify equipment patterns that indicate escalation potential
              </p>
            </div>
            <Button variant="outline" onClick={fetchData}>
              <RefreshCw className="h-4 w-4 mr-2" />
              Refresh
            </Button>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {!hasData ? (
          <Card className="p-12 text-center">
            <Shield className="h-16 w-16 text-gray-300 mx-auto mb-4" />
            <h2 className="text-xl font-bold text-gray-900 mb-2">No Equipment Data</h2>
            <p className="text-gray-600 mb-4">
              No equipment detections have been recorded yet. Analyze officer uniforms to detect equipment.
            </p>
            <Link to="/admin">
              <Button>Go to Admin Panel</Button>
            </Link>
          </Card>
        ) : (
          <>
            {/* Stats Row */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
              <StatCard
                icon={Shield}
                label="Total Detections"
                value={data.total_detections}
                subtext="Equipment items identified"
                color="blue"
              />
              <StatCard
                icon={Link2}
                label="Co-occurrences"
                value={data.co_occurrences?.length || 0}
                subtext="Equipment pairs found"
                color="green"
              />
              <StatCard
                icon={TrendingUp}
                label="High-Risk Events"
                value={data.escalation_events?.filter(e => e.escalation_score >= 8).length || 0}
                subtext="Elevated escalation"
                color="red"
              />
              <StatCard
                icon={AlertTriangle}
                label="Equipment Types"
                value={data.equipment_counts?.length || 0}
                subtext="Different items detected"
                color="orange"
              />
            </div>

            {/* Info Banner */}
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-8 flex items-start gap-3">
              <Info className="h-5 w-5 text-blue-600 flex-shrink-0 mt-0.5" />
              <div>
                <h3 className="font-medium text-blue-900">About Escalation Scoring</h3>
                <p className="text-sm text-blue-700 mt-1">
                  Escalation scores are calculated based on equipment presence: High-risk items (shields, batons, tasers)
                  score 3 points each, medium-risk items (helmets, body armor) score 1 point each.
                  Higher scores indicate greater potential for confrontational scenarios.
                </p>
              </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Left Column - Category Distribution & Top Equipment */}
              <div className="space-y-6">
                <CategoryDistribution distribution={data.category_distribution} />

                {/* Top Equipment */}
                <Card className="p-4">
                  <h3 className="font-semibold text-gray-900 mb-4">Most Common Equipment</h3>
                  <div className="space-y-2">
                    {data.equipment_counts?.slice(0, 10).map((eq, i) => {
                      const style = CATEGORY_COLORS[eq.category] || CATEGORY_COLORS.specialist;
                      return (
                        <div key={i} className="flex items-center justify-between p-2 rounded bg-gray-50">
                          <div className="flex items-center gap-2">
                            <span className={`w-3 h-3 rounded-full ${style.bg.replace('100', '500')}`} />
                            <span className="text-sm font-medium">{eq.name}</span>
                          </div>
                          <span className="text-sm text-gray-500">{eq.count}</span>
                        </div>
                      );
                    })}
                  </div>
                </Card>
              </div>

              {/* Right Column - Escalation Events & Co-occurrences */}
              <div className="lg:col-span-2 space-y-6">
                {/* Escalation Events */}
                {data.escalation_events?.length > 0 && (
                  <div>
                    <h2 className="text-lg font-bold text-gray-900 mb-4 flex items-center gap-2">
                      <AlertTriangle className="h-5 w-5 text-red-500" />
                      Escalation Events
                    </h2>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {data.escalation_events.slice(0, 6).map((event, i) => (
                        <EscalationEventCard key={i} event={event} />
                      ))}
                    </div>
                  </div>
                )}

                {/* Co-occurrences */}
                {data.co_occurrences?.length > 0 && (
                  <Card className="p-4">
                    <h3 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
                      <Link2 className="h-5 w-5 text-green-600" />
                      Equipment Co-occurrences
                    </h3>
                    <p className="text-sm text-gray-500 mb-4">
                      Equipment items frequently seen together on the same officer
                    </p>
                    <div className="space-y-2">
                      {data.co_occurrences.slice(0, 10).map((pair, i) => (
                        <CoOccurrenceCard
                          key={i}
                          item1={pair.item1}
                          item2={pair.item2}
                          count={pair.count}
                        />
                      ))}
                    </div>
                  </Card>
                )}

                {/* Escalation Indicators Reference */}
                {data.escalation_indicators && (
                  <Card className="p-4">
                    <h3 className="font-semibold text-gray-900 mb-4">Escalation Indicator Reference</h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div>
                        <div className="flex items-center gap-2 mb-2">
                          <div className="w-3 h-3 rounded-full bg-red-500" />
                          <span className="text-sm font-medium text-red-700">High Risk (3 pts each)</span>
                        </div>
                        <div className="flex flex-wrap gap-1">
                          {data.escalation_indicators.high.map((eq, i) => (
                            <span key={i} className="bg-red-100 text-red-800 text-xs px-2 py-0.5 rounded">
                              {eq}
                            </span>
                          ))}
                        </div>
                      </div>
                      <div>
                        <div className="flex items-center gap-2 mb-2">
                          <div className="w-3 h-3 rounded-full bg-orange-500" />
                          <span className="text-sm font-medium text-orange-700">Medium Risk (1 pt each)</span>
                        </div>
                        <div className="flex flex-wrap gap-1">
                          {data.escalation_indicators.medium.map((eq, i) => (
                            <span key={i} className="bg-orange-100 text-orange-800 text-xs px-2 py-0.5 rounded">
                              {eq}
                            </span>
                          ))}
                        </div>
                      </div>
                    </div>
                  </Card>
                )}
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

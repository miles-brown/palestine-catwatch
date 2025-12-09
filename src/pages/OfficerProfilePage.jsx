import { useEffect, useState, useCallback, useRef, useMemo } from 'react';
import { useParams, Link } from 'react-router-dom';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import {
  ArrowLeft, Shield, User, Clock, MapPin, Camera, Video, Calendar,
  Award, ChevronUp, ChevronDown, RefreshCw, Download, AlertTriangle,
  FileText, Users, Eye, Share2, ExternalLink, Image as ImageIcon
} from 'lucide-react';
import UniformAnalysisCard from '@/components/UniformAnalysisCard';
import { Skeleton } from '@/components/ui/skeleton';
import { API_BASE, getMediaUrl, fetchWithErrorHandling } from '../utils/api';
import { getRankColor, logger } from '../utils/constants';
import { withErrorBoundary } from '../components/ErrorBoundary';

// Use centralized utility for secure path handling
const getCropUrl = getMediaUrl;

// Profile Header Component
const ProfileHeader = ({ officer, network, onDownloadDossier, downloading, downloadError, mediaCount, verifiedCount }) => {
  const primaryAppearance = officer.appearances?.[0];
  const cropUrl = primaryAppearance?.image_crop_path
    ? getCropUrl(primaryAppearance.image_crop_path)
    : null;

  return (
    <div className="bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 text-white rounded-xl overflow-hidden">
      <div className="p-6 md:p-8">
        <div className="flex flex-col md:flex-row gap-6 items-start">
          {/* Officer Image */}
          <div className="relative">
            {cropUrl ? (
              <img
                src={cropUrl}
                alt="Officer"
                className="w-32 h-32 md:w-40 md:h-40 rounded-xl object-cover border-4 border-white/20"
              />
            ) : (
              <div className="w-32 h-32 md:w-40 md:h-40 rounded-xl bg-slate-700 flex items-center justify-center border-4 border-white/20">
                <User className="h-16 w-16 text-slate-500" />
              </div>
            )}
            {officer.rank && (
              <div className="absolute -bottom-2 -right-2">
                <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-bold border-2 ${getRankColor(officer.rank)}`}>
                  <Award className="h-4 w-4 mr-1" />
                  {officer.rank}
                </span>
              </div>
            )}
          </div>

          {/* Officer Details */}
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-2">
              <Shield className="h-6 w-6 text-green-400" />
              <span className="text-green-400 uppercase text-sm font-bold tracking-wider">Officer Profile</span>
            </div>

            <h1 className="text-3xl md:text-4xl font-bold mb-3">
              {officer.badge_number || `Officer #${officer.id}`}
            </h1>

            <div className="flex flex-wrap items-center gap-4 text-slate-300 mb-4">
              {officer.force && (
                <span className="flex items-center gap-1">
                  <Shield className="h-4 w-4" />
                  {officer.force}
                </span>
              )}
              <span className="flex items-center gap-1">
                <Camera className="h-4 w-4" />
                {officer.appearances?.length || 0} appearances
              </span>
              {network?.co_appearances?.length > 0 && (
                <span className="flex items-center gap-1">
                  <Users className="h-4 w-4" />
                  {network.co_appearances.length} associates
                </span>
              )}
            </div>

            {/* Quick Stats */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6">
              <div className="bg-white/10 rounded-lg p-3 text-center">
                <div className="text-2xl font-bold">{officer.appearances?.length || 0}</div>
                <div className="text-xs text-slate-400 uppercase">Appearances</div>
              </div>
              <div className="bg-white/10 rounded-lg p-3 text-center">
                <div className="text-2xl font-bold">{mediaCount}</div>
                <div className="text-xs text-slate-400 uppercase">Media Files</div>
              </div>
              <div className="bg-white/10 rounded-lg p-3 text-center">
                <div className="text-2xl font-bold">
                  {network?.co_appearances?.length || 0}
                </div>
                <div className="text-xs text-slate-400 uppercase">Associates</div>
              </div>
              <div className="bg-white/10 rounded-lg p-3 text-center">
                <div className="text-2xl font-bold">{verifiedCount}</div>
                <div className="text-xs text-slate-400 uppercase">Verified</div>
              </div>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex flex-col gap-2">
            <Button
              onClick={onDownloadDossier}
              disabled={downloading}
              className="bg-green-600 hover:bg-green-700"
            >
              {downloading ? (
                <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <Download className="h-4 w-4 mr-2" />
              )}
              Download Dossier
            </Button>
            {downloadError && (
              <div className="text-red-400 text-xs flex items-center gap-1">
                <AlertTriangle className="h-3 w-3" />
                {downloadError}
              </div>
            )}
            <Button variant="outline" className="border-white/30 text-white hover:bg-white/10">
              <Share2 className="h-4 w-4 mr-2" />
              Share Profile
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};

// Chain of Command Section
const ChainOfCommandSection = ({ officerId }) => {
  const [chainData, setChainData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const controller = new AbortController();

    fetchWithErrorHandling(`${API_BASE}/officers/${officerId}/chain`, {
      signal: controller.signal
    })
      .then(setChainData)
      .catch(err => {
        // Ignore abort errors - component unmounted
        if (err.name !== 'AbortError') {
          logger.warn('Failed to fetch chain of command:', err);
        }
      })
      .finally(() => setLoading(false));

    return () => controller.abort();
  }, [officerId]);

  if (loading) {
    return (
      <Card className="p-6">
        <Skeleton className="h-6 w-48 mb-4" />
        <div className="space-y-3">
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-16 w-full" />
        </div>
      </Card>
    );
  }

  return (
    <Card className="p-6">
      <h3 className="text-lg font-bold text-gray-900 flex items-center gap-2 mb-4">
        <Users className="h-5 w-5 text-green-600" />
        Chain of Command
      </h3>

      {/* Supervisors */}
      <div className="mb-6">
        <h4 className="text-sm font-semibold text-gray-700 uppercase tracking-wider mb-3 flex items-center gap-1">
          <ChevronUp className="h-4 w-4" />
          Supervisors
        </h4>
        {chainData?.supervisors?.length > 0 ? (
          <div className="space-y-2">
            {chainData.supervisors.map((sup, idx) => (
              <Link
                key={sup.id}
                to={`/officer/${sup.id}`}
                className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg border-l-4 border-green-500 hover:bg-gray-100 transition-colors"
                style={{ marginLeft: `${idx * 12}px` }}
              >
                <Shield className="h-5 w-5 text-green-600 flex-shrink-0" />
                <div className="flex-1">
                  <div className="font-medium text-gray-900">
                    {sup.badge_number || `Officer #${sup.id}`}
                  </div>
                  <div className="text-sm text-gray-500">
                    {sup.rank || 'Unknown Rank'} - {sup.force || 'Unknown Force'}
                  </div>
                </div>
                <ExternalLink className="h-4 w-4 text-gray-400" />
              </Link>
            ))}
          </div>
        ) : (
          <p className="text-sm text-gray-500 italic">No supervisor linked</p>
        )}
      </div>

      {/* Subordinates */}
      <div>
        <h4 className="text-sm font-semibold text-gray-700 uppercase tracking-wider mb-3 flex items-center gap-1">
          <ChevronDown className="h-4 w-4" />
          Direct Reports
        </h4>
        {chainData?.subordinates?.length > 0 ? (
          <div className="space-y-2">
            {chainData.subordinates.map((sub) => (
              <Link
                key={sub.id}
                to={`/officer/${sub.id}`}
                className="flex items-center gap-3 p-3 bg-blue-50 rounded-lg border-l-4 border-blue-500 hover:bg-blue-100 transition-colors"
              >
                <Users className="h-5 w-5 text-blue-600 flex-shrink-0" />
                <div className="flex-1">
                  <div className="font-medium text-gray-900">
                    {sub.badge_number || `Officer #${sub.id}`}
                  </div>
                  <div className="text-sm text-gray-500">
                    {sub.rank || 'Unknown Rank'} - {sub.force || 'Unknown Force'}
                  </div>
                </div>
                {sub.subordinate_count > 0 && (
                  <span className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded">
                    +{sub.subordinate_count}
                  </span>
                )}
                <ExternalLink className="h-4 w-4 text-gray-400" />
              </Link>
            ))}
          </div>
        ) : (
          <p className="text-sm text-gray-500 italic">No direct reports</p>
        )}
      </div>
    </Card>
  );
};

// Network Section (Officers who appear together)
const NetworkSection = ({ network }) => {
  if (!network?.co_appearances?.length) {
    return (
      <Card className="p-6">
        <h3 className="text-lg font-bold text-gray-900 flex items-center gap-2 mb-4">
          <Share2 className="h-5 w-5 text-purple-600" />
          Officer Network
        </h3>
        <p className="text-sm text-gray-500 italic">No co-appearances found</p>
      </Card>
    );
  }

  return (
    <Card className="p-6">
      <h3 className="text-lg font-bold text-gray-900 flex items-center gap-2 mb-4">
        <Share2 className="h-5 w-5 text-purple-600" />
        Officer Network ({network.co_appearances.length} associates)
      </h3>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {network.co_appearances.slice(0, 8).map((assoc) => (
          <Link
            key={assoc.officer_id}
            to={`/officer/${assoc.officer_id}`}
            className="flex items-center gap-3 p-3 bg-purple-50 rounded-lg hover:bg-purple-100 transition-colors"
          >
            {assoc.crop_path && getCropUrl(assoc.crop_path) ? (
              <img
                src={getCropUrl(assoc.crop_path)}
                alt="Associate"
                className="w-10 h-10 rounded-full object-cover"
              />
            ) : (
              <div className="w-10 h-10 rounded-full bg-purple-200 flex items-center justify-center">
                <User className="h-5 w-5 text-purple-600" />
              </div>
            )}
            <div className="flex-1 min-w-0">
              <div className="font-medium text-gray-900 truncate">
                {assoc.badge_number || `Officer #${assoc.officer_id}`}
              </div>
              <div className="text-xs text-gray-500">
                {assoc.co_appearance_count} shared appearance{assoc.co_appearance_count !== 1 ? 's' : ''}
              </div>
            </div>
          </Link>
        ))}
      </div>
      {network.co_appearances.length > 8 && (
        <p className="text-sm text-gray-500 mt-3 text-center">
          +{network.co_appearances.length - 8} more associates
        </p>
      )}
    </Card>
  );
};

// Appearances Timeline
const AppearancesTimeline = ({ appearances }) => {
  const [expandedAppearance, setExpandedAppearance] = useState(null);

  if (!appearances?.length) {
    return (
      <Card className="p-6">
        <h3 className="text-lg font-bold text-gray-900 flex items-center gap-2 mb-4">
          <Clock className="h-5 w-5 text-blue-600" />
          Appearances Timeline
        </h3>
        <p className="text-sm text-gray-500 italic">No appearances recorded</p>
      </Card>
    );
  }

  // Group appearances by media
  const groupedByMedia = appearances.reduce((acc, app) => {
    const key = app.media_id;
    if (!acc[key]) {
      acc[key] = {
        media: app.media,
        appearances: []
      };
    }
    acc[key].appearances.push(app);
    return acc;
  }, {});

  return (
    <Card className="p-6">
      <h3 className="text-lg font-bold text-gray-900 flex items-center gap-2 mb-4">
        <Clock className="h-5 w-5 text-blue-600" />
        Appearances Timeline ({appearances.length} total)
      </h3>

      <div className="space-y-4">
        {Object.entries(groupedByMedia).map(([mediaId, { media, appearances: apps }]) => (
          <div key={mediaId} className="border rounded-lg overflow-hidden">
            {/* Media Header */}
            <div className="bg-gray-50 p-4 border-b">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  {media?.type === 'video' ? (
                    <Video className="h-5 w-5 text-red-500" />
                  ) : (
                    <ImageIcon className="h-5 w-5 text-blue-500" />
                  )}
                  <div>
                    <div className="font-medium text-gray-900">
                      Media #{mediaId}
                    </div>
                    {media?.timestamp && (
                      <div className="text-xs text-gray-500">
                        {new Date(media.timestamp).toLocaleString()}
                      </div>
                    )}
                  </div>
                </div>
                <Link
                  to={`/report/${mediaId}`}
                  className="text-sm text-green-600 hover:text-green-700 flex items-center gap-1"
                >
                  View Report <ExternalLink className="h-3 w-3" />
                </Link>
              </div>
            </div>

            {/* Appearances in this media */}
            <div className="divide-y">
              {apps.map((appearance) => (
                <div key={appearance.id} className="p-4">
                  <div
                    className="flex items-start gap-4 cursor-pointer"
                    onClick={() => setExpandedAppearance(
                      expandedAppearance === appearance.id ? null : appearance.id
                    )}
                  >
                    {appearance.image_crop_path && getCropUrl(appearance.image_crop_path) ? (
                      <img
                        src={getCropUrl(appearance.image_crop_path)}
                        alt="Appearance"
                        className="w-16 h-16 rounded-lg object-cover border"
                      />
                    ) : (
                      <div className="w-16 h-16 rounded-lg bg-gray-100 flex items-center justify-center">
                        <User className="h-8 w-8 text-gray-400" />
                      </div>
                    )}

                    <div className="flex-1">
                      <div className="flex items-center gap-2 flex-wrap">
                        {appearance.timestamp_in_video && (
                          <span className="bg-gray-100 text-gray-700 text-xs px-2 py-1 rounded font-mono">
                            {appearance.timestamp_in_video}
                          </span>
                        )}
                        {appearance.role && (
                          <span className="bg-blue-100 text-blue-700 text-xs px-2 py-1 rounded">
                            {appearance.role}
                          </span>
                        )}
                        {appearance.verified && (
                          <span className="bg-green-100 text-green-700 text-xs px-2 py-1 rounded">
                            Verified
                          </span>
                        )}
                        {appearance.confidence && (
                          <span className={`text-xs px-2 py-1 rounded ${
                            appearance.confidence >= 80 ? 'bg-green-100 text-green-700' :
                            appearance.confidence >= 50 ? 'bg-yellow-100 text-yellow-700' :
                            'bg-red-100 text-red-700'
                          }`}>
                            {Math.round(appearance.confidence)}% conf
                          </span>
                        )}
                      </div>
                      {appearance.action && (
                        <p className="text-sm text-gray-600 mt-1">{appearance.action}</p>
                      )}
                    </div>

                    <ChevronDown className={`h-5 w-5 text-gray-400 transition-transform ${
                      expandedAppearance === appearance.id ? 'rotate-180' : ''
                    }`} />
                  </div>

                  {/* Expanded Uniform Analysis */}
                  {expandedAppearance === appearance.id && (
                    <div className="mt-4 pt-4 border-t">
                      <UniformAnalysisCard
                        officerId={appearance.officer_id}
                        appearanceId={appearance.id}
                        cropPath={appearance.image_crop_path}
                        compact={false}
                      />
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
};

// Uniform Analyses Summary
const UniformSummary = ({ officerId }) => {
  const [uniformData, setUniformData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const controller = new AbortController();

    fetchWithErrorHandling(`${API_BASE}/officers/${officerId}/uniform`, {
      signal: controller.signal
    })
      .then(setUniformData)
      .catch(err => {
        // Ignore abort errors - component unmounted
        if (err.name !== 'AbortError') {
          logger.warn('Failed to fetch uniform data:', err);
        }
      })
      .finally(() => setLoading(false));

    return () => controller.abort();
  }, [officerId]);

  if (loading) {
    return (
      <Card className="p-6">
        <Skeleton className="h-6 w-48 mb-4" />
        <div className="space-y-3">
          <Skeleton className="h-24 w-full" />
        </div>
      </Card>
    );
  }

  if (!uniformData?.analyses?.length) {
    return (
      <Card className="p-6">
        <h3 className="text-lg font-bold text-gray-900 flex items-center gap-2 mb-4">
          <Shield className="h-5 w-5 text-orange-600" />
          Uniform Analysis
        </h3>
        <p className="text-sm text-gray-500 italic">No uniform analyses available</p>
      </Card>
    );
  }

  // Aggregate data from all analyses
  const forceCounts = {};
  const rankCounts = {};
  const unitCounts = {};
  const equipmentCounts = {};

  uniformData.analyses.forEach(analysis => {
    if (analysis.analysis?.detected_force) {
      forceCounts[analysis.analysis.detected_force] = (forceCounts[analysis.analysis.detected_force] || 0) + 1;
    }
    if (analysis.analysis?.detected_rank) {
      rankCounts[analysis.analysis.detected_rank] = (rankCounts[analysis.analysis.detected_rank] || 0) + 1;
    }
    if (analysis.analysis?.unit_type) {
      unitCounts[analysis.analysis.unit_type] = (unitCounts[analysis.analysis.unit_type] || 0) + 1;
    }
    analysis.equipment?.forEach(eq => {
      equipmentCounts[eq.name] = (equipmentCounts[eq.name] || 0) + 1;
    });
  });

  const mostLikelyForce = Object.entries(forceCounts).sort((a, b) => b[1] - a[1])[0];
  const mostLikelyRank = Object.entries(rankCounts).sort((a, b) => b[1] - a[1])[0];
  const mostLikelyUnit = Object.entries(unitCounts).sort((a, b) => b[1] - a[1])[0];

  return (
    <Card className="p-6">
      <h3 className="text-lg font-bold text-gray-900 flex items-center gap-2 mb-4">
        <Shield className="h-5 w-5 text-orange-600" />
        Uniform Analysis Summary
      </h3>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        {mostLikelyForce && (
          <div className="bg-blue-50 rounded-lg p-4">
            <div className="text-xs text-blue-600 uppercase font-bold mb-1">Most Detected Force</div>
            <div className="font-semibold text-gray-900">{mostLikelyForce[0]}</div>
            <div className="text-xs text-gray-500">{mostLikelyForce[1]} detection{mostLikelyForce[1] !== 1 ? 's' : ''}</div>
          </div>
        )}
        {mostLikelyRank && (
          <div className="bg-green-50 rounded-lg p-4">
            <div className="text-xs text-green-600 uppercase font-bold mb-1">Most Detected Rank</div>
            <div className="font-semibold text-gray-900">{mostLikelyRank[0]}</div>
            <div className="text-xs text-gray-500">{mostLikelyRank[1]} detection{mostLikelyRank[1] !== 1 ? 's' : ''}</div>
          </div>
        )}
        {mostLikelyUnit && (
          <div className="bg-orange-50 rounded-lg p-4">
            <div className="text-xs text-orange-600 uppercase font-bold mb-1">Most Detected Unit</div>
            <div className="font-semibold text-gray-900">{mostLikelyUnit[0]}</div>
            <div className="text-xs text-gray-500">{mostLikelyUnit[1]} detection{mostLikelyUnit[1] !== 1 ? 's' : ''}</div>
          </div>
        )}
      </div>

      {/* Equipment Breakdown */}
      {Object.keys(equipmentCounts).length > 0 && (
        <div>
          <h4 className="text-sm font-semibold text-gray-700 mb-2">Equipment Observed</h4>
          <div className="flex flex-wrap gap-2">
            {Object.entries(equipmentCounts)
              .sort((a, b) => b[1] - a[1])
              .map(([name, count]) => (
                <span
                  key={name}
                  className="bg-gray-100 text-gray-700 text-xs px-2 py-1 rounded"
                >
                  {name} ({count}x)
                </span>
              ))}
          </div>
        </div>
      )}
    </Card>
  );
};

// Main Officer Profile Page
function OfficerProfilePage() {
  const { officerId } = useParams();
  const [officer, setOfficer] = useState(null);
  const [network, setNetwork] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [downloading, setDownloading] = useState(false);
  const [downloadError, setDownloadError] = useState(null);

  // Ref for abort controller to prevent memory leaks
  const abortControllerRef = useRef(null);

  const fetchOfficerData = useCallback(async (signal) => {
    setLoading(true);
    setError(null);

    try {
      // Fetch officer data (required) and network (optional) in parallel
      const [officerData, networkData] = await Promise.all([
        // Officer data is required - use error handling helper
        fetchWithErrorHandling(`${API_BASE}/officers/${officerId}`, { signal }),
        // Network data is optional - catch errors and return null
        fetchWithErrorHandling(`${API_BASE}/officers/${officerId}/network`, { signal })
          .catch(() => null)
      ]);

      setOfficer(officerData);
      setNetwork(networkData);
    } catch (err) {
      // Ignore abort errors
      if (err.name === 'AbortError') return;
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [officerId]);

  useEffect(() => {
    // Abort previous request if any
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    // Create new abort controller
    abortControllerRef.current = new AbortController();
    fetchOfficerData(abortControllerRef.current.signal);

    // Cleanup: abort on unmount or officerId change
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, [fetchOfficerData]);

  const handleDownloadDossier = async () => {
    setDownloading(true);
    setDownloadError(null);
    try {
      const response = await fetch(`${API_BASE}/officers/${officerId}/dossier`);
      if (!response.ok) throw new Error('Failed to generate dossier');

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `officer-${officerId}-dossier.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      logger.error('Dossier download failed:', err);
      setDownloadError('Failed to download dossier. Please try again.');
    } finally {
      setDownloading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          {/* Back button skeleton */}
          <Skeleton className="h-10 w-32 mb-6" />

          {/* Header skeleton */}
          <div className="bg-slate-900 rounded-xl p-8 mb-8">
            <div className="flex gap-6">
              <Skeleton className="w-40 h-40 rounded-xl" />
              <div className="flex-1 space-y-4">
                <Skeleton className="h-6 w-32" />
                <Skeleton className="h-10 w-64" />
                <Skeleton className="h-4 w-48" />
                <div className="grid grid-cols-4 gap-4 mt-6">
                  {Array.from({ length: 4 }).map((_, i) => (
                    <Skeleton key={i} className="h-20" />
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* Content skeleton */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2 space-y-6">
              <Skeleton className="h-64" />
              <Skeleton className="h-96" />
            </div>
            <div className="space-y-6">
              <Skeleton className="h-48" />
              <Skeleton className="h-64" />
            </div>
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
          <h2 className="text-xl font-bold text-gray-900 mb-2">Error Loading Officer</h2>
          <p className="text-red-500 mb-4">{error}</p>
          <Link to="/dashboard">
            <Button>Back to Dashboard</Button>
          </Link>
        </div>
      </div>
    );
  }

  // Memoize expensive calculations to prevent recreation on every render
  const mediaCount = useMemo(() => {
    if (!officer?.appearances) return 0;
    return new Set(officer.appearances.map(a => a.media_id)).size;
  }, [officer?.appearances]);

  const verifiedCount = useMemo(() => {
    if (!officer?.appearances) return 0;
    return officer.appearances.filter(a => a.verified).length;
  }, [officer?.appearances]);

  if (!officer) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <User className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <p className="text-gray-600">Officer not found.</p>
          <Link to="/dashboard">
            <Button className="mt-4">Back to Dashboard</Button>
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {/* Back Button */}
        <Link to="/dashboard" className="inline-flex items-center text-gray-600 hover:text-gray-900 mb-6">
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to Dashboard
        </Link>

        {/* Profile Header */}
        <div className="mb-8">
          <ProfileHeader
            officer={officer}
            network={network}
            onDownloadDossier={handleDownloadDossier}
            downloading={downloading}
            downloadError={downloadError}
            mediaCount={mediaCount}
            verifiedCount={verifiedCount}
          />
        </div>

        {/* Main Content Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Column - Timeline & Appearances */}
          <div className="lg:col-span-2 space-y-6">
            {/* Uniform Analysis Summary */}
            <UniformSummary officerId={officerId} />

            {/* Appearances Timeline */}
            <AppearancesTimeline appearances={officer.appearances} />
          </div>

          {/* Right Column - Chain of Command & Network */}
          <div className="space-y-6">
            {/* Chain of Command */}
            <ChainOfCommandSection officerId={officerId} />

            {/* Network */}
            <NetworkSection network={network} />

            {/* Officer Notes */}
            {officer.notes && (
              <Card className="p-6">
                <h3 className="text-lg font-bold text-gray-900 flex items-center gap-2 mb-4">
                  <FileText className="h-5 w-5 text-gray-600" />
                  Notes
                </h3>
                <p className="text-gray-600 whitespace-pre-wrap">{officer.notes}</p>
              </Card>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default withErrorBoundary(OfficerProfilePage, 'An error occurred while loading the Officer Profile. Please try again.');

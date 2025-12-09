import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  Users, Edit2, Trash2, Merge, Save, X, Search,
  ChevronLeft, ChevronRight, AlertTriangle, CheckCircle,
  Download, FileJson, FileSpreadsheet, Shield, Eye, ThumbsUp, ThumbsDown,
  BarChart3, Clock
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import PasswordGate from '@/components/PasswordGate';

let API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";
if (!API_BASE.startsWith("http")) {
  API_BASE = `https://${API_BASE}`;
}

const ITEMS_PER_PAGE = 20;

const AdminPage = () => {
  const [activeTab, setActiveTab] = useState('officers'); // 'officers' or 'verification'
  const [officers, setOfficers] = useState([]);
  const [totalOfficers, setTotalOfficers] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');

  // Edit state
  const [editingOfficer, setEditingOfficer] = useState(null);
  const [editForm, setEditForm] = useState({ badge_number: '', force: '', notes: '' });

  // Merge state
  const [mergeMode, setMergeMode] = useState(false);
  const [selectedForMerge, setSelectedForMerge] = useState([]);
  const [primaryOfficer, setPrimaryOfficer] = useState(null);

  // Status messages
  const [statusMessage, setStatusMessage] = useState(null);

  // Verification state
  const [unverifiedAppearances, setUnverifiedAppearances] = useState([]);
  const [verificationStats, setVerificationStats] = useState(null);
  const [verificationLoading, setVerificationLoading] = useState(false);
  const [verificationPage, setVerificationPage] = useState(1);
  const [totalUnverified, setTotalUnverified] = useState(0);

  // Fetch officers
  useEffect(() => {
    if (activeTab !== 'officers') return;

    const fetchOfficers = async () => {
      setLoading(true);
      try {
        const skip = (currentPage - 1) * ITEMS_PER_PAGE;
        const params = new URLSearchParams({
          skip: skip.toString(),
          limit: ITEMS_PER_PAGE.toString(),
        });
        if (searchQuery) {
          params.append('badge_number', searchQuery);
        }

        const [officersRes, countRes] = await Promise.all([
          fetch(`${API_BASE}/officers?${params}`),
          fetch(`${API_BASE}/officers/count${searchQuery ? `?badge_number=${searchQuery}` : ''}`)
        ]);

        const officersData = await officersRes.json();
        const countData = await countRes.json();

        setOfficers(officersData);
        setTotalOfficers(countData.count || 0);
      } catch (error) {
        console.error("Failed to fetch officers:", error);
        setStatusMessage({ type: 'error', text: 'Failed to load officers' });
      } finally {
        setLoading(false);
      }
    };

    fetchOfficers();
  }, [currentPage, searchQuery, activeTab]);

  // Fetch verification data
  useEffect(() => {
    if (activeTab !== 'verification') return;

    const fetchVerificationData = async () => {
      setVerificationLoading(true);
      try {
        const skip = (verificationPage - 1) * ITEMS_PER_PAGE;
        const [appearancesRes, statsRes] = await Promise.all([
          fetch(`${API_BASE}/appearances/unverified?skip=${skip}&limit=${ITEMS_PER_PAGE}`),
          fetch(`${API_BASE}/confidence/stats`)
        ]);

        const appearancesData = await appearancesRes.json();
        const statsData = await statsRes.json();

        setUnverifiedAppearances(appearancesData.appearances || []);
        setTotalUnverified(appearancesData.total || 0);
        setVerificationStats(statsData);
      } catch (error) {
        console.error("Failed to fetch verification data:", error);
        setStatusMessage({ type: 'error', text: 'Failed to load verification data' });
      } finally {
        setVerificationLoading(false);
      }
    };

    fetchVerificationData();
  }, [activeTab, verificationPage]);

  // Handle verification action
  const handleVerify = async (appearanceId, verified) => {
    try {
      const response = await fetch(`${API_BASE}/appearances/${appearanceId}/verify`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ verified, confidence: verified ? 100 : 0 })
      });

      if (!response.ok) throw new Error('Verification failed');

      // Remove from list
      setUnverifiedAppearances(prev => prev.filter(a => a.id !== appearanceId));
      setTotalUnverified(prev => prev - 1);

      // Update stats
      if (verificationStats) {
        setVerificationStats(prev => ({
          ...prev,
          verified_count: prev.verified_count + (verified ? 1 : 0),
          unverified_count: prev.unverified_count - 1
        }));
      }

      setStatusMessage({
        type: 'success',
        text: verified ? 'Detection verified' : 'Detection rejected'
      });
      setTimeout(() => setStatusMessage(null), 2000);

    } catch (error) {
      setStatusMessage({ type: 'error', text: 'Failed to update verification' });
    }
  };

  const getCropUrl = (cropPath) => {
    if (!cropPath) return null;
    const cleanPath = cropPath.split('data/')[1] || cropPath.replace('../data/', '').replace(/^\/+/, '');
    return `${API_BASE}/data/${cleanPath}`;
  };

  const getConfidenceColor = (confidence) => {
    if (confidence === null || confidence === undefined) return 'text-gray-500';
    if (confidence >= 80) return 'text-green-600';
    if (confidence >= 50) return 'text-yellow-600';
    return 'text-red-600';
  };

  const getConfidenceBg = (confidence) => {
    if (confidence === null || confidence === undefined) return 'bg-gray-100';
    if (confidence >= 80) return 'bg-green-100';
    if (confidence >= 50) return 'bg-yellow-100';
    return 'bg-red-100';
  };

  const totalPages = Math.ceil(totalOfficers / ITEMS_PER_PAGE);

  // Start editing an officer
  const handleStartEdit = (officer) => {
    setEditingOfficer(officer.id);
    setEditForm({
      badge_number: officer.badge_number || '',
      force: officer.force || '',
      notes: officer.notes || ''
    });
  };

  // Save edited officer
  const handleSaveEdit = async () => {
    try {
      const params = new URLSearchParams();
      if (editForm.badge_number) params.append('badge_number', editForm.badge_number);
      if (editForm.force) params.append('force', editForm.force);
      if (editForm.notes) params.append('notes', editForm.notes);

      const response = await fetch(`${API_BASE}/officers/${editingOfficer}?${params}`, {
        method: 'PATCH',
      });

      if (!response.ok) throw new Error('Update failed');

      // Update local state
      setOfficers(officers.map(o =>
        o.id === editingOfficer
          ? { ...o, ...editForm }
          : o
      ));

      setEditingOfficer(null);
      setStatusMessage({ type: 'success', text: 'Officer updated successfully' });
      setTimeout(() => setStatusMessage(null), 3000);

    } catch (error) {
      setStatusMessage({ type: 'error', text: 'Failed to update officer' });
    }
  };

  // Delete officer
  const handleDelete = async (officerId) => {
    if (!confirm('Are you sure you want to delete this officer? This action cannot be undone.')) {
      return;
    }

    try {
      const response = await fetch(`${API_BASE}/officers/${officerId}`, {
        method: 'DELETE',
      });

      if (!response.ok) throw new Error('Delete failed');

      setOfficers(officers.filter(o => o.id !== officerId));
      setTotalOfficers(prev => prev - 1);
      setStatusMessage({ type: 'success', text: 'Officer deleted successfully' });
      setTimeout(() => setStatusMessage(null), 3000);

    } catch (error) {
      setStatusMessage({ type: 'error', text: 'Failed to delete officer' });
    }
  };

  // Toggle merge selection
  const toggleMergeSelection = (officerId) => {
    if (selectedForMerge.includes(officerId)) {
      setSelectedForMerge(selectedForMerge.filter(id => id !== officerId));
      if (primaryOfficer === officerId) {
        setPrimaryOfficer(null);
      }
    } else {
      setSelectedForMerge([...selectedForMerge, officerId]);
      if (!primaryOfficer) {
        setPrimaryOfficer(officerId);
      }
    }
  };

  // Execute merge
  const handleMerge = async () => {
    if (!primaryOfficer || selectedForMerge.length < 2) {
      setStatusMessage({ type: 'error', text: 'Select at least 2 officers and set a primary' });
      return;
    }

    const secondaryIds = selectedForMerge.filter(id => id !== primaryOfficer);

    try {
      const params = new URLSearchParams({
        primary_id: primaryOfficer.toString(),
      });
      secondaryIds.forEach(id => params.append('secondary_ids', id.toString()));

      const response = await fetch(`${API_BASE}/officers/merge?${params}`, {
        method: 'POST',
      });

      if (!response.ok) throw new Error('Merge failed');

      const data = await response.json();

      // Remove merged officers from list
      setOfficers(officers.filter(o => !secondaryIds.includes(o.id)));
      setTotalOfficers(prev => prev - secondaryIds.length);

      // Reset merge mode
      setMergeMode(false);
      setSelectedForMerge([]);
      setPrimaryOfficer(null);

      setStatusMessage({ type: 'success', text: data.message || 'Officers merged successfully' });
      setTimeout(() => setStatusMessage(null), 3000);

    } catch (error) {
      setStatusMessage({ type: 'error', text: 'Failed to merge officers' });
    }
  };

  // Cancel merge mode
  const cancelMerge = () => {
    setMergeMode(false);
    setSelectedForMerge([]);
    setPrimaryOfficer(null);
  };

  const verificationPages = Math.ceil(totalUnverified / ITEMS_PER_PAGE);

  return (
    <PasswordGate>
      <div className="min-h-screen bg-gray-50">
        {/* Header */}
        <div className="bg-white border-b-2 border-green-700">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
            <div className="flex items-center justify-between flex-wrap gap-4">
              <div>
                <h1 className="text-3xl font-bold text-gray-900">
                  Admin Panel
                </h1>
                <p className="text-gray-600 mt-2">
                  Edit, merge, and manage officer records
                </p>
              </div>
              <div className="flex items-center gap-3">
                {/* Export Dropdown */}
                <div className="relative group">
                  <Button variant="outline" className="flex items-center gap-2">
                    <Download className="h-4 w-4" />
                    Export
                  </Button>
                  <div className="absolute right-0 mt-2 w-48 bg-white rounded-lg shadow-lg border border-gray-200 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all z-10">
                    <a
                      href={`${API_BASE}/export/officers/csv`}
                      className="flex items-center gap-2 px-4 py-3 hover:bg-gray-50 rounded-t-lg text-sm"
                    >
                      <FileSpreadsheet className="h-4 w-4 text-green-600" />
                      Export as CSV
                    </a>
                    <a
                      href={`${API_BASE}/export/officers/json`}
                      className="flex items-center gap-2 px-4 py-3 hover:bg-gray-50 rounded-b-lg border-t text-sm"
                    >
                      <FileJson className="h-4 w-4 text-blue-600" />
                      Export as JSON
                    </a>
                  </div>
                </div>

                {mergeMode ? (
                  <>
                    <Button
                      onClick={handleMerge}
                      disabled={selectedForMerge.length < 2}
                      className="bg-blue-600 hover:bg-blue-700 text-white"
                    >
                      <Merge className="h-4 w-4 mr-2" />
                      Merge ({selectedForMerge.length})
                    </Button>
                    <Button onClick={cancelMerge} variant="outline">
                      Cancel
                    </Button>
                  </>
                ) : (
                  <Button
                    onClick={() => setMergeMode(true)}
                    className="bg-blue-600 hover:bg-blue-700 text-white"
                  >
                    <Merge className="h-4 w-4 mr-2" />
                    Merge Officers
                  </Button>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="bg-white border-b border-gray-200">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex gap-6">
              <button
                onClick={() => setActiveTab('officers')}
                className={`py-4 px-1 text-sm font-medium border-b-2 transition ${
                  activeTab === 'officers'
                    ? 'border-green-600 text-green-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700'
                }`}
              >
                <Users className="h-4 w-4 inline mr-2" />
                Officers ({totalOfficers})
              </button>
              <button
                onClick={() => setActiveTab('verification')}
                className={`py-4 px-1 text-sm font-medium border-b-2 transition ${
                  activeTab === 'verification'
                    ? 'border-green-600 text-green-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700'
                }`}
              >
                <Eye className="h-4 w-4 inline mr-2" />
                Verification Review
                {totalUnverified > 0 && (
                  <span className="ml-2 px-2 py-0.5 bg-yellow-100 text-yellow-800 text-xs rounded-full">
                    {totalUnverified}
                  </span>
                )}
              </button>
            </div>
          </div>
        </div>

        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {/* Status Message */}
          {statusMessage && (
            <div className={`mb-6 p-4 rounded-lg flex items-center gap-2 ${
              statusMessage.type === 'success'
                ? 'bg-green-100 text-green-800'
                : 'bg-red-100 text-red-800'
            }`}>
              {statusMessage.type === 'success' ? (
                <CheckCircle className="h-5 w-5" />
              ) : (
                <AlertTriangle className="h-5 w-5" />
              )}
              {statusMessage.text}
            </div>
          )}

          {/* VERIFICATION TAB */}
          {activeTab === 'verification' && (
            <div>
              {/* Confidence Stats */}
              {verificationStats && (
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                  <Card className="p-4">
                    <div className="text-sm text-gray-500 mb-1">Total Detections</div>
                    <div className="text-2xl font-bold text-gray-900">
                      {verificationStats.total_appearances}
                    </div>
                  </Card>
                  <Card className="p-4">
                    <div className="text-sm text-gray-500 mb-1">Verified</div>
                    <div className="text-2xl font-bold text-green-600">
                      {verificationStats.verified_count}
                    </div>
                    <div className="text-xs text-gray-500">
                      {verificationStats.verification_rate}%
                    </div>
                  </Card>
                  <Card className="p-4">
                    <div className="text-sm text-gray-500 mb-1">Pending Review</div>
                    <div className="text-2xl font-bold text-yellow-600">
                      {verificationStats.unverified_count}
                    </div>
                  </Card>
                  <Card className="p-4">
                    <div className="text-sm text-gray-500 mb-1">Avg. Confidence</div>
                    <div className="text-2xl font-bold text-blue-600">
                      {verificationStats.average_confidence || 'N/A'}%
                    </div>
                  </Card>
                </div>
              )}

              {/* Confidence Distribution */}
              {verificationStats?.confidence_distribution && (
                <Card className="p-4 mb-6">
                  <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
                    <BarChart3 className="h-4 w-4" />
                    Confidence Distribution
                  </h3>
                  <div className="flex gap-2 h-8">
                    <div
                      className="bg-green-500 rounded"
                      style={{ flex: verificationStats.confidence_distribution.high || 1 }}
                      title={`High (80%+): ${verificationStats.confidence_distribution.high}`}
                    />
                    <div
                      className="bg-yellow-500 rounded"
                      style={{ flex: verificationStats.confidence_distribution.medium || 1 }}
                      title={`Medium (50-79%): ${verificationStats.confidence_distribution.medium}`}
                    />
                    <div
                      className="bg-red-500 rounded"
                      style={{ flex: verificationStats.confidence_distribution.low || 1 }}
                      title={`Low (<50%): ${verificationStats.confidence_distribution.low}`}
                    />
                    <div
                      className="bg-gray-300 rounded"
                      style={{ flex: verificationStats.confidence_distribution.unknown || 1 }}
                      title={`Unknown: ${verificationStats.confidence_distribution.unknown}`}
                    />
                  </div>
                  <div className="flex justify-between mt-2 text-xs text-gray-500">
                    <span className="flex items-center gap-1">
                      <span className="w-3 h-3 bg-green-500 rounded"></span>
                      High ({verificationStats.confidence_distribution.high})
                    </span>
                    <span className="flex items-center gap-1">
                      <span className="w-3 h-3 bg-yellow-500 rounded"></span>
                      Medium ({verificationStats.confidence_distribution.medium})
                    </span>
                    <span className="flex items-center gap-1">
                      <span className="w-3 h-3 bg-red-500 rounded"></span>
                      Low ({verificationStats.confidence_distribution.low})
                    </span>
                    <span className="flex items-center gap-1">
                      <span className="w-3 h-3 bg-gray-300 rounded"></span>
                      Unknown ({verificationStats.confidence_distribution.unknown})
                    </span>
                  </div>
                </Card>
              )}

              {/* Unverified Appearances Grid */}
              <Card className="overflow-hidden">
                <div className="p-4 border-b bg-gray-50">
                  <h3 className="font-semibold text-gray-900">Pending Verification</h3>
                  <p className="text-sm text-gray-500">
                    Review and verify officer detections. Items are sorted by lowest confidence first.
                  </p>
                </div>

                {verificationLoading ? (
                  <div className="p-12 text-center">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-green-600 mx-auto"></div>
                  </div>
                ) : unverifiedAppearances.length === 0 ? (
                  <div className="p-12 text-center text-gray-500">
                    <CheckCircle className="h-12 w-12 mx-auto mb-3 text-green-500" />
                    <p className="text-lg">All detections verified!</p>
                    <p className="text-sm mt-1">No pending items to review.</p>
                  </div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 p-4">
                    {unverifiedAppearances.map((appearance) => (
                      <div
                        key={appearance.id}
                        className="border rounded-lg overflow-hidden bg-white"
                      >
                        {/* Image */}
                        <div className="aspect-square bg-gray-100 relative">
                          {appearance.image_crop_path ? (
                            <img
                              src={getCropUrl(appearance.image_crop_path)}
                              alt="Detection"
                              className="w-full h-full object-cover"
                              onError={(e) => {
                                e.target.style.display = 'none';
                              }}
                            />
                          ) : (
                            <div className="w-full h-full flex items-center justify-center">
                              <Users className="h-16 w-16 text-gray-300" />
                            </div>
                          )}

                          {/* Confidence Badge */}
                          <div className={`absolute top-2 right-2 px-2 py-1 rounded text-xs font-bold ${getConfidenceBg(appearance.confidence)} ${getConfidenceColor(appearance.confidence)}`}>
                            {appearance.confidence !== null ? `${Math.round(appearance.confidence)}%` : '?'}
                          </div>
                        </div>

                        {/* Details */}
                        <div className="p-3 space-y-2">
                          <div className="flex items-center justify-between">
                            <span className="font-medium text-gray-900">
                              {appearance.badge_number || `Officer #${appearance.officer_id}`}
                            </span>
                            <span className="text-xs text-gray-500">
                              {appearance.force || 'Unknown Force'}
                            </span>
                          </div>

                          {appearance.timestamp_in_video && (
                            <div className="flex items-center gap-1 text-xs text-gray-500">
                              <Clock className="h-3 w-3" />
                              {appearance.timestamp_in_video}
                            </div>
                          )}

                          {appearance.action && (
                            <p className="text-xs text-gray-600 truncate">
                              {appearance.action}
                            </p>
                          )}

                          {/* Action Buttons */}
                          <div className="flex gap-2 pt-2">
                            <button
                              onClick={() => handleVerify(appearance.id, true)}
                              className="flex-1 flex items-center justify-center gap-1 px-3 py-2 bg-green-100 text-green-700 rounded hover:bg-green-200 transition text-sm font-medium"
                            >
                              <ThumbsUp className="h-4 w-4" />
                              Verify
                            </button>
                            <button
                              onClick={() => handleVerify(appearance.id, false)}
                              className="flex-1 flex items-center justify-center gap-1 px-3 py-2 bg-red-100 text-red-700 rounded hover:bg-red-200 transition text-sm font-medium"
                            >
                              <ThumbsDown className="h-4 w-4" />
                              Reject
                            </button>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                {/* Pagination */}
                {verificationPages > 1 && (
                  <div className="flex items-center justify-between px-4 py-3 border-t bg-gray-50">
                    <div className="text-sm text-gray-600">
                      Page {verificationPage} of {verificationPages}
                    </div>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => setVerificationPage(prev => Math.max(1, prev - 1))}
                        disabled={verificationPage === 1}
                        className="p-2 rounded border bg-white hover:bg-gray-50 disabled:opacity-50"
                      >
                        <ChevronLeft className="h-4 w-4" />
                      </button>
                      <button
                        onClick={() => setVerificationPage(prev => Math.min(verificationPages, prev + 1))}
                        disabled={verificationPage === verificationPages}
                        className="p-2 rounded border bg-white hover:bg-gray-50 disabled:opacity-50"
                      >
                        <ChevronRight className="h-4 w-4" />
                      </button>
                    </div>
                  </div>
                )}
              </Card>
            </div>
          )}

          {/* OFFICERS TAB */}
          {activeTab === 'officers' && (
            <>
          {/* Merge Mode Instructions */}
          {mergeMode && (
            <div className="mb-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
              <h3 className="font-medium text-blue-800 mb-2">Merge Mode Active</h3>
              <p className="text-sm text-blue-700">
                Select officers to merge by clicking the checkboxes. The first selected officer
                will be the primary (kept), and others will be merged into it.
                Click on a different checkbox to change the primary.
              </p>
              {primaryOfficer && (
                <p className="text-sm text-blue-800 mt-2 font-medium">
                  Primary: Officer #{primaryOfficer}
                </p>
              )}
            </div>
          )}

          {/* Search */}
          <div className="mb-6">
            <div className="relative max-w-md">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400" />
              <input
                type="text"
                placeholder="Search by badge number..."
                value={searchQuery}
                onChange={(e) => {
                  setSearchQuery(e.target.value);
                  setCurrentPage(1);
                }}
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500"
              />
            </div>
          </div>

          {/* Officers Table */}
          <Card className="overflow-hidden">
            {loading ? (
              <div className="p-12 text-center">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-green-600 mx-auto"></div>
              </div>
            ) : officers.length === 0 ? (
              <div className="p-12 text-center text-gray-500">
                <Users className="h-12 w-12 mx-auto mb-3 opacity-50" />
                <p>No officers found</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-gray-50 border-b">
                    <tr>
                      {mergeMode && (
                        <th className="py-3 px-4 text-left text-xs font-medium text-gray-500 uppercase">
                          Select
                        </th>
                      )}
                      <th className="py-3 px-4 text-left text-xs font-medium text-gray-500 uppercase">
                        ID
                      </th>
                      <th className="py-3 px-4 text-left text-xs font-medium text-gray-500 uppercase">
                        Badge
                      </th>
                      <th className="py-3 px-4 text-left text-xs font-medium text-gray-500 uppercase">
                        Force
                      </th>
                      <th className="py-3 px-4 text-left text-xs font-medium text-gray-500 uppercase">
                        Appearances
                      </th>
                      <th className="py-3 px-4 text-left text-xs font-medium text-gray-500 uppercase">
                        Notes
                      </th>
                      <th className="py-3 px-4 text-right text-xs font-medium text-gray-500 uppercase">
                        Actions
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {officers.map((officer) => (
                      <tr
                        key={officer.id}
                        className={`hover:bg-gray-50 ${
                          selectedForMerge.includes(officer.id) ? 'bg-blue-50' : ''
                        } ${primaryOfficer === officer.id ? 'ring-2 ring-blue-500 ring-inset' : ''}`}
                      >
                        {mergeMode && (
                          <td className="py-3 px-4">
                            <input
                              type="checkbox"
                              checked={selectedForMerge.includes(officer.id)}
                              onChange={() => toggleMergeSelection(officer.id)}
                              className="w-5 h-5 text-blue-600 rounded"
                            />
                          </td>
                        )}
                        <td className="py-3 px-4 text-sm font-mono text-gray-600">
                          #{officer.id}
                        </td>
                        <td className="py-3 px-4">
                          {editingOfficer === officer.id ? (
                            <input
                              type="text"
                              value={editForm.badge_number}
                              onChange={(e) => setEditForm({ ...editForm, badge_number: e.target.value })}
                              className="w-full px-2 py-1 border rounded text-sm"
                              placeholder="Badge number"
                            />
                          ) : (
                            <span className="text-sm font-medium text-gray-900">
                              {officer.badge_number || '-'}
                            </span>
                          )}
                        </td>
                        <td className="py-3 px-4">
                          {editingOfficer === officer.id ? (
                            <input
                              type="text"
                              value={editForm.force}
                              onChange={(e) => setEditForm({ ...editForm, force: e.target.value })}
                              className="w-full px-2 py-1 border rounded text-sm"
                              placeholder="Force"
                            />
                          ) : (
                            <span className="text-sm text-gray-600">
                              {officer.force || '-'}
                            </span>
                          )}
                        </td>
                        <td className="py-3 px-4">
                          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-800">
                            {officer.appearances?.length || 0}
                          </span>
                        </td>
                        <td className="py-3 px-4 max-w-xs">
                          {editingOfficer === officer.id ? (
                            <textarea
                              value={editForm.notes}
                              onChange={(e) => setEditForm({ ...editForm, notes: e.target.value })}
                              className="w-full px-2 py-1 border rounded text-sm"
                              rows={2}
                              placeholder="Notes"
                            />
                          ) : (
                            <span className="text-sm text-gray-500 truncate block">
                              {officer.notes || '-'}
                            </span>
                          )}
                        </td>
                        <td className="py-3 px-4 text-right">
                          {editingOfficer === officer.id ? (
                            <div className="flex items-center justify-end gap-2">
                              <button
                                onClick={handleSaveEdit}
                                className="p-2 text-green-600 hover:bg-green-50 rounded"
                              >
                                <Save className="h-4 w-4" />
                              </button>
                              <button
                                onClick={() => setEditingOfficer(null)}
                                className="p-2 text-gray-600 hover:bg-gray-100 rounded"
                              >
                                <X className="h-4 w-4" />
                              </button>
                            </div>
                          ) : (
                            <div className="flex items-center justify-end gap-2">
                              <button
                                onClick={() => handleStartEdit(officer)}
                                className="p-2 text-blue-600 hover:bg-blue-50 rounded"
                                title="Edit"
                              >
                                <Edit2 className="h-4 w-4" />
                              </button>
                              <button
                                onClick={() => handleDelete(officer.id)}
                                className="p-2 text-red-600 hover:bg-red-50 rounded"
                                title="Delete"
                              >
                                <Trash2 className="h-4 w-4" />
                              </button>
                            </div>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex items-center justify-between px-4 py-3 border-t bg-gray-50">
                <div className="text-sm text-gray-600">
                  Showing {((currentPage - 1) * ITEMS_PER_PAGE) + 1} to{' '}
                  {Math.min(currentPage * ITEMS_PER_PAGE, totalOfficers)} of {totalOfficers}
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
                    disabled={currentPage === 1}
                    className="p-2 rounded border bg-white hover:bg-gray-50 disabled:opacity-50"
                  >
                    <ChevronLeft className="h-4 w-4" />
                  </button>
                  <span className="text-sm text-gray-600">
                    Page {currentPage} of {totalPages}
                  </span>
                  <button
                    onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))}
                    disabled={currentPage === totalPages}
                    className="p-2 rounded border bg-white hover:bg-gray-50 disabled:opacity-50"
                  >
                    <ChevronRight className="h-4 w-4" />
                  </button>
                </div>
              </div>
            )}
          </Card>
            </>
          )}
        </div>
      </div>
    </PasswordGate>
  );
};

export default AdminPage;

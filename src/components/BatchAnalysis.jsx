import { useState, useEffect, useCallback, useRef } from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import {
  Shield, RefreshCw, Play, AlertTriangle, CheckCircle, XCircle,
  Loader2, Users, ChevronDown, ChevronUp
} from 'lucide-react';
import { API_BASE, fetchWithErrorHandling } from '../utils/api';
import { UI, BATCH_ANALYSIS, logger } from '../utils/constants';

// Polling configuration with exponential backoff
const INITIAL_POLL_INTERVAL = UI.POLL_INTERVAL_MS;
const MAX_POLL_INTERVAL = 10000; // 10 seconds max
const BACKOFF_MULTIPLIER = 1.5;

const BatchAnalysis = () => {
  const [pending, setPending] = useState([]);
  const [loading, setLoading] = useState(false);
  const [selected, setSelected] = useState(new Set());
  const [batchId, setBatchId] = useState(null);
  const [batchProgress, setBatchProgress] = useState(null);
  const [error, setError] = useState(null);
  const [expanded, setExpanded] = useState(true);

  // Ref to track if batch is still in progress (avoids stale closure in interval)
  const batchInProgressRef = useRef(false);
  // Ref to track current poll interval for backoff
  const pollIntervalRef = useRef(INITIAL_POLL_INTERVAL);
  // Ref to track consecutive errors for backoff
  const consecutiveErrorsRef = useRef(0);

  // Fetch pending appearances
  const fetchPending = useCallback(async () => {
    setLoading(true);
    try {
      const data = await fetchWithErrorHandling(`${API_BASE}/appearances/pending-analysis?limit=${BATCH_ANALYSIS.PENDING_LIMIT}`);
      setPending(data.appearances || []);
      setError(null);
    } catch (err) {
      setError(`Failed to fetch pending appearances: ${err.message}`);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchPending();
  }, [fetchPending]);

  // Poll for batch progress with exponential backoff
  // Uses setTimeout chain instead of setInterval for dynamic intervals
  useEffect(() => {
    if (!batchId) {
      // Clean up ref when batchId is cleared to prevent stale polling
      batchInProgressRef.current = false;
      return;
    }

    batchInProgressRef.current = true;
    pollIntervalRef.current = INITIAL_POLL_INTERVAL;
    consecutiveErrorsRef.current = 0;
    let timeoutId = null;

    const pollProgress = async () => {
      // Check ref instead of state to avoid stale closure
      if (!batchInProgressRef.current) return;

      try {
        const data = await fetchWithErrorHandling(`${API_BASE}/appearances/batch-status/${batchId}`);
        setBatchProgress(data);

        // Reset backoff on success
        consecutiveErrorsRef.current = 0;
        pollIntervalRef.current = INITIAL_POLL_INTERVAL;

        if (!data.in_progress) {
          // Batch complete - stop polling and refresh pending list
          batchInProgressRef.current = false;
          fetchPending();
          return;
        }
      } catch (err) {
        logger.warn('Failed to fetch batch progress:', err);
        // Apply exponential backoff on errors
        consecutiveErrorsRef.current += 1;
        pollIntervalRef.current = Math.min(
          pollIntervalRef.current * BACKOFF_MULTIPLIER,
          MAX_POLL_INTERVAL
        );
      }

      // Schedule next poll with current interval (may have been increased by backoff)
      if (batchInProgressRef.current) {
        timeoutId = setTimeout(pollProgress, pollIntervalRef.current);
      }
    };

    // Initial poll
    pollProgress();

    return () => {
      if (timeoutId) clearTimeout(timeoutId);
      batchInProgressRef.current = false;
    };
  }, [batchId, fetchPending]);

  const handleSelectAll = () => {
    if (selected.size === pending.length) {
      setSelected(new Set());
    } else {
      setSelected(new Set(pending.map(p => p.id)));
    }
  };

  const handleToggleSelect = (id) => {
    const newSelected = new Set(selected);
    if (newSelected.has(id)) {
      newSelected.delete(id);
    } else {
      newSelected.add(id);
    }
    setSelected(newSelected);
  };

  const handleStartBatch = async (forceReanalyze = false) => {
    if (selected.size === 0) {
      setError('Please select appearances to analyze');
      return;
    }

    setError(null);
    setBatchProgress(null);

    try {
      const data = await fetchWithErrorHandling(`${API_BASE}/appearances/batch-analyze`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          appearance_ids: Array.from(selected),
          force_reanalyze: forceReanalyze
        })
      });

      if (data.status === 'batch_started') {
        setBatchId(data.batch_id);
        setBatchProgress({
          total: data.total_to_analyze,
          completed: 0,
          failed: 0,
          in_progress: true
        });
      } else if (data.status === 'no_work') {
        setError(data.message);
      } else {
        setError(data.detail || 'Failed to start batch analysis');
      }
    } catch (err) {
      setError(`Failed to start batch analysis: ${err.message}`);
    }
  };

  const progressPercent = batchProgress
    ? Math.round(((batchProgress.completed + batchProgress.failed) / batchProgress.total) * 100)
    : 0;

  return (
    <Card className="overflow-hidden">
      {/* Header */}
      <div
        className="p-4 bg-gradient-to-r from-purple-600 to-purple-700 text-white cursor-pointer"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Shield className="h-6 w-6" />
            <div>
              <h3 className="font-semibold text-lg">Batch Uniform Analysis</h3>
              <p className="text-purple-200 text-sm">
                Analyze multiple officer uniforms at once
              </p>
            </div>
          </div>
          {expanded ? (
            <ChevronUp className="h-5 w-5" />
          ) : (
            <ChevronDown className="h-5 w-5" />
          )}
        </div>
      </div>

      {expanded && (
        <div className="p-6 space-y-6">
          {/* Error Display */}
          {error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex items-start gap-3">
              <AlertTriangle className="h-5 w-5 text-red-500 flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-red-800 font-medium">Error</p>
                <p className="text-red-600 text-sm">{error}</p>
              </div>
              <button
                onClick={() => setError(null)}
                className="ml-auto text-red-400 hover:text-red-600"
              >
                &times;
              </button>
            </div>
          )}

          {/* Batch Progress */}
          {batchProgress && (
            <div className="bg-purple-50 border border-purple-200 rounded-lg p-4">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  {batchProgress.in_progress ? (
                    <Loader2 className="h-5 w-5 text-purple-600 animate-spin" />
                  ) : batchProgress.failed > 0 ? (
                    <AlertTriangle className="h-5 w-5 text-orange-500" />
                  ) : (
                    <CheckCircle className="h-5 w-5 text-green-500" />
                  )}
                  <span className="font-medium text-gray-900">
                    {batchProgress.in_progress
                      ? 'Analyzing uniforms...'
                      : 'Batch complete'}
                  </span>
                </div>
                <span className="text-sm text-gray-600">
                  {batchProgress.completed + batchProgress.failed} / {batchProgress.total}
                </span>
              </div>

              {/* Progress Bar */}
              <div className="w-full bg-purple-200 rounded-full h-3 overflow-hidden">
                <div
                  className={`h-full transition-all duration-300 ${
                    batchProgress.failed > 0 ? 'bg-orange-500' : 'bg-purple-600'
                  }`}
                  style={{ width: `${progressPercent}%` }}
                />
              </div>

              <div className="mt-3 flex items-center gap-4 text-sm">
                <span className="flex items-center gap-1 text-green-600">
                  <CheckCircle className="h-4 w-4" />
                  {batchProgress.completed} successful
                </span>
                {batchProgress.failed > 0 && (
                  <span className="flex items-center gap-1 text-red-600">
                    <XCircle className="h-4 w-4" />
                    {batchProgress.failed} failed
                  </span>
                )}
              </div>

              {/* Results */}
              {!batchProgress.in_progress && batchProgress.results?.length > 0 && (
                <div className="mt-4 pt-4 border-t border-purple-200">
                  <p className="text-xs font-medium text-gray-600 mb-2">Recent Results:</p>
                  <div className="space-y-1">
                    {batchProgress.results.slice(-BATCH_ANALYSIS.MAX_RESULTS_SHOWN).map((result, idx) => (
                      <div
                        key={idx}
                        className={`text-xs p-2 rounded ${
                          result.success
                            ? 'bg-green-100 text-green-800'
                            : 'bg-red-100 text-red-800'
                        }`}
                      >
                        Appearance #{result.appearance_id}:
                        {result.success
                          ? ` ${result.force || 'Unknown force'}`
                          : ` Error - ${result.error}`}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Pending Appearances */}
          <div>
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <Users className="h-5 w-5 text-gray-500" />
                <span className="font-medium text-gray-900">
                  Pending Analysis ({pending.length} appearances)
                </span>
              </div>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={fetchPending}
                  disabled={loading}
                >
                  {loading ? (
                    <RefreshCw className="h-4 w-4 animate-spin" />
                  ) : (
                    <RefreshCw className="h-4 w-4" />
                  )}
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleSelectAll}
                >
                  {selected.size === pending.length ? 'Deselect All' : 'Select All'}
                </Button>
              </div>
            </div>

            {pending.length === 0 ? (
              <div className="text-center py-8 text-gray-500">
                <CheckCircle className="h-12 w-12 mx-auto mb-3 text-green-500" />
                <p className="font-medium">All appearances analyzed!</p>
                <p className="text-sm mt-1">No pending uniform analyses found.</p>
              </div>
            ) : (
              <>
                {/* Selection List */}
                <div
                  className="border rounded-lg divide-y max-h-64 overflow-y-auto"
                  role="group"
                  aria-label="Pending appearances for analysis"
                >
                  {pending.map((appearance) => {
                    const officerName = appearance.badge_number || `Officer #${appearance.officer_id}`;
                    return (
                      <label
                        key={appearance.id}
                        className={`flex items-center gap-3 p-3 cursor-pointer hover:bg-gray-50 ${
                          selected.has(appearance.id) ? 'bg-purple-50' : ''
                        }`}
                      >
                        <input
                          type="checkbox"
                          checked={selected.has(appearance.id)}
                          onChange={() => handleToggleSelect(appearance.id)}
                          aria-label={`Select ${officerName} for analysis`}
                          className="w-4 h-4 rounded border-gray-300 text-purple-600 focus:ring-purple-500"
                        />
                        <div className="flex-1 min-w-0">
                          <div className="font-medium text-gray-900 text-sm">
                            {officerName}
                          </div>
                          <div className="text-xs text-gray-500">
                            Appearance #{appearance.id} | Media #{appearance.media_id}
                            {appearance.current_force && ` | ${appearance.current_force}`}
                          </div>
                        </div>
                      </label>
                    );
                  })}
                </div>

                {/* Action Buttons */}
                <div className="mt-4 flex items-center justify-between">
                  <span className="text-sm text-gray-600">
                    {selected.size} selected
                  </span>
                  <div className="flex items-center gap-2">
                    <Button
                      onClick={() => handleStartBatch(false)}
                      disabled={selected.size === 0 || batchProgress?.in_progress}
                      className="bg-purple-600 hover:bg-purple-700"
                    >
                      {batchProgress?.in_progress ? (
                        <>
                          <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                          Processing...
                        </>
                      ) : (
                        <>
                          <Play className="h-4 w-4 mr-2" />
                          Analyze {selected.size > 0 ? `(${selected.size})` : ''}
                        </>
                      )}
                    </Button>
                  </div>
                </div>

                {/* Cost Warning */}
                <p className="mt-3 text-xs text-gray-500">
                  Note: Each analysis uses the Claude Vision API (~$0.015 per image).
                  Select carefully to manage costs.
                </p>
              </>
            )}
          </div>
        </div>
      )}
    </Card>
  );
};

export default BatchAnalysis;

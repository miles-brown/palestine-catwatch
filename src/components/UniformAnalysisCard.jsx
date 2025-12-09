import { useState } from 'react';
import { Shield, Award, Radio, ChevronDown, ChevronUp, Loader2, AlertCircle, CheckCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// Force color coding
const FORCE_COLORS = {
  'Metropolitan Police Service': 'bg-blue-600',
  'City of London Police': 'bg-red-600',
  'British Transport Police': 'bg-purple-600',
  'default': 'bg-gray-600'
};

// Unit type badges
const UNIT_BADGES = {
  'TSG': { color: 'bg-red-700', label: 'TSG' },
  'TSG (Territorial Support Group)': { color: 'bg-red-700', label: 'TSG' },
  'FIT': { color: 'bg-blue-700', label: 'FIT' },
  'FIT (Forward Intelligence Team)': { color: 'bg-blue-700', label: 'FIT' },
  'Level 1 PSU': { color: 'bg-orange-600', label: 'L1 PSU' },
  'Level 2 PSU': { color: 'bg-yellow-600', label: 'L2 PSU' },
  'SCO19': { color: 'bg-black', label: 'SCO19' },
  'Standard': { color: 'bg-gray-500', label: 'Standard' },
  'default': { color: 'bg-gray-500', label: 'Unknown' }
};

// Equipment category icons
const CATEGORY_STYLES = {
  'defensive': { color: 'text-blue-500', bg: 'bg-blue-100' },
  'offensive': { color: 'text-red-500', bg: 'bg-red-100' },
  'restraint': { color: 'text-orange-500', bg: 'bg-orange-100' },
  'identification': { color: 'text-green-500', bg: 'bg-green-100' },
  'communication': { color: 'text-purple-500', bg: 'bg-purple-100' },
  'specialist': { color: 'text-gray-500', bg: 'bg-gray-100' }
};

const ConfidenceBadge = ({ confidence, small = false }) => {
  if (!confidence && confidence !== 0) return null;

  const percent = Math.round(confidence * 100);
  const colorClass = percent >= 80 ? 'bg-green-500' : percent >= 50 ? 'bg-yellow-500' : 'bg-red-500';

  return (
    <span className={`${colorClass} text-white rounded-full ${small ? 'text-[9px] px-1.5 py-0.5' : 'text-xs px-2 py-0.5'}`}>
      {percent}%
    </span>
  );
};

const UniformAnalysisCard = ({
  officerId,
  appearanceId,
  existingAnalysis = null,
  cropPath = null,
  compact = false,
  onAnalysisComplete = null
}) => {
  const [analysis, setAnalysis] = useState(existingAnalysis);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [expanded, setExpanded] = useState(false);

  const triggerAnalysis = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`${API_BASE}/appearances/${appearanceId}/analyze`, {
        method: 'POST'
      });

      const data = await response.json();

      if (data.status === 'analysis_started') {
        // Poll for results
        setTimeout(async () => {
          try {
            const uniformRes = await fetch(`${API_BASE}/officers/${officerId}/uniform`);
            const uniformData = await uniformRes.json();

            // Find the analysis for this appearance
            const thisAnalysis = uniformData.analyses?.find(a => a.appearance_id === appearanceId);
            if (thisAnalysis) {
              setAnalysis(thisAnalysis);
              if (onAnalysisComplete) onAnalysisComplete(thisAnalysis);
            }
          } catch (e) {
            console.error('Error fetching analysis results:', e);
          }
          setLoading(false);
        }, 5000); // Wait 5 seconds for analysis to complete
      } else if (data.status === 'already_analyzed') {
        // Fetch existing analysis
        const uniformRes = await fetch(`${API_BASE}/officers/${officerId}/uniform`);
        const uniformData = await uniformRes.json();
        const thisAnalysis = uniformData.analyses?.find(a => a.appearance_id === appearanceId);
        if (thisAnalysis) setAnalysis(thisAnalysis);
        setLoading(false);
      } else {
        setError(data.detail || 'Analysis failed');
        setLoading(false);
      }
    } catch (e) {
      setError(e.message);
      setLoading(false);
    }
  };

  // No analysis yet - show button
  if (!analysis) {
    return (
      <div className={`border rounded-lg p-3 ${compact ? 'bg-gray-50' : 'bg-white'}`}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-gray-600">
            <Shield className="h-4 w-4" />
            <span className="text-sm font-medium">Uniform Analysis</span>
          </div>

          <Button
            size="sm"
            variant="outline"
            onClick={triggerAnalysis}
            disabled={loading}
            className="text-xs"
          >
            {loading ? (
              <>
                <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                Analyzing...
              </>
            ) : (
              'Analyze Uniform'
            )}
          </Button>
        </div>

        {error && (
          <div className="mt-2 text-xs text-red-600 flex items-center gap-1">
            <AlertCircle className="h-3 w-3" />
            {error}
          </div>
        )}
      </div>
    );
  }

  const { analysis: analysisData, equipment } = analysis;
  const forceColor = FORCE_COLORS[analysisData?.detected_force] || FORCE_COLORS.default;
  const unitBadge = UNIT_BADGES[analysisData?.unit_type] || UNIT_BADGES.default;

  // Compact view for inline display
  if (compact && !expanded) {
    return (
      <div
        className="border rounded-lg p-2 bg-gray-50 cursor-pointer hover:bg-gray-100 transition-colors"
        onClick={() => setExpanded(true)}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 flex-wrap">
            {analysisData?.detected_force && (
              <span className={`${forceColor} text-white text-[10px] px-2 py-0.5 rounded`}>
                {analysisData.detected_force.split(' ').slice(0, 2).join(' ')}
              </span>
            )}
            {analysisData?.unit_type && (
              <span className={`${unitBadge.color} text-white text-[10px] px-2 py-0.5 rounded`}>
                {unitBadge.label}
              </span>
            )}
            {analysisData?.detected_rank && (
              <span className="text-[10px] text-gray-600">
                {analysisData.detected_rank}
              </span>
            )}
          </div>
          <ChevronDown className="h-3 w-3 text-gray-400" />
        </div>
      </div>
    );
  }

  // Full view
  return (
    <div className="border rounded-lg bg-white overflow-hidden">
      {/* Header */}
      <div
        className={`${forceColor} text-white p-3 cursor-pointer`}
        onClick={() => compact && setExpanded(!expanded)}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Shield className="h-5 w-5" />
            <span className="font-medium">
              {analysisData?.detected_force || 'Unknown Force'}
            </span>
            {analysisData?.force_confidence && (
              <ConfidenceBadge confidence={analysisData.force_confidence} small />
            )}
          </div>
          {compact && <ChevronUp className="h-4 w-4" />}
        </div>

        {/* Unit and Rank badges */}
        <div className="flex items-center gap-2 mt-2">
          {analysisData?.unit_type && (
            <span className={`${unitBadge.color} text-white text-xs px-2 py-0.5 rounded flex items-center gap-1`}>
              {unitBadge.label}
              <ConfidenceBadge confidence={analysisData.unit_confidence} small />
            </span>
          )}
          {analysisData?.detected_rank && (
            <span className="bg-white/20 text-white text-xs px-2 py-0.5 rounded flex items-center gap-1">
              <Award className="h-3 w-3" />
              {analysisData.detected_rank}
              <ConfidenceBadge confidence={analysisData.rank_confidence} small />
            </span>
          )}
        </div>
      </div>

      {/* Body */}
      <div className="p-3 space-y-3">
        {/* Shoulder Number */}
        {analysisData?.shoulder_number && (
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-gray-700">Shoulder #:</span>
            <span className="bg-yellow-100 text-yellow-800 font-mono text-sm px-2 py-0.5 rounded">
              {analysisData.shoulder_number}
            </span>
            <ConfidenceBadge confidence={analysisData.shoulder_number_confidence} small />
          </div>
        )}

        {/* Uniform Type */}
        {analysisData?.uniform_type && (
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-gray-700">Uniform:</span>
            <span className="text-sm text-gray-600 capitalize">
              {analysisData.uniform_type.replace(/_/g, ' ')}
            </span>
          </div>
        )}

        {/* Equipment List */}
        {equipment && equipment.length > 0 && (
          <div>
            <div className="text-sm font-medium text-gray-700 mb-2">Equipment Detected:</div>
            <div className="flex flex-wrap gap-1.5">
              {equipment.map((eq, idx) => {
                const style = CATEGORY_STYLES[eq.category] || CATEGORY_STYLES.specialist;
                return (
                  <span
                    key={idx}
                    className={`${style.bg} ${style.color} text-xs px-2 py-1 rounded flex items-center gap-1`}
                  >
                    {eq.name}
                    {eq.confidence && <ConfidenceBadge confidence={eq.confidence} small />}
                  </span>
                );
              })}
            </div>
          </div>
        )}

        {/* Force Indicators */}
        {analysisData?.force_indicators && analysisData.force_indicators.length > 0 && (
          <div className="text-xs text-gray-500 mt-2">
            <span className="font-medium">Identification clues: </span>
            {analysisData.force_indicators.join(', ')}
          </div>
        )}

        {/* Analysis timestamp */}
        {analysisData?.analyzed_at && (
          <div className="text-[10px] text-gray-400 flex items-center gap-1 pt-2 border-t">
            <CheckCircle className="h-3 w-3 text-green-500" />
            Analyzed {new Date(analysisData.analyzed_at).toLocaleDateString()}
          </div>
        )}

        {/* Re-analyze button */}
        <div className="pt-2">
          <Button
            size="sm"
            variant="ghost"
            onClick={triggerAnalysis}
            disabled={loading}
            className="text-xs text-gray-500 hover:text-gray-700"
          >
            {loading ? (
              <>
                <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                Re-analyzing...
              </>
            ) : (
              'Re-analyze'
            )}
          </Button>
        </div>
      </div>
    </div>
  );
};

export default UniformAnalysisCard;

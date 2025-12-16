import { useState, useEffect, useCallback, useMemo } from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import {
    Check, X, GitMerge, GitBranch, ChevronRight, AlertTriangle,
    Zap, User, CheckCircle, XCircle, Filter, Eye
} from 'lucide-react';
import MergeSuggestionCard from './MergeSuggestionCard';

let API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";
if (!API_BASE.startsWith("http")) {
    API_BASE = `https://${API_BASE}`;
}

// Helper to handle both absolute R2 URLs and relative API paths
const getImageUrl = (url) => {
    if (!url) return '';
    if (url.startsWith('http://') || url.startsWith('https://')) {
        return url;
    }
    return `${API_BASE}${url.startsWith('/') ? '' : '/'}${url}`;
};

/**
 * OfficerReviewPanel - Grid of officers for approval/rejection with merge functionality
 *
 * This component displays all detected officers from a media analysis and allows:
 * - Approving/rejecting officers as confirmed police
 * - Auto-merge suggestions when face similarity > 90%
 * - Manual merge selection by clicking multiple officers
 * - Quick approve/reject all buttons
 */
export default function OfficerReviewPanel({ mediaId, officers, onComplete, onBack }) {
    // Approval decisions: officer_id -> boolean
    const [decisions, setDecisions] = useState(() => {
        // Default: approve officers with confidence >= 80%
        return officers.reduce((acc, o) => ({
            ...acc,
            [o.officer_id || o.id]: (o.confidence || 0) >= 0.8
        }), {});
    });

    // Merge state
    const [mergeSuggestions, setMergeSuggestions] = useState([]);
    const [loadingSuggestions, setLoadingSuggestions] = useState(true);
    const [selectedForMerge, setSelectedForMerge] = useState([]);
    const [mergedGroups, setMergedGroups] = useState([]);
    const [showMergeSuggestions, setShowMergeSuggestions] = useState(true);

    // UI state
    const [mergeMode, setMergeMode] = useState(false);
    const [processing, setProcessing] = useState(false);

    // Fetch merge suggestions on mount
    useEffect(() => {
        const fetchSuggestions = async () => {
            try {
                const response = await fetch(`${API_BASE}/media/${mediaId}/merge-suggestions?threshold=0.85`);
                if (response.ok) {
                    const data = await response.json();
                    setMergeSuggestions(data.suggestions || []);
                }
            } catch (err) {
                console.error('Failed to fetch merge suggestions:', err);
            } finally {
                setLoadingSuggestions(false);
            }
        };

        if (mediaId) {
            fetchSuggestions();
        }
    }, [mediaId]);

    // Calculate approved count
    const approvedCount = useMemo(() => {
        return Object.values(decisions).filter(Boolean).length;
    }, [decisions]);

    // Get officers not in merged groups
    const unmergedOfficers = useMemo(() => {
        const mergedIds = new Set(mergedGroups.flatMap(g => g.officer_ids));
        return officers.filter(o => !mergedIds.has(o.officer_id || o.id));
    }, [officers, mergedGroups]);

    // Toggle approval for single officer
    const toggleApproval = useCallback((officerId) => {
        setDecisions(prev => ({
            ...prev,
            [officerId]: !prev[officerId]
        }));
    }, []);

    // Toggle merge selection
    const toggleMergeSelect = useCallback((officerId) => {
        setSelectedForMerge(prev => {
            if (prev.includes(officerId)) {
                return prev.filter(id => id !== officerId);
            }
            return [...prev, officerId];
        });
    }, []);

    // Approve all above threshold
    const handleApproveAllAbove = useCallback((threshold) => {
        setDecisions(
            officers.reduce((acc, o) => ({
                ...acc,
                [o.officer_id || o.id]: (o.confidence || 0) >= threshold
            }), {})
        );
    }, [officers]);

    // Reject all
    const handleRejectAll = useCallback(() => {
        setDecisions(
            officers.reduce((acc, o) => ({
                ...acc,
                [o.officer_id || o.id]: false
            }), {})
        );
    }, [officers]);

    // Handle merge suggestion acceptance
    const handleMergeAccept = useCallback(async (suggestion) => {
        try {
            setProcessing(true);
            const response = await fetch(`${API_BASE}/media/${mediaId}/officers/merge`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    officer_ids: [suggestion.officer_a_id, suggestion.officer_b_id],
                    confidence: suggestion.confidence,
                    auto_merged: suggestion.auto_merge
                })
            });

            if (response.ok) {
                // Add to merged groups
                setMergedGroups(prev => [...prev, {
                    id: `merge_${Date.now()}`,
                    primary_id: suggestion.officer_a_id,
                    officer_ids: [suggestion.officer_a_id, suggestion.officer_b_id],
                    confidence: suggestion.confidence
                }]);

                // Remove from suggestions
                setMergeSuggestions(prev =>
                    prev.filter(s =>
                        !(s.officer_a_id === suggestion.officer_a_id && s.officer_b_id === suggestion.officer_b_id)
                    )
                );
            }
        } catch (err) {
            console.error('Merge failed:', err);
        } finally {
            setProcessing(false);
        }
    }, [mediaId]);

    // Reject merge suggestion
    const handleMergeReject = useCallback((suggestion) => {
        setMergeSuggestions(prev =>
            prev.filter(s =>
                !(s.officer_a_id === suggestion.officer_a_id && s.officer_b_id === suggestion.officer_b_id)
            )
        );
    }, []);

    // Manual merge
    const handleManualMerge = useCallback(async () => {
        if (selectedForMerge.length < 2) return;

        try {
            setProcessing(true);
            const response = await fetch(`${API_BASE}/media/${mediaId}/officers/merge`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    officer_ids: selectedForMerge,
                    confidence: 0.0,
                    auto_merged: false
                })
            });

            if (response.ok) {
                setMergedGroups(prev => [...prev, {
                    id: `merge_${Date.now()}`,
                    primary_id: selectedForMerge[0],
                    officer_ids: [...selectedForMerge],
                    confidence: 0.0
                }]);
                setSelectedForMerge([]);
                setMergeMode(false);
            }
        } catch (err) {
            console.error('Manual merge failed:', err);
        } finally {
            setProcessing(false);
        }
    }, [selectedForMerge, mediaId]);

    // Complete review and continue
    const handleComplete = useCallback(() => {
        // Build verified officers list
        const verifiedOfficers = officers
            .map(o => ({
                ...o,
                verified: decisions[o.officer_id || o.id] || false
            }))
            .filter(o => o.verified);

        onComplete({
            decisions,
            mergedGroups,
            verifiedOfficers
        });
    }, [officers, decisions, mergedGroups, onComplete]);

    // Get confidence color
    const getConfidenceColor = (confidence) => {
        if (confidence >= 0.8) return 'text-green-400';
        if (confidence >= 0.6) return 'text-yellow-400';
        return 'text-red-400';
    };

    // Officer Review Card Component
    const OfficerReviewCard = ({ officer }) => {
        const officerId = officer.officer_id || officer.id;
        const isApproved = decisions[officerId];
        const isSelected = selectedForMerge.includes(officerId);
        const confidence = officer.confidence || 0;

        const cropUrl = officer.face_crop_path || officer.body_crop_path || officer.image_crop_path;

        return (
            <Card
                className={`relative overflow-hidden transition-all duration-200 cursor-pointer
                    ${isApproved
                        ? 'border-2 border-green-500 bg-slate-800'
                        : 'border-2 border-slate-700 bg-slate-900'}
                    ${isSelected ? 'ring-2 ring-blue-500 ring-offset-2 ring-offset-slate-950' : ''}
                    ${mergeMode ? 'hover:ring-2 hover:ring-blue-400' : 'hover:border-slate-500'}
                `}
                onClick={() => mergeMode ? toggleMergeSelect(officerId) : toggleApproval(officerId)}
            >
                {/* Image */}
                <div className="aspect-square bg-slate-800 relative">
                    {cropUrl ? (
                        <img
                            src={cropUrl}
                            alt={`Officer ${officerId}`}
                            className="w-full h-full object-cover"
                        />
                    ) : (
                        <div className="w-full h-full flex items-center justify-center">
                            <User className="h-16 w-16 text-slate-600" />
                        </div>
                    )}

                    {/* Approval indicator */}
                    <div className={`absolute top-2 right-2 p-1.5 rounded-full
                        ${isApproved ? 'bg-green-500' : 'bg-slate-700'}`}>
                        {isApproved ? (
                            <Check className="h-4 w-4 text-white" />
                        ) : (
                            <X className="h-4 w-4 text-slate-400" />
                        )}
                    </div>

                    {/* Merge select indicator */}
                    {mergeMode && (
                        <div className={`absolute top-2 left-2 p-1.5 rounded-full
                            ${isSelected ? 'bg-blue-500' : 'bg-slate-700/80'}`}>
                            <GitMerge className={`h-4 w-4 ${isSelected ? 'text-white' : 'text-slate-400'}`} />
                        </div>
                    )}

                    {/* Confidence badge */}
                    <div className="absolute bottom-2 left-2 bg-black/75 px-2 py-1 rounded">
                        <span className={`text-xs font-bold ${getConfidenceColor(confidence)}`}>
                            {(confidence * 100).toFixed(0)}%
                        </span>
                    </div>
                </div>

                {/* Info */}
                <div className="p-3 space-y-1">
                    {/* Badge number */}
                    <div className="flex items-center justify-between">
                        <span className="text-xs text-slate-500 uppercase">Badge</span>
                        <span className="text-sm font-mono text-white">
                            {officer.ocr_badge_result || officer.badge_override || 'Unknown'}
                        </span>
                    </div>

                    {/* Name */}
                    {(officer.ocr_name_result || officer.ai_name || officer.name_override) && (
                        <div className="flex items-center justify-between">
                            <span className="text-xs text-slate-500 uppercase">Name</span>
                            <span className="text-sm text-white truncate max-w-[120px]">
                                {officer.name_override || officer.ocr_name_result || officer.ai_name}
                            </span>
                        </div>
                    )}

                    {/* Timestamp */}
                    {officer.timestamp && (
                        <div className="text-xs text-slate-500">
                            @ {officer.timestamp}
                        </div>
                    )}
                </div>
            </Card>
        );
    };

    // Merged Group Card
    const MergedGroupCard = ({ group }) => {
        const primaryOfficer = officers.find(o => (o.officer_id || o.id) === group.primary_id);
        const groupOfficers = officers.filter(o => group.officer_ids.includes(o.officer_id || o.id));

        return (
            <Card className="border-2 border-blue-500/50 bg-slate-800 overflow-hidden">
                <div className="p-3 bg-blue-500/10 border-b border-blue-500/30 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                        <GitMerge className="h-4 w-4 text-blue-400" />
                        <span className="text-sm font-bold text-blue-400">
                            Merged ({groupOfficers.length} officers)
                        </span>
                    </div>
                    <span className="text-xs text-slate-400">
                        {(group.confidence * 100).toFixed(0)}% match
                    </span>
                </div>

                <div className="p-3">
                    {/* Primary photo */}
                    <div className="aspect-square bg-slate-700 rounded-lg overflow-hidden mb-3">
                        {primaryOfficer && (primaryOfficer.face_crop_path || primaryOfficer.image_crop_path) ? (
                            <img
                                src={getImageUrl(primaryOfficer.face_crop_path || primaryOfficer.image_crop_path)}
                                alt="Primary officer"
                                className="w-full h-full object-cover"
                            />
                        ) : (
                            <div className="w-full h-full flex items-center justify-center">
                                <User className="h-12 w-12 text-slate-600" />
                            </div>
                        )}
                    </div>

                    {/* Thumbnails of merged officers */}
                    <div className="flex gap-1 overflow-x-auto pb-2">
                        {groupOfficers.map((o, idx) => (
                            <div
                                key={o.officer_id || o.id}
                                className="flex-shrink-0 w-10 h-10 rounded border border-slate-600 overflow-hidden"
                            >
                                {(o.face_crop_path || o.image_crop_path) ? (
                                    <img
                                        src={getImageUrl(o.face_crop_path || o.image_crop_path)}
                                        alt={`Officer ${idx + 1}`}
                                        className="w-full h-full object-cover"
                                    />
                                ) : (
                                    <div className="w-full h-full bg-slate-700 flex items-center justify-center">
                                        <User className="h-4 w-4 text-slate-500" />
                                    </div>
                                )}
                            </div>
                        ))}
                    </div>

                    {/* Badge info */}
                    <div className="text-sm font-mono text-white">
                        {primaryOfficer?.ocr_badge_result || primaryOfficer?.badge_override || 'Unknown Badge'}
                    </div>
                </div>
            </Card>
        );
    };

    return (
        <div className="min-h-screen bg-slate-950 text-slate-200 p-4 md:p-6">
            <div className="max-w-7xl mx-auto">
                {/* Header */}
                <div className="text-center mb-8">
                    <h1 className="text-2xl md:text-3xl font-bold text-white mb-2">
                        Officer Verification
                    </h1>
                    <p className="text-slate-400">
                        Review detected officers, merge duplicates, and confirm identifications
                    </p>
                </div>

                {/* Merge Suggestions */}
                {showMergeSuggestions && mergeSuggestions.length > 0 && (
                    <div className="mb-8">
                        <div className="flex items-center justify-between mb-4">
                            <h2 className="text-lg font-bold text-yellow-400 flex items-center gap-2">
                                <Zap className="h-5 w-5" />
                                Merge Suggestions ({mergeSuggestions.length})
                            </h2>
                            <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => setShowMergeSuggestions(false)}
                                className="text-slate-400 hover:text-slate-200"
                            >
                                Dismiss All
                            </Button>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            {mergeSuggestions.slice(0, 4).map((suggestion, idx) => (
                                <MergeSuggestionCard
                                    key={idx}
                                    suggestion={suggestion}
                                    officers={officers}
                                    onAccept={() => handleMergeAccept(suggestion)}
                                    onReject={() => handleMergeReject(suggestion)}
                                    disabled={processing}
                                />
                            ))}
                        </div>

                        {mergeSuggestions.length > 4 && (
                            <p className="text-sm text-slate-500 mt-2 text-center">
                                +{mergeSuggestions.length - 4} more suggestions
                            </p>
                        )}
                    </div>
                )}

                {/* Manual Merge Selection Bar */}
                {selectedForMerge.length > 0 && (
                    <div className="sticky top-4 z-10 mb-6 p-4 bg-blue-900/50 border border-blue-500 rounded-xl flex flex-col sm:flex-row items-center justify-between gap-3">
                        <div className="flex items-center gap-3">
                            <GitMerge className="h-5 w-5 text-blue-400" />
                            <span className="text-blue-200">
                                {selectedForMerge.length} officers selected for merge
                            </span>
                        </div>
                        <div className="flex gap-2">
                            <Button
                                variant="ghost"
                                onClick={() => {
                                    setSelectedForMerge([]);
                                    setMergeMode(false);
                                }}
                                className="text-blue-300 hover:text-blue-100"
                            >
                                Cancel
                            </Button>
                            <Button
                                onClick={handleManualMerge}
                                className="bg-blue-600 hover:bg-blue-500"
                                disabled={selectedForMerge.length < 2 || processing}
                            >
                                Merge Selected ({selectedForMerge.length})
                            </Button>
                        </div>
                    </div>
                )}

                {/* Quick Actions */}
                <div className="flex flex-wrap gap-3 mb-6 justify-center">
                    <Button
                        onClick={() => handleApproveAllAbove(0.8)}
                        variant="outline"
                        className="border-green-500/50 text-green-400 hover:bg-green-500/20"
                    >
                        <CheckCircle className="h-4 w-4 mr-2" />
                        Approve All 80%+
                    </Button>
                    <Button
                        onClick={() => handleApproveAllAbove(0.6)}
                        variant="outline"
                        className="border-yellow-500/50 text-yellow-400 hover:bg-yellow-500/20"
                    >
                        Approve All 60%+
                    </Button>
                    <Button
                        onClick={handleRejectAll}
                        variant="ghost"
                        className="text-red-400 hover:bg-red-500/20"
                    >
                        <XCircle className="h-4 w-4 mr-2" />
                        Reject All
                    </Button>
                    <div className="w-px h-8 bg-slate-700 hidden sm:block" />
                    <Button
                        variant={mergeMode ? "default" : "outline"}
                        className={mergeMode
                            ? "bg-blue-600 hover:bg-blue-500"
                            : "border-blue-500/50 text-blue-400 hover:bg-blue-500/20"}
                        onClick={() => {
                            setMergeMode(!mergeMode);
                            if (mergeMode) setSelectedForMerge([]);
                        }}
                    >
                        <GitMerge className="h-4 w-4 mr-2" />
                        {mergeMode ? 'Exit Merge Mode' : 'Manual Merge'}
                    </Button>
                </div>

                {/* Merged Groups */}
                {mergedGroups.length > 0 && (
                    <div className="mb-8">
                        <h3 className="text-sm font-bold text-green-400 uppercase mb-4 flex items-center gap-2">
                            <GitBranch className="h-4 w-4" />
                            Merged Officers ({mergedGroups.length})
                        </h3>
                        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
                            {mergedGroups.map((group) => (
                                <MergedGroupCard key={group.id} group={group} />
                            ))}
                        </div>
                    </div>
                )}

                {/* Officer Grid */}
                <div className="mb-8">
                    {mergeMode && (
                        <p className="text-sm text-blue-400 mb-4 text-center">
                            Click officers you believe are the same person to merge them
                        </p>
                    )}

                    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4">
                        {unmergedOfficers.map((officer) => (
                            <OfficerReviewCard
                                key={officer.officer_id || officer.id || officer.appearance_id}
                                officer={officer}
                            />
                        ))}
                    </div>

                    {unmergedOfficers.length === 0 && (
                        <div className="text-center py-12 text-slate-500">
                            <User className="h-16 w-16 mx-auto mb-4 opacity-50" />
                            <p>No officers to review</p>
                        </div>
                    )}
                </div>

                {/* Footer */}
                <div className="sticky bottom-0 bg-slate-950/95 backdrop-blur border-t border-slate-800 -mx-4 md:-mx-6 px-4 md:px-6 py-4">
                    <div className="max-w-7xl mx-auto flex flex-col sm:flex-row justify-between items-center gap-4">
                        <div className="text-center sm:text-left">
                            <div className="text-2xl font-bold text-white">
                                {approvedCount} <span className="text-slate-500 text-lg font-normal">of {officers.length} approved</span>
                            </div>
                            <div className="text-sm text-slate-400">
                                {mergedGroups.length} merge groups created
                            </div>
                        </div>

                        <div className="flex gap-3">
                            {onBack && (
                                <Button
                                    variant="ghost"
                                    onClick={onBack}
                                    className="text-slate-400"
                                >
                                    Back
                                </Button>
                            )}
                            <Button
                                onClick={handleComplete}
                                className="bg-green-600 hover:bg-green-500 px-8"
                                disabled={approvedCount === 0 || processing}
                                size="lg"
                            >
                                Continue to Editing
                                <ChevronRight className="h-5 w-5 ml-2" />
                            </Button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}

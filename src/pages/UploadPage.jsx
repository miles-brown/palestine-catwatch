import { useState, useEffect, useCallback } from 'react';
import { Upload, FileVideo, Image as ImageIcon, CheckCircle, AlertCircle, Link as LinkIcon, FileUp, List, Loader2, X, Users, Edit3, FileText, ArrowRight, ArrowLeft } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import IngestQuestionnaire from '@/components/IngestQuestionnaire';
import LiveAnalysis from '@/components/LiveAnalysis';
import OfficerReviewPanel from '@/components/OfficerReviewPanel';
import OfficerDetailEditor from '@/components/OfficerDetailEditor';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/context/AuthContext';
import Turnstile from '@/components/Turnstile';
import { API_BASE, getMediaUrl } from '../utils/api';

// Use shared getMediaUrl for image URLs (handles R2 and local paths)
const getImageUrl = (url) => getMediaUrl(url) || '';

// Helper to format error messages consistently
const formatErrorMessage = (error) => {
    return typeof error === 'object' ? JSON.stringify(error) : String(error);
};

const UploadPage = () => {
    const navigate = useNavigate();
    const { isAuthenticated, loading } = useAuth();

    // Redirect to login if not authenticated
    useEffect(() => {
        if (!loading && !isAuthenticated) {
            navigate('/login', { state: { from: '/upload' } });
        }
    }, [isAuthenticated, loading, navigate]);

    // Multi-stage workflow state
    // Stages: 'upload' | 'analysis' | 'review' | 'details' | 'preview'
    const [currentStage, setCurrentStage] = useState('upload');
    const [mediaId, setMediaId] = useState(null);
    const [officers, setOfficers] = useState([]);
    const [approvedOfficers, setApprovedOfficers] = useState([]);

    // Shared State
    const [activeTab, setActiveTab] = useState('upload'); // 'upload' | 'link' | 'bulk'
    const [protests, setProtests] = useState([]);
    const [submitStatus, setSubmitStatus] = useState(null); // 'success' | 'error' | 'loading'
    const [message, setMessage] = useState('');
    const [liveTaskId, setLiveTaskId] = useState(null); // If set, shows LiveAnalysis

    // Upload State
    const [file, setFile] = useState(null);
    const [mediaType, setMediaType] = useState('image');

    // Bulk Import State
    const [bulkUrls, setBulkUrls] = useState('');
    const [bulkResults, setBulkResults] = useState(null);

    // Turnstile State
    const [turnstileToken, setTurnstileToken] = useState(null);

    // Stage definitions for progress indicator
    const stages = [
        { id: 'upload', label: 'Upload', icon: Upload },
        { id: 'analysis', label: 'Analysis', icon: Loader2 },
        { id: 'review', label: 'Review Officers', icon: Users },
        { id: 'details', label: 'Edit Details', icon: Edit3 },
        { id: 'preview', label: 'Report', icon: FileText }
    ];

    // Fetch officers when entering review stage
    const fetchOfficers = useCallback(async (id) => {
        try {
            const response = await fetch(`${API_BASE}/media/${id}/officers/pending`);
            if (response.ok) {
                const data = await response.json();
                setOfficers(data.officers || []);
            } else {
                // Fallback to regular officers endpoint
                const fallbackResponse = await fetch(`${API_BASE}/media/${id}/officers`);
                if (fallbackResponse.ok) {
                    const data = await fallbackResponse.json();
                    setOfficers(data);
                }
            }
        } catch (error) {
            console.error('Failed to fetch officers:', error);
            // Try fallback
            try {
                const fallbackResponse = await fetch(`${API_BASE}/media/${id}/officers`);
                if (fallbackResponse.ok) {
                    const data = await fallbackResponse.json();
                    setOfficers(data);
                }
            } catch (e) {
                console.error('Fallback also failed:', e);
            }
        }
    }, []);

    // Handle stage transitions
    const handleAnalysisComplete = useCallback(async (id, approvedCandidates = null) => {
        if (id) {
            setMediaId(id);
            setLiveTaskId(null);

            console.log(`[handleAnalysisComplete] Media ID: ${id}, Candidates: ${approvedCandidates?.length || 0}`);

            // Store approved candidates from live analysis
            if (approvedCandidates && approvedCandidates.length > 0) {
                console.log(`[handleAnalysisComplete] Storing ${approvedCandidates.length} pre-approved candidates`);

                // Transform candidates to officer format for consistency
                const transformedOfficers = approvedCandidates.map((c, idx) => ({
                    appearance_id: c.appearance_id || `temp-${idx}`,
                    officer_id: c.officer_id,
                    timestamp: c.timestamp,
                    confidence: c.confidence,
                    face_crop_path: c.face_url || c.image_url,
                    body_crop_path: c.body_url,
                    image_crop_path: c.image_url,
                    badge_override: c.badge || null,
                    name_override: c.officer_name || null,
                    force_override: c.force || null,
                    rank_override: c.rank || null,
                    decision: c.decision,
                    reviewed: c.reviewed
                }));

                // Store these as the current officers - they'll be used if DB fetch fails
                setOfficers(transformedOfficers);

                // Also store approved ones for the final submit
                const approved = transformedOfficers.filter(o => o.decision === 'yes' || !o.reviewed);
                setApprovedOfficers(approved);
                console.log(`[handleAnalysisComplete] ${approved.length} officers approved/pending review`);
            }

            // Try to fetch from database as well (may have more complete data)
            try {
                const response = await fetch(`${API_BASE}/media/${id}/officers/pending`);
                if (response.ok) {
                    const data = await response.json();
                    if (data.officers && data.officers.length > 0) {
                        console.log(`[handleAnalysisComplete] Fetched ${data.officers.length} officers from database`);
                        // Merge database data with local candidates
                        setOfficers(data.officers);
                    } else {
                        console.log(`[handleAnalysisComplete] Database returned empty, using local candidates`);
                    }
                }
            } catch (error) {
                console.error('[handleAnalysisComplete] Failed to fetch from database:', error);
                // Keep using the local candidates set above
            }

            setCurrentStage('review');
        } else {
            console.error("[handleAnalysisComplete] No media ID returned from analysis");
            setLiveTaskId(null);
            setCurrentStage('upload');
        }
    }, []);

    const handleReviewComplete = useCallback((reviewResult) => {
        // reviewResult contains { decisions, mergedGroups, verifiedOfficers }
        const verified = reviewResult.verifiedOfficers || reviewResult;
        setApprovedOfficers(Array.isArray(verified) ? verified : []);
        setCurrentStage('details');
    }, []);

    const handleDetailsComplete = useCallback((editedOfficers) => {
        // Save all edits and move to report preview
        setApprovedOfficers(editedOfficers);
        setCurrentStage('preview');
    }, []);

    const handleFinalSubmit = useCallback(async () => {
        console.log(`[handleFinalSubmit] Starting with mediaId=${mediaId}, approvedOfficers=${approvedOfficers.length}`);

        // Save approved officers to database before navigating to report
        if (mediaId && approvedOfficers.length > 0) {
            try {
                // Build batch update request - filter out temporary IDs
                const updates = approvedOfficers
                    .filter(officer => {
                        const appId = officer.appearance_id || officer.id;
                        // Skip temporary IDs that aren't in the database
                        if (typeof appId === 'string' && appId.startsWith('temp-')) {
                            console.log(`[handleFinalSubmit] Skipping temporary appearance: ${appId}`);
                            return false;
                        }
                        return true;
                    })
                    .map(officer => ({
                        appearance_id: officer.appearance_id || officer.id,
                        verified: true,
                        badge_override: officer.badge_override || officer.badge || null,
                        name_override: officer.name_override || officer.officer_name || null,
                        force_override: officer.force_override || officer.force || null,
                        rank_override: officer.rank_override || officer.rank || null,
                        role_override: officer.role_override || officer.role || null,
                        notes: officer.notes || null
                    }));

                console.log(`[handleFinalSubmit] Sending ${updates.length} updates to database:`, updates);

                if (updates.length > 0) {
                    const response = await fetch(`${API_BASE}/media/${mediaId}/officers/batch-update`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({ updates })
                    });

                    if (!response.ok) {
                        const errorText = await response.text();
                        console.error('[handleFinalSubmit] Failed to save officer updates:', errorText);
                    } else {
                        const result = await response.json();
                        console.log(`[handleFinalSubmit] Successfully saved ${result.updated?.length || 0} officer updates`);
                    }
                } else {
                    console.log('[handleFinalSubmit] No valid updates to save');
                }
            } catch (error) {
                console.error('[handleFinalSubmit] Error saving officer updates:', error);
            }
        } else {
            console.log(`[handleFinalSubmit] Nothing to save - mediaId: ${mediaId}, officers: ${approvedOfficers.length}`);
        }

        // Navigate to the final report page
        navigate(`/report/${mediaId}`);
    }, [navigate, mediaId, approvedOfficers]);

    const handleBackToReview = useCallback(() => {
        setCurrentStage('review');
    }, []);

    const handleBackToDetails = useCallback(() => {
        setCurrentStage('details');
    }, []);

    // Fetch protests on mount
    useEffect(() => {
        fetch(`${API_BASE}/protests`)
            .then(res => res.json())
            .then(data => setProtests(data))
            .catch(err => console.error("Failed to fetch protests", err));
    }, []);

    // --- File Upload Logic ---
    const handleFileChange = (e) => {
        if (e.target.files && e.target.files[0]) {
            setFile(e.target.files[0]);
            setSubmitStatus(null);
            const type = e.target.files[0].type;
            if (type.startsWith('video/')) setMediaType('video');
            else if (type.startsWith('image/')) setMediaType('image');
        }
    };

    const handleDrop = (e) => {
        e.preventDefault();
        if (e.dataTransfer.files && e.dataTransfer.files[0]) {
            setFile(e.dataTransfer.files[0]);
            setSubmitStatus(null);
            const type = e.dataTransfer.files[0].type;
            if (type.startsWith('video/')) setMediaType('video');
            else if (type.startsWith('image/')) setMediaType('image');
        }
    };

    const handleFileUpload = async (e) => {
        e.preventDefault();
        if (!file) return;

        if (!turnstileToken) {
            setSubmitStatus('error');
            setMessage('Please complete the security check');
            return;
        }

        setSubmitStatus('loading');
        const formData = new FormData();
        formData.append('file', file);
        formData.append('type', mediaType);
        formData.append('protest_id', 1); // Default ID, should be selectable if we add dropdown here too
        formData.append('turnstile_token', turnstileToken);

        try {
            const response = await fetch(`${API_BASE}/upload`, {
                method: 'POST',
                body: formData,
            });
            if (!response.ok) throw new Error('Upload failed');
            const data = await response.json();
            setSubmitStatus('success');
            setMessage(`Upload successful! ID: ${data.media_id}. Processing started...`);
            setFile(null);

            // TODO: If we want upload to also trigger live analysis, backend upload endpoint needs to return task_id 
            // and trigger async processing with SIO. For now, we only implemented this for URL Ingest.

        } catch (error) {
            setSubmitStatus('error');
            setMessage('Failed to upload file. Please try again.');
        }
    };

    // --- Bulk Import Logic ---
    const handleBulkSubmit = async (e) => {
        e.preventDefault();

        if (!turnstileToken) {
            setSubmitStatus('error');
            setMessage('Please complete the security check');
            return;
        }

        // Parse URLs from textarea (one per line)
        const urls = bulkUrls
            .split('\n')
            .map(url => url.trim())
            .filter(url => url.length > 0 && (url.startsWith('http://') || url.startsWith('https://')));

        if (urls.length === 0) {
            setSubmitStatus('error');
            setMessage('Please enter at least one valid URL (must start with http:// or https://)');
            return;
        }

        if (urls.length > 10) {
            setSubmitStatus('error');
            setMessage('Maximum 10 URLs per batch. Please reduce the number of URLs.');
            return;
        }

        setSubmitStatus('loading');
        setBulkResults(null);

        try {
            const response = await fetch(`${API_BASE}/ingest/bulk`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    urls: urls,
                    protest_id: null,
                    answers: {}
                }),
            });

            if (!response.ok) {
                const errData = await response.json().catch(() => ({}));
                const errorMsg = formatErrorMessage(errData.detail || 'Bulk ingest failed');
                throw new Error(errorMsg);
            }

            const data = await response.json();
            setSubmitStatus('success');
            setMessage(data.message || `Queued ${urls.length} URLs for processing`);
            setBulkResults(data);

        } catch (error) {
            setSubmitStatus('error');
            setMessage(`${error.message || 'Bulk import failed'}`);
        }
    };

    // --- URL Ingest Logic ---
    const handleUrlSubmit = async (answers) => {
        setSubmitStatus('loading');
        try {
            // Validate protest_id if provided
            let protestId = null;
            if (answers.protestId) {
                protestId = parseInt(answers.protestId, 10);
                if (isNaN(protestId)) {
                    throw new Error('Invalid protest ID');
                }
            }

            const response = await fetch(`${API_BASE}/ingest/url`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    url: answers.url,
                    protest_id: protestId,
                    answers: answers
                }),
            });

            if (!response.ok) {
                const errData = await response.json().catch(() => ({}));
                const errorMsg = formatErrorMessage(errData.detail || 'Ingest failed');
                throw new Error(errorMsg);
            }
            const data = await response.json();

            setSubmitStatus('success');
            setMessage(`Ingestion started! ${data.message}`);

            // Start Live Analysis and transition to analysis stage
            if (data.task_id) {
                setLiveTaskId(data.task_id);
                setCurrentStage('analysis');
            }

        } catch (error) {
            setSubmitStatus('error');
            // Only show API target URL in development mode for security
            const debugInfo = import.meta.env.DEV ? ` (Target: ${API_BASE})` : '';
            setMessage(`${error.message || 'Failed'}${debugInfo}`);
        }
    };

    // Show loading while checking auth
    if (loading) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-gray-50">
                <div className="animate-pulse text-gray-500">Checking access...</div>
            </div>
        );
    }

    // Don't render if not authenticated (redirect will happen via useEffect)
    if (!isAuthenticated) {
        return null;
    }

    // Stage Progress Indicator Component
    const StageProgress = () => {
        const currentIndex = stages.findIndex(s => s.id === currentStage);

        return (
            <div className="bg-slate-900 border-b border-slate-800 py-4 px-6">
                <div className="max-w-4xl mx-auto">
                    <div className="flex items-center justify-between">
                        {stages.map((stage, index) => {
                            const Icon = stage.icon;
                            const isActive = stage.id === currentStage;
                            const isCompleted = index < currentIndex;
                            const isUpcoming = index > currentIndex;

                            return (
                                <div key={stage.id} className="flex items-center">
                                    <div className={`flex flex-col items-center ${
                                        isUpcoming ? 'opacity-40' : ''
                                    }`}>
                                        <div className={`
                                            w-10 h-10 rounded-full flex items-center justify-center
                                            transition-all duration-300
                                            ${isActive
                                                ? 'bg-green-600 text-white ring-4 ring-green-600/30'
                                                : isCompleted
                                                    ? 'bg-green-600 text-white'
                                                    : 'bg-slate-700 text-slate-400'
                                            }
                                        `}>
                                            {isCompleted ? (
                                                <CheckCircle className="h-5 w-5" />
                                            ) : (
                                                <Icon className={`h-5 w-5 ${
                                                    isActive && stage.id === 'analysis' ? 'animate-spin' : ''
                                                }`} />
                                            )}
                                        </div>
                                        <span className={`mt-2 text-xs font-medium ${
                                            isActive ? 'text-green-400' : isCompleted ? 'text-slate-300' : 'text-slate-500'
                                        }`}>
                                            {stage.label}
                                        </span>
                                    </div>
                                    {index < stages.length - 1 && (
                                        <div className={`
                                            w-12 sm:w-20 h-0.5 mx-2
                                            ${index < currentIndex ? 'bg-green-600' : 'bg-slate-700'}
                                        `} />
                                    )}
                                </div>
                            );
                        })}
                    </div>
                </div>
            </div>
        );
    };

    // Analysis stage - show LiveAnalysis
    if (currentStage === 'analysis' || liveTaskId) {
        return (
            <div className="min-h-screen bg-slate-950">
                <StageProgress />
                <LiveAnalysis
                    taskId={liveTaskId}
                    onComplete={handleAnalysisComplete}
                />
            </div>
        );
    }

    // Review stage - show OfficerReviewPanel
    if (currentStage === 'review') {
        return (
            <div className="min-h-screen bg-slate-950">
                <StageProgress />
                <OfficerReviewPanel
                    mediaId={mediaId}
                    officers={officers}
                    onComplete={handleReviewComplete}
                    onBack={() => {
                        setCurrentStage('upload');
                        setMediaId(null);
                        setOfficers([]);
                    }}
                />
            </div>
        );
    }

    // Details stage - show OfficerDetailEditor
    if (currentStage === 'details') {
        return (
            <div className="min-h-screen bg-slate-950">
                <StageProgress />
                <OfficerDetailEditor
                    officers={approvedOfficers}
                    onComplete={handleDetailsComplete}
                    onBack={handleBackToReview}
                />
            </div>
        );
    }

    // Preview stage - show final report preview with submit button
    if (currentStage === 'preview') {
        return (
            <div className="min-h-screen bg-slate-950">
                <StageProgress />
                <div className="max-w-4xl mx-auto px-4 py-8">
                    <Card className="bg-slate-900 border-slate-700 p-8">
                        <div className="text-center mb-8">
                            <div className="w-16 h-16 mx-auto bg-green-600/20 rounded-full flex items-center justify-center mb-4">
                                <FileText className="h-8 w-8 text-green-400" />
                            </div>
                            <h2 className="text-2xl font-bold text-white mb-2">Report Ready</h2>
                            <p className="text-slate-400">
                                {approvedOfficers.length} officer{approvedOfficers.length !== 1 ? 's' : ''} verified and ready for report generation
                            </p>
                        </div>

                        {/* Officer Summary */}
                        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4 mb-8">
                            {approvedOfficers.slice(0, 8).map((officer, idx) => (
                                <div key={officer.officer_id || officer.id || idx}
                                     className="bg-slate-800 rounded-lg overflow-hidden">
                                    <div className="aspect-square bg-slate-700">
                                        {(officer.face_crop_path || officer.body_crop_path) ? (
                                            <img
                                                src={getImageUrl(officer.face_crop_path || officer.body_crop_path)}
                                                alt={`Officer ${idx + 1}`}
                                                className="w-full h-full object-cover"
                                            />
                                        ) : (
                                            <div className="w-full h-full flex items-center justify-center text-slate-500">
                                                <Users className="h-8 w-8" />
                                            </div>
                                        )}
                                    </div>
                                    <div className="p-2 text-center">
                                        <p className="text-xs text-slate-400 truncate">
                                            {officer.name_override || officer.name || officer.badge_override || officer.badge || `Officer #${idx + 1}`}
                                        </p>
                                    </div>
                                </div>
                            ))}
                            {approvedOfficers.length > 8 && (
                                <div className="bg-slate-800 rounded-lg flex items-center justify-center aspect-square">
                                    <span className="text-slate-400 text-lg font-medium">
                                        +{approvedOfficers.length - 8} more
                                    </span>
                                </div>
                            )}
                        </div>

                        {/* Actions */}
                        <div className="flex gap-4">
                            <Button
                                variant="outline"
                                onClick={handleBackToDetails}
                                className="flex-1 border-slate-600 text-slate-300 hover:bg-slate-800"
                            >
                                <ArrowLeft className="h-4 w-4 mr-2" />
                                Back to Edit
                            </Button>
                            <Button
                                onClick={handleFinalSubmit}
                                className="flex-1 bg-green-600 hover:bg-green-500 text-white"
                            >
                                Generate Final Report
                                <ArrowRight className="h-4 w-4 ml-2" />
                            </Button>
                        </div>
                    </Card>
                </div>
            </div>
        );
    }

    return (
        <div className="max-w-3xl mx-auto px-4 py-12">
            <div className="text-center mb-8">
                <h1 className="text-3xl font-bold text-gray-900 mb-2">Submit Evidence</h1>
                <p className="text-gray-600">
                    Upload footage or link to external media for AI analysis.
                </p>
            </div>

            {/* Tabs */}
            <div className="flex justify-center mb-8">
                <div className="bg-white p-1 rounded-xl shadow-sm border border-gray-200 inline-flex flex-wrap justify-center">
                    <button
                        onClick={() => { setActiveTab('upload'); setSubmitStatus(null); setMessage(''); setBulkResults(null); }}
                        className={`px-4 sm:px-6 py-2 rounded-lg font-medium flex items-center gap-2 transition-colors ${activeTab === 'upload' ? 'bg-green-100 text-green-800' : 'text-gray-600 hover:bg-gray-50'
                            }`}
                    >
                        <FileUp className="h-4 w-4" />
                        <span className="hidden sm:inline">Upload File</span>
                        <span className="sm:hidden">Upload</span>
                    </button>
                    <button
                        onClick={() => { setActiveTab('link'); setSubmitStatus(null); setMessage(''); setBulkResults(null); }}
                        className={`px-4 sm:px-6 py-2 rounded-lg font-medium flex items-center gap-2 transition-colors ${activeTab === 'link' ? 'bg-green-100 text-green-800' : 'text-gray-600 hover:bg-gray-50'
                            }`}
                    >
                        <LinkIcon className="h-4 w-4" />
                        <span className="hidden sm:inline">Web Link</span>
                        <span className="sm:hidden">Link</span>
                    </button>
                    <button
                        onClick={() => { setActiveTab('bulk'); setSubmitStatus(null); setMessage(''); setBulkResults(null); }}
                        className={`px-4 sm:px-6 py-2 rounded-lg font-medium flex items-center gap-2 transition-colors ${activeTab === 'bulk' ? 'bg-green-100 text-green-800' : 'text-gray-600 hover:bg-gray-50'
                            }`}
                    >
                        <List className="h-4 w-4" />
                        <span className="hidden sm:inline">Bulk Import</span>
                        <span className="sm:hidden">Bulk</span>
                    </button>
                </div>
            </div>

            <Card className="p-8">
                {/* Status Message */}
                {submitStatus && submitStatus !== 'loading' && (
                    <div className={`mb-6 p-4 rounded-lg flex items-center gap-2 ${submitStatus === 'success' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                        {submitStatus === 'success' ? <CheckCircle className="h-5 w-5" /> : <AlertCircle className="h-5 w-5" />}
                        {message}
                    </div>
                )}

                {activeTab === 'upload' ? (
                    <form onSubmit={handleFileUpload} className="space-y-6">
                        {/* Drag & Drop Zone */}
                        <div
                            className={`border-2 border-dashed rounded-xl p-12 text-center transition-colors ${file ? 'border-green-500 bg-green-50' : 'border-gray-300 hover:border-gray-400'
                                }`}
                            onDragOver={(e) => e.preventDefault()}
                            onDrop={handleDrop}
                        >
                            <input
                                type="file"
                                id="file-upload"
                                className="hidden"
                                onChange={handleFileChange}
                                accept="image/*,video/*"
                            />

                            <label htmlFor="file-upload" className="cursor-pointer flex flex-col items-center">
                                {file ? (
                                    <>
                                        {mediaType === 'video' ? (
                                            <FileVideo className="h-16 w-16 text-green-600 mb-4" />
                                        ) : (
                                            <ImageIcon className="h-16 w-16 text-green-600 mb-4" />
                                        )}
                                        <span className="text-lg font-medium text-gray-900">{file.name}</span>
                                        <span className="text-sm text-gray-500 mt-1">{(file.size / 1024 / 1024).toFixed(2)} MB</span>
                                    </>
                                ) : (
                                    <>
                                        <Upload className="h-16 w-16 text-gray-400 mb-4" />
                                        <span className="text-lg font-medium text-gray-900">
                                            Click to upload or drag and drop
                                        </span>
                                        <span className="text-sm text-gray-500 mt-1">
                                            MP4, JPG, PNG (Max 100MB)
                                        </span>
                                    </>
                                )}
                            </label>
                        </div>

                        {/* Media Type Selection */}
                        <div className="flex justify-center gap-6">
                            <label className="flex items-center gap-2 cursor-pointer">
                                <input
                                    type="radio"
                                    name="type"
                                    value="image"
                                    checked={mediaType === 'image'}
                                    onChange={(e) => setMediaType(e.target.value)}
                                    className="w-4 h-4 text-green-600"
                                />
                                <span className="text-gray-700">Photo</span>
                            </label>
                            <label className="flex items-center gap-2 cursor-pointer">
                                <input
                                    type="radio"
                                    name="type"
                                    value="video"
                                    checked={mediaType === 'video'}
                                    onChange={(e) => setMediaType(e.target.value)}
                                    className="w-4 h-4 text-green-600"
                                />
                                <span className="text-gray-700">Video</span>
                            </label>
                        </div>

                        {/* Turnstile CAPTCHA */}
                        <div className="py-2 flex justify-center">
                            <Turnstile
                                onVerify={(token) => setTurnstileToken(token)}
                                onExpire={() => setTurnstileToken(null)}
                                onError={() => {
                                    setSubmitStatus('error');
                                    setMessage('Security check failed. Please try again.');
                                }}
                                theme="light"
                            />
                        </div>

                        <Button
                            type="submit"
                            className="w-full bg-green-700 hover:bg-green-800 text-white py-6 text-lg"
                            disabled={!file || submitStatus === 'loading' || !turnstileToken}
                        >
                            {submitStatus === 'loading' ? 'Uploading...' : 'Submit Evidence'}
                        </Button>
                    </form>
                ) : activeTab === 'link' ? (
                    // Ingest URL Tab
                    <IngestQuestionnaire
                        protests={protests}
                        onSubmit={handleUrlSubmit}
                        isSubmitting={submitStatus === 'loading'}
                    />
                ) : (
                    // Bulk Import Tab
                    <form onSubmit={handleBulkSubmit} className="space-y-6">
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-2">
                                Enter URLs (one per line, max 10)
                            </label>
                            <textarea
                                value={bulkUrls}
                                onChange={(e) => setBulkUrls(e.target.value)}
                                placeholder={`https://example.com/article-1\nhttps://youtube.com/watch?v=abc123\nhttps://news-site.com/protest-coverage`}
                                className="w-full h-48 p-4 border border-gray-300 rounded-lg font-mono text-sm focus:ring-2 focus:ring-green-500 focus:border-green-500"
                            />
                            <p className="mt-2 text-sm text-gray-500">
                                Supports YouTube, news articles, and image URLs. Each URL will be processed separately.
                            </p>
                        </div>

                        {/* URL Count Preview */}
                        {bulkUrls.trim() && (
                            <div className="p-4 bg-gray-50 rounded-lg">
                                <div className="text-sm text-gray-600">
                                    <span className="font-medium">URLs detected: </span>
                                    {bulkUrls.split('\n').filter(url => url.trim() && (url.trim().startsWith('http://') || url.trim().startsWith('https://'))).length}
                                    /10
                                </div>
                            </div>
                        )}

                        {/* Bulk Results */}
                        {bulkResults && (
                            <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
                                <h4 className="font-medium text-blue-800 mb-2">Processing Started</h4>
                                {bulkResults.tasks && (
                                    <div className="space-y-2">
                                        {bulkResults.tasks.map((task, idx) => (
                                            <div key={idx} className="flex items-center gap-2 text-sm">
                                                <Loader2 className="h-4 w-4 animate-spin text-blue-600" />
                                                <span className="text-gray-700 truncate max-w-md">{task.url}</span>
                                                <span className="text-xs text-gray-500">({task.task_id})</span>
                                            </div>
                                        ))}
                                    </div>
                                )}
                                {bulkResults.errors && bulkResults.errors.length > 0 && (
                                    <div className="mt-3 pt-3 border-t border-blue-200">
                                        <h5 className="font-medium text-red-700 mb-1">Validation Errors:</h5>
                                        {bulkResults.errors.map((err, idx) => (
                                            <div key={idx} className="flex items-center gap-2 text-sm text-red-600">
                                                <X className="h-4 w-4" />
                                                <span className="truncate">{err.url}: {err.error}</span>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>
                        )}

                        {/* Turnstile CAPTCHA */}
                        <div className="py-2 flex justify-center">
                            <Turnstile
                                onVerify={(token) => setTurnstileToken(token)}
                                onExpire={() => setTurnstileToken(null)}
                                onError={() => {
                                    setSubmitStatus('error');
                                    setMessage('Security check failed. Please try again.');
                                }}
                                theme="light"
                            />
                        </div>

                        <Button
                            type="submit"
                            className="w-full bg-green-700 hover:bg-green-800 text-white py-6 text-lg"
                            disabled={!bulkUrls.trim() || submitStatus === 'loading' || !turnstileToken}
                        >
                            {submitStatus === 'loading' ? (
                                <span className="flex items-center gap-2">
                                    <Loader2 className="h-5 w-5 animate-spin" />
                                    Processing...
                                </span>
                            ) : (
                                'Start Bulk Import'
                            )}
                        </Button>

                        <div className="text-center text-xs text-gray-500">
                            All URLs are processed in parallel. Check the Dashboard to monitor progress.
                        </div>
                    </form>
                )}
            </Card>
        </div>
    );
};

export default UploadPage;


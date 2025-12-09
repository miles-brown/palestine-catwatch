import { useState, useEffect } from 'react';
import { Upload, FileVideo, Image as ImageIcon, CheckCircle, AlertCircle, Link as LinkIcon, FileUp, List, Loader2, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import IngestQuestionnaire from '@/components/IngestQuestionnaire';
import LiveAnalysis from '@/components/LiveAnalysis';
import PasswordGate from '@/components/PasswordGate';
import { useNavigate } from 'react-router-dom';
import { API_BASE, safeFetch } from '@/utils/api';

// Helper to format error messages consistently
const formatErrorMessage = (error) => {
    return typeof error === 'object' ? JSON.stringify(error) : String(error);
};

const UploadPage = () => {
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

    // Fetch protests on mount with proper error handling
    useEffect(() => {
        const fetchProtests = async () => {
            const { data, error } = await safeFetch(`${API_BASE}/protests`);
            if (error) {
                console.error("Failed to fetch protests:", error);
                // Non-blocking - protests dropdown will be empty but upload still works
            } else if (data) {
                setProtests(data);
            }
        };
        fetchProtests();
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

        setSubmitStatus('loading');
        const formData = new FormData();
        formData.append('file', file);
        formData.append('type', mediaType);
        formData.append('protest_id', 1); // Default ID, should be selectable if we add dropdown here too

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

            // Start Live Analysis
            if (data.task_id) {
                setLiveTaskId(data.task_id);
            }

        } catch (error) {
            setSubmitStatus('error');
            // Only show API target URL in development mode for security
            const debugInfo = import.meta.env.DEV ? ` (Target: ${API_BASE})` : '';
            setMessage(`${error.message || 'Failed'}${debugInfo}`);
        }
    };

    const navigate = useNavigate();

    if (liveTaskId) {
        return (
            <LiveAnalysis
                taskId={liveTaskId}
                onComplete={(mediaId) => {
                    if (mediaId) {
                        setLiveTaskId(null);
                        setSubmitStatus(null);
                        setMessage('');
                        navigate(`/report/${mediaId}`);
                    } else {
                        console.error("Report Generation Error: No Media ID returned.");
                        alert("Error: Analysis completed but no Report could be generated (Missing Media ID).");
                        setLiveTaskId(null);
                    }
                }}
            />
        );
    }

    return (
        <PasswordGate>
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

                        <Button
                            type="submit"
                            className="w-full bg-green-700 hover:bg-green-800 text-white py-6 text-lg"
                            disabled={!file || submitStatus === 'loading'}
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

                        <Button
                            type="submit"
                            className="w-full bg-green-700 hover:bg-green-800 text-white py-6 text-lg"
                            disabled={!bulkUrls.trim() || submitStatus === 'loading'}
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
        </PasswordGate>
    );
};

export default UploadPage;


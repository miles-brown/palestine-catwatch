import { useEffect, useState, useRef, useCallback, useMemo } from 'react';
import { io } from 'socket.io-client';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Terminal, Cpu, Shield, AlertTriangle, Check, X, Activity, ZoomIn, RefreshCw, WifiOff, Clock, CheckCircle, User, MapPin, Calendar, Image as ImageIcon, FileCheck, Globe, Video, FileText, Download, Search, ScanLine, MonitorPlay, Server, HardDrive, Undo2, StopCircle } from 'lucide-react';

let API_URL = import.meta.env.VITE_API_BASE || 'http://localhost:8000';
if (!API_URL.startsWith("http")) {
    API_URL = `https://${API_URL}`;
}

// Helper to handle both absolute R2 URLs and relative API paths
const getImageUrl = (url) => {
    if (!url) return '';
    // If URL is already absolute (starts with http), use it directly
    if (url.startsWith('http://') || url.startsWith('https://')) {
        return url;
    }
    // Otherwise, prepend API_URL for relative paths
    return `${API_URL}${url}`;
};

// UK Police Forces for dropdown
const UK_POLICE_FORCES = [
    { value: "", label: "Select Force..." },
    { value: "Metropolitan Police Service", label: "Metropolitan Police" },
    { value: "City of London Police", label: "City of London Police" },
    { value: "British Transport Police", label: "British Transport Police" },
    { value: "Greater Manchester Police", label: "Greater Manchester Police" },
    { value: "West Midlands Police", label: "West Midlands Police" },
    { value: "West Yorkshire Police", label: "West Yorkshire Police" },
    { value: "Merseyside Police", label: "Merseyside Police" },
    { value: "South Yorkshire Police", label: "South Yorkshire Police" },
    { value: "Thames Valley Police", label: "Thames Valley Police" },
    { value: "Hampshire Constabulary", label: "Hampshire Constabulary" },
    { value: "Kent Police", label: "Kent Police" },
    { value: "Essex Police", label: "Essex Police" },
    { value: "Sussex Police", label: "Sussex Police" },
    { value: "Surrey Police", label: "Surrey Police" },
    { value: "Avon and Somerset Police", label: "Avon and Somerset" },
    { value: "Devon and Cornwall Police", label: "Devon and Cornwall" },
    { value: "Dorset Police", label: "Dorset Police" },
    { value: "Wiltshire Police", label: "Wiltshire Police" },
    { value: "South Wales Police", label: "South Wales Police" },
    { value: "Gwent Police", label: "Gwent Police" },
    { value: "Dyfed-Powys Police", label: "Dyfed-Powys Police" },
    { value: "North Wales Police", label: "North Wales Police" },
    { value: "Police Scotland", label: "Police Scotland" },
    { value: "Police Service of Northern Ireland", label: "PSNI" },
    { value: "Ministry of Defence Police", label: "MOD Police" },
    { value: "Civil Nuclear Constabulary", label: "Civil Nuclear" },
    { value: "Unknown", label: "Unknown" },
];

// UK Police Ranks
const UK_POLICE_RANKS = [
    { value: "", label: "Select Rank..." },
    { value: "Police Constable", label: "Police Constable (PC)" },
    { value: "Sergeant", label: "Sergeant (Sgt)" },
    { value: "Inspector", label: "Inspector (Insp)" },
    { value: "Chief Inspector", label: "Chief Inspector (CI)" },
    { value: "Superintendent", label: "Superintendent (Supt)" },
    { value: "Chief Superintendent", label: "Chief Superintendent" },
    { value: "PCSO", label: "PCSO" },
    { value: "Special Constable", label: "Special Constable" },
    { value: "Unknown", label: "Unknown" },
];

const MAX_RECONNECT_ATTEMPTS = 5;
const CONNECTION_TIMEOUT = 20000; // 20 seconds
const STALE_TIMEOUT = 60000; // 60 seconds without updates = stale

// Error types for granular handling
const ErrorType = {
    CONNECTION_FAILED: 'connection_failed',
    CONNECTION_TIMEOUT: 'connection_timeout',
    CONNECTION_LOST: 'connection_lost',
    PROCESSING_ERROR: 'processing_error',
    RATE_LIMITED: 'rate_limited',
    SERVER_ERROR: 'server_error',
    STALE_CONNECTION: 'stale_connection'
};

// Error messages and recovery actions
const ERROR_CONFIG = {
    [ErrorType.CONNECTION_FAILED]: {
        title: 'Connection Failed',
        message: 'Unable to connect to the analysis server.',
        recoverable: true,
        retryDelay: 2000
    },
    [ErrorType.CONNECTION_TIMEOUT]: {
        title: 'Connection Timeout',
        message: 'Server is not responding. It may be overloaded or unavailable.',
        recoverable: true,
        retryDelay: 5000
    },
    [ErrorType.CONNECTION_LOST]: {
        title: 'Connection Lost',
        message: 'Lost connection to server during analysis.',
        recoverable: true,
        retryDelay: 1000
    },
    [ErrorType.PROCESSING_ERROR]: {
        title: 'Processing Error',
        message: 'An error occurred during analysis.',
        recoverable: false,
        retryDelay: 0
    },
    [ErrorType.RATE_LIMITED]: {
        title: 'Rate Limited',
        message: 'Too many requests. Please wait before trying again.',
        recoverable: true,
        retryDelay: 60000
    },
    [ErrorType.SERVER_ERROR]: {
        title: 'Server Error',
        message: 'The server encountered an internal error.',
        recoverable: true,
        retryDelay: 5000
    },
    [ErrorType.STALE_CONNECTION]: {
        title: 'Stale Connection',
        message: 'No updates received for a while. Connection may be stale.',
        recoverable: true,
        retryDelay: 1000
    }
};

export default function LiveAnalysis({ taskId, onComplete }) {
    const [logs, setLogs] = useState([]);
    const [candidates, setCandidates] = useState([]);
    const [scrapedMedia, setScrapedMedia] = useState([]);
    const [status, setStatus] = useState('connecting'); // connecting, active, complete, error, paused
    const [stats, setStats] = useState({ faces: 0, objects: 0, confidence_avg: 0 });
    const [errorInfo, setErrorInfo] = useState(null); // { type, message, recoverable }
    const [reconnectAttempts, setReconnectAttempts] = useState(0);
    const [lastUpdate, setLastUpdate] = useState(Date.now());
    const [processingStage, setProcessingStage] = useState('initializing');
    // Stages: initializing, url_analysis, content_detection, downloading, video_analysis, officer_detection, finalizing
    const [detectedContent, setDetectedContent] = useState(null); // { type: 'video'|'images'|'article', count: number }
    const [downloadProgress, setDownloadProgress] = useState({ current: 0, total: 0, percent: 0 });
    const [analysisProgress, setAnalysisProgress] = useState({ framesProcessed: 0, totalFrames: 0 });
    const logEndRef = useRef(null);
    const socketRef = useRef(null);

    const [currentFrame, setCurrentFrame] = useState(null);
    const [reconData, setReconData] = useState(null);
    const [articleMetadata, setArticleMetadata] = useState(null);
    const [mediaId, setMediaId] = useState(null);
    const [finishedEarly, setFinishedEarly] = useState(false);
    const frameTimeoutRef = useRef(null);
    const connectionTimeoutRef = useRef(null);
    const staleCheckRef = useRef(null);

    const addLog = useCallback((source, message) => {
        setLogs(prev => [...prev, { time: new Date().toLocaleTimeString(), source, message }]);
        setLastUpdate(Date.now());
    }, []);

    // Set error with proper typing
    const setError = useCallback((errorType, customMessage = null) => {
        const config = ERROR_CONFIG[errorType] || ERROR_CONFIG[ErrorType.SERVER_ERROR];
        setErrorInfo({
            type: errorType,
            title: config.title,
            message: customMessage || config.message,
            recoverable: config.recoverable,
            retryDelay: config.retryDelay
        });
        setStatus('error');
        addLog('Error', customMessage || config.message);
    }, [addLog]);

    // Clear error state
    const clearError = useCallback(() => {
        setErrorInfo(null);
    }, []);

    // Detect processing stage and content type from log messages
    const detectStage = useCallback((message) => {
        const lowerMsg = message.toLowerCase();

        // URL Analysis stage
        if (lowerMsg.includes('fetching url') || lowerMsg.includes('analyzing url') ||
            lowerMsg.includes('checking url') || lowerMsg.includes('requesting')) {
            setProcessingStage('url_analysis');
        }
        // Content Detection stage
        else if (lowerMsg.includes('found video') || lowerMsg.includes('detected video')) {
            setProcessingStage('content_detection');
            const match = message.match(/(\d+)/);
            setDetectedContent({ type: 'video', count: 1, duration: match ? match[1] : null });
        }
        else if (lowerMsg.includes('found') && lowerMsg.includes('image')) {
            setProcessingStage('content_detection');
            const match = message.match(/(\d+)/);
            setDetectedContent({ type: 'images', count: match ? parseInt(match[1]) : 1 });
        }
        else if (lowerMsg.includes('article') || lowerMsg.includes('text content')) {
            setProcessingStage('content_detection');
            setDetectedContent({ type: 'article', count: 1 });
        }
        // Downloading stage
        else if (lowerMsg.includes('download') || lowerMsg.includes('fetch')) {
            setProcessingStage('downloading');
            // Try to extract progress
            const progressMatch = message.match(/(\d+)%/);
            if (progressMatch) {
                setDownloadProgress(prev => ({ ...prev, percent: parseInt(progressMatch[1]) }));
            }
            const sizeMatch = message.match(/(\d+\.?\d*)\s*(mb|gb|kb)/i);
            if (sizeMatch) {
                setDownloadProgress(prev => ({ ...prev, current: parseFloat(sizeMatch[1]), unit: sizeMatch[2] }));
            }
        }
        // Video Analysis stage
        else if (lowerMsg.includes('processing video') || lowerMsg.includes('extracting frame') ||
                 lowerMsg.includes('scanning video') || lowerMsg.includes('analyzing video')) {
            setProcessingStage('video_analysis');
            const frameMatch = message.match(/frame\s*(\d+)/i);
            const totalMatch = message.match(/of\s*(\d+)/i) || message.match(/total:\s*(\d+)/i);
            if (frameMatch) {
                setAnalysisProgress(prev => ({
                    framesProcessed: parseInt(frameMatch[1]),
                    totalFrames: totalMatch ? parseInt(totalMatch[1]) : prev.totalFrames
                }));
            }
        }
        // Officer Detection stage
        else if (lowerMsg.includes('detect') && (lowerMsg.includes('officer') || lowerMsg.includes('police') || lowerMsg.includes('face'))) {
            setProcessingStage('officer_detection');
        }
        else if (lowerMsg.includes('analyz') || lowerMsg.includes('scan')) {
            setProcessingStage('officer_detection');
        }
        // Finalizing stage
        else if (lowerMsg.includes('sav') || lowerMsg.includes('final') || lowerMsg.includes('complet') || lowerMsg.includes('generating report')) {
            setProcessingStage('finalizing');
        }
    }, []);

    // Check for stale connection
    const checkStale = useCallback(() => {
        const timeSinceUpdate = Date.now() - lastUpdate;
        if (timeSinceUpdate > STALE_TIMEOUT && status === 'active') {
            setError(ErrorType.STALE_CONNECTION, `No updates for ${Math.round(timeSinceUpdate / 1000)}s`);
        }
    }, [lastUpdate, status, setError]);

    // Start stale connection checker
    useEffect(() => {
        if (status === 'active') {
            staleCheckRef.current = setInterval(checkStale, 10000);
        }
        return () => {
            if (staleCheckRef.current) {
                clearInterval(staleCheckRef.current);
            }
        };
    }, [status, checkStale]);

    const connectSocket = useCallback(() => {
        // Clear any existing connection timeout
        if (connectionTimeoutRef.current) {
            clearTimeout(connectionTimeoutRef.current);
        }

        // Set connection timeout
        connectionTimeoutRef.current = setTimeout(() => {
            if (status === 'connecting') {
                setError(ErrorType.CONNECTION_TIMEOUT);
            }
        }, CONNECTION_TIMEOUT);

        // Connect to WebSocket
        const socket = io(API_URL, {
            path: '/socket.io',
            transports: ['websocket', 'polling'], // Allow fallback to polling
            timeout: CONNECTION_TIMEOUT,
            reconnection: true,
            reconnectionAttempts: MAX_RECONNECT_ATTEMPTS,
            reconnectionDelay: 1000,
        });
        socketRef.current = socket;

        socket.on('connect', () => {
            clearTimeout(connectionTimeoutRef.current);
            setReconnectAttempts(0);
            clearError();
            addLog('System', 'Connected to analysis server.');
            setStatus('active');
            setProcessingStage('initializing');
            socket.emit('join_task', taskId);
        });

        socket.on('connect_error', (error) => {
            clearTimeout(connectionTimeoutRef.current);
            setReconnectAttempts(prev => {
                const newCount = prev + 1;
                if (newCount >= MAX_RECONNECT_ATTEMPTS) {
                    // Check for rate limiting
                    if (error.message && error.message.includes('429')) {
                        setError(ErrorType.RATE_LIMITED, 'Too many connection attempts. Please wait.');
                    } else {
                        setError(ErrorType.CONNECTION_FAILED, `Failed after ${MAX_RECONNECT_ATTEMPTS} attempts. Is the server running?`);
                    }
                } else {
                    addLog('Warning', `Connection attempt ${newCount}/${MAX_RECONNECT_ATTEMPTS} failed`);
                }
                return newCount;
            });
        });

        socket.on('disconnect', (reason) => {
            addLog('System', `Disconnected: ${reason}`);
            if (reason === 'io server disconnect') {
                // Server intentionally disconnected - could be error or rate limit
                if (status !== 'complete') {
                    setError(ErrorType.SERVER_ERROR, 'Server closed the connection.');
                }
            } else if (reason === 'transport close' || reason === 'transport error') {
                // Network issue
                if (status !== 'complete' && status !== 'error') {
                    setError(ErrorType.CONNECTION_LOST);
                }
            }
        });

        socket.on('reconnect', (attemptNumber) => {
            addLog('System', `Reconnected after ${attemptNumber} attempts`);
            clearError();
            setStatus('active');
            socket.emit('join_task', taskId);
        });

        socket.on('reconnect_failed', () => {
            setError(ErrorType.CONNECTION_FAILED, 'Failed to reconnect after multiple attempts.');
        });

        socket.on('log_message', (data) => {
            addLog('System', data.message);
            detectStage(data.message);
        });

        // Custom events from backend
        socket.on('log', (msg) => {
            addLog('Info', msg);
            detectStage(msg);
        });

        // Handle backend errors with granular types
        socket.on('Error', (msg) => {
            const lowerMsg = msg.toLowerCase();
            if (lowerMsg.includes('rate limit') || lowerMsg.includes('too many')) {
                setError(ErrorType.RATE_LIMITED, msg);
            } else if (lowerMsg.includes('not found') || lowerMsg.includes('invalid')) {
                setError(ErrorType.PROCESSING_ERROR, msg);
            } else {
                // Non-fatal error - log but don't stop processing
                addLog('Error', msg);
                // Show warning but don't set error status
                setErrorInfo({
                    type: ErrorType.PROCESSING_ERROR,
                    title: 'Warning',
                    message: msg,
                    recoverable: true,
                    retryDelay: 0
                });
            }
        });

        socket.on('analyzing_frame', (data) => {
            setCurrentFrame(data);
            // Clear frame after 2 seconds if no new one comes (prevents stale "stuck" image)
            if (frameTimeoutRef.current) clearTimeout(frameTimeoutRef.current);
            frameTimeoutRef.current = setTimeout(() => setCurrentFrame(null), 2000);
        });

        socket.on('recon_result', (data) => {
            setReconData(data);
        });

        socket.on('article_metadata', (data) => {
            setArticleMetadata(data);
            addLog('AI', `Analyzed: ${data.source_name} - ${data.image_count} images found`);
        });

        socket.on('media_created', (data) => {
            if (data && data.media_id) {
                setMediaId(data.media_id);
                addLog('System', `Media ID confirmed: ${data.media_id}`);
            }
        });

        socket.on('scraped_image', (data) => {
            setScrapedMedia(prev => [...prev, data]);
        });

        socket.on('status_update', (newStatus) => {
            // Don't override error status unless it's complete
            if (status !== 'error' || newStatus === 'complete') {
                setStatus(newStatus);
            }
        });

        socket.on('candidate_officer', (data) => {
            addLog('AI', `Candidate detected with ${(data.confidence * 100).toFixed(1)}% confidence (ID: ${data.appearance_id || 'pending'})`);
            console.log('[LiveAnalysis] candidate_officer received:', data);
            setCandidates(prev => [...prev, {
                ...data,
                id: data.appearance_id || Date.now(), // Use DB ID if available
                appearance_id: data.appearance_id,
                officer_id: data.officer_id,
                reviewed: false
            }]);
            setStats(s => ({ ...s, faces: s.faces + 1, confidence_avg: (s.confidence_avg + data.confidence) / 2 }));
        });

        socket.on('complete', (data) => {
            let msg = data;
            if (typeof data === 'object') {
                msg = data.message;
                if (data.media_id) {
                    setMediaId(data.media_id);
                    addLog('System', `Finalized Media ID: ${data.media_id}`);
                }
            }
            addLog('System', msg || 'Processing complete');
            setStatus('complete');
            setCurrentFrame(null);
            clearError();
        });

        return socket;
    }, [taskId, addLog, status, reconnectAttempts]);

    const handleRetry = useCallback(() => {
        setStatus('connecting');
        clearError();
        setReconnectAttempts(0);
        setProcessingStage('initializing');
        if (socketRef.current) {
            socketRef.current.disconnect();
        }
        connectSocket();
    }, [connectSocket, clearError]);

    useEffect(() => {
        const socket = connectSocket();

        return () => {
            socket.disconnect();
            if (frameTimeoutRef.current) clearTimeout(frameTimeoutRef.current);
            if (connectionTimeoutRef.current) clearTimeout(connectionTimeoutRef.current);
            if (staleCheckRef.current) clearInterval(staleCheckRef.current);
        };
        // NOTE: connectSocket is intentionally omitted from deps to prevent reconnection
        // on every state change. We only want to reconnect when taskId changes.
        // The socket handlers access latest state via closures in the callbacks.
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [taskId]);

    // Auto-scroll logs - only scroll if user is near bottom
    const logContainerRef = useRef(null);
    const userScrolledUp = useRef(false);

    useEffect(() => {
        const container = logContainerRef.current;
        if (!container || userScrolledUp.current) return;

        // Only auto-scroll if user is near the bottom
        const isNearBottom = container.scrollHeight - container.scrollTop - container.clientHeight < 100;
        if (isNearBottom) {
            // Use scrollTo on the container instead of scrollIntoView to prevent page jumping
            container.scrollTo({ top: container.scrollHeight, behavior: 'smooth' });
        }
    }, [logs]);

    // Track if user scrolled up
    const handleLogScroll = useCallback((e) => {
        const container = e.target;
        const isNearBottom = container.scrollHeight - container.scrollTop - container.clientHeight < 100;
        userScrolledUp.current = !isNearBottom;
    }, []);

    const handleDecision = (id, decision) => {
        // Update local state with decision
        console.log(`User decision for ${id}: ${decision}`);
        setCandidates(prev => prev.map(c => c.id === id ? { ...c, reviewed: true, decision } : c));
    };

    const handleUndoDecision = (id) => {
        // Undo a previous decision (particularly useful for undoing declines)
        console.log(`Undoing decision for ${id}`);
        setCandidates(prev => prev.map(c => c.id === id ? { ...c, reviewed: false, decision: null } : c));
    };

    const handleFinishEarly = () => {
        // Stop processing and proceed with what we have
        setFinishedEarly(true);
        setStatus('complete');
        setCurrentFrame(null);
        addLog('System', 'Processing stopped early by user. Proceeding with collected results.');

        // Disconnect socket to stop receiving more candidates
        if (socketRef.current) {
            socketRef.current.disconnect();
        }
    };

    // Get status display properties
    const getStatusDisplay = () => {
        switch (status) {
            case 'connecting':
                return { text: 'CONNECTING', color: 'text-yellow-400', bgColor: 'bg-yellow-500/10' };
            case 'active':
                return { text: 'ACTIVE', color: 'text-green-400', bgColor: 'bg-green-500/10' };
            case 'complete':
                return { text: 'COMPLETE', color: 'text-blue-400', bgColor: 'bg-blue-500/10' };
            case 'error':
                return { text: 'ERROR', color: 'text-red-400', bgColor: 'bg-red-500/10' };
            default:
                return { text: status.toUpperCase(), color: 'text-blue-400', bgColor: 'bg-blue-500/10' };
        }
    };

    const statusDisplay = getStatusDisplay();

    // Connection Status Bar Component
    const ConnectionStatusBar = () => {
        if (status === 'active' && !errorInfo) return null;

        const getStatusConfig = () => {
            if (status === 'connecting') {
                return {
                    bg: 'bg-yellow-500/20',
                    border: 'border-yellow-500/50',
                    icon: <RefreshCw className="h-4 w-4 animate-spin text-yellow-400" />,
                    text: reconnectAttempts > 0
                        ? `Reconnecting... (${reconnectAttempts}/${MAX_RECONNECT_ATTEMPTS})`
                        : 'Connecting to server...',
                    subtext: 'Please wait while we establish connection',
                    color: 'text-yellow-400'
                };
            }
            if (status === 'error') {
                return {
                    bg: 'bg-red-500/20',
                    border: 'border-red-500/50',
                    icon: <WifiOff className="h-4 w-4 text-red-400" />,
                    text: errorInfo?.title || 'Connection Error',
                    subtext: errorInfo?.message || 'Unable to connect to server',
                    color: 'text-red-400'
                };
            }
            if (status === 'complete') {
                return {
                    bg: 'bg-green-500/20',
                    border: 'border-green-500/50',
                    icon: <CheckCircle className="h-4 w-4 text-green-400" />,
                    text: 'Analysis Complete',
                    subtext: mediaId ? `Report ready (Media #${mediaId})` : 'Processing finished successfully',
                    color: 'text-green-400'
                };
            }
            return null;
        };

        const config = getStatusConfig();
        if (!config) return null;

        return (
            <div className={`mb-4 p-3 rounded-lg border ${config.bg} ${config.border} flex items-center justify-between`}>
                <div className="flex items-center gap-3">
                    {config.icon}
                    <div>
                        <p className={`font-semibold text-sm ${config.color}`}>{config.text}</p>
                        <p className="text-xs text-slate-400">{config.subtext}</p>
                    </div>
                </div>
                {status === 'error' && errorInfo?.recoverable && (
                    <Button
                        onClick={handleRetry}
                        size="sm"
                        className="bg-red-500/20 hover:bg-red-500/30 border border-red-500/50 text-red-400"
                    >
                        <RefreshCw className="h-4 w-4 mr-1" />
                        Retry
                    </Button>
                )}
            </div>
        );
    };

    // ===== ANIMATED STAGE VISUALIZERS =====

    // URL Analysis Animation - Globe with scanning effect
    const UrlAnalysisVisual = () => (
        <div className="relative flex flex-col items-center justify-center p-8">
            {/* Rotating globe with pulse rings */}
            <div className="relative">
                {/* Pulse rings */}
                <div className="absolute inset-0 flex items-center justify-center">
                    <div className="w-32 h-32 rounded-full border-2 border-blue-500/30 animate-ping" style={{ animationDuration: '2s' }} />
                </div>
                <div className="absolute inset-0 flex items-center justify-center">
                    <div className="w-40 h-40 rounded-full border border-blue-500/20 animate-ping" style={{ animationDuration: '2.5s', animationDelay: '0.5s' }} />
                </div>

                {/* Main globe */}
                <div className="relative w-24 h-24 rounded-full bg-gradient-to-br from-blue-600 to-blue-900 flex items-center justify-center shadow-2xl shadow-blue-500/30">
                    <Globe className="h-12 w-12 text-blue-200 animate-spin" style={{ animationDuration: '8s' }} />

                    {/* Scanning line */}
                    <div className="absolute inset-0 overflow-hidden rounded-full">
                        <div className="absolute w-full h-1 bg-gradient-to-r from-transparent via-cyan-400 to-transparent animate-scan-vertical" />
                    </div>
                </div>
            </div>

            <div className="mt-6 text-center">
                <h3 className="text-lg font-bold text-blue-400 flex items-center gap-2 justify-center">
                    <Search className="h-5 w-5 animate-pulse" />
                    Analyzing URL for Content
                </h3>
                <p className="text-sm text-slate-400 mt-2">Scanning webpage structure and media elements...</p>

                {/* Animated dots */}
                <div className="flex items-center justify-center gap-1 mt-4">
                    <span className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                    <span className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                    <span className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                </div>
            </div>
        </div>
    );

    // Content Detection Animation - Shows what was found
    const ContentDetectionVisual = () => (
        <div className="relative flex flex-col items-center justify-center p-8">
            {/* Success pulse */}
            <div className="relative">
                <div className="absolute inset-0 flex items-center justify-center">
                    <div className="w-36 h-36 rounded-full bg-green-500/20 animate-pulse" />
                </div>

                {/* Content type icon with checkmark */}
                <div className="relative w-28 h-28 rounded-2xl bg-gradient-to-br from-green-600 to-green-800 flex items-center justify-center shadow-2xl shadow-green-500/30 animate-bounce-slow">
                    {detectedContent?.type === 'video' && <Video className="h-14 w-14 text-green-100" />}
                    {detectedContent?.type === 'images' && <ImageIcon className="h-14 w-14 text-green-100" />}
                    {detectedContent?.type === 'article' && <FileText className="h-14 w-14 text-green-100" />}

                    {/* Checkmark badge */}
                    <div className="absolute -top-2 -right-2 w-8 h-8 bg-green-400 rounded-full flex items-center justify-center border-4 border-slate-950">
                        <Check className="h-4 w-4 text-green-900" />
                    </div>
                </div>
            </div>

            <div className="mt-6 text-center">
                <h3 className="text-lg font-bold text-green-400">
                    Content Identified!
                </h3>
                <div className="mt-3 px-4 py-2 bg-green-500/20 rounded-lg border border-green-500/30">
                    {detectedContent?.type === 'video' && (
                        <p className="text-green-300">
                            <span className="font-bold">Video clip</span> detected
                            {detectedContent.duration && <span> ({detectedContent.duration}s)</span>}
                        </p>
                    )}
                    {detectedContent?.type === 'images' && (
                        <p className="text-green-300">
                            <span className="font-bold">{detectedContent.count} image{detectedContent.count !== 1 ? 's' : ''}</span> found
                        </p>
                    )}
                    {detectedContent?.type === 'article' && (
                        <p className="text-green-300">
                            <span className="font-bold">Article</span> with embedded media
                        </p>
                    )}
                </div>
                <p className="text-sm text-slate-400 mt-3">Preparing to download...</p>
            </div>
        </div>
    );

    // Download Animation - Data packets flying from server to computer
    const DownloadVisual = () => (
        <div className="relative flex flex-col items-center justify-center p-8">
            {/* Server to Computer Animation */}
            <div className="flex items-center gap-8">
                {/* Server */}
                <div className="relative">
                    <div className="w-16 h-20 bg-gradient-to-b from-slate-600 to-slate-800 rounded-lg flex flex-col items-center justify-center border border-slate-500 shadow-lg">
                        <Server className="h-6 w-6 text-slate-300 mb-1" />
                        <div className="flex gap-1">
                            <div className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" />
                            <div className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" style={{ animationDelay: '0.2s' }} />
                        </div>
                    </div>
                    <p className="text-xs text-slate-500 mt-2 text-center">Server</p>
                </div>

                {/* Data packets flying */}
                <div className="relative w-32 h-8 overflow-visible">
                    {/* Track line */}
                    <div className="absolute top-1/2 left-0 right-0 h-0.5 bg-gradient-to-r from-blue-500/50 via-cyan-500/50 to-blue-500/50" />

                    {/* Flying packets */}
                    {[0, 1, 2, 3, 4].map((i) => (
                        <div
                            key={i}
                            className="absolute top-1/2 -translate-y-1/2 w-3 h-3 bg-cyan-400 rounded-sm animate-fly-packet shadow-lg shadow-cyan-400/50"
                            style={{
                                animationDelay: `${i * 0.3}s`,
                                animationDuration: '1.5s'
                            }}
                        />
                    ))}
                </div>

                {/* Computer */}
                <div className="relative">
                    <div className="w-20 h-16 bg-gradient-to-b from-slate-700 to-slate-900 rounded-lg flex items-center justify-center border border-slate-600 shadow-lg">
                        <HardDrive className="h-8 w-8 text-cyan-400 animate-pulse" />
                    </div>
                    <div className="w-24 h-2 bg-slate-700 rounded-b-lg mx-auto border-x border-b border-slate-600" />
                    <p className="text-xs text-slate-500 mt-2 text-center">Local</p>
                </div>
            </div>

            <div className="mt-8 text-center w-full max-w-xs">
                <h3 className="text-lg font-bold text-cyan-400 flex items-center gap-2 justify-center">
                    <Download className="h-5 w-5 animate-bounce" />
                    Downloading Media
                </h3>

                {/* Progress bar */}
                <div className="mt-4 w-full">
                    <div className="h-3 bg-slate-800 rounded-full overflow-hidden border border-slate-700">
                        <div
                            className="h-full bg-gradient-to-r from-cyan-600 to-cyan-400 rounded-full transition-all duration-300 relative overflow-hidden"
                            style={{ width: `${Math.max(downloadProgress.percent, 10)}%` }}
                        >
                            {/* Shimmer effect */}
                            <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/30 to-transparent animate-shimmer" />
                        </div>
                    </div>
                    <div className="flex justify-between mt-2 text-xs text-slate-400">
                        <span>{downloadProgress.percent || 0}%</span>
                        {downloadProgress.current > 0 && (
                            <span>{downloadProgress.current} {downloadProgress.unit || 'MB'}</span>
                        )}
                    </div>
                </div>

                <p className="text-sm text-slate-400 mt-3">
                    {detectedContent?.type === 'video' ? 'Downloading video file...' :
                     detectedContent?.type === 'images' ? `Downloading ${detectedContent.count} images...` :
                     'Fetching content...'}
                </p>
            </div>
        </div>
    );

    // Video Analysis Animation - Frame scanning effect
    const VideoAnalysisVisual = () => (
        <div className="relative flex flex-col items-center justify-center p-8">
            {/* Video frame with scanning effect */}
            <div className="relative">
                {/* Outer glow */}
                <div className="absolute -inset-4 bg-purple-500/20 rounded-xl blur-xl animate-pulse" />

                {/* Main video frame */}
                <div className="relative w-64 h-40 bg-gradient-to-br from-slate-800 to-slate-900 rounded-lg border-2 border-purple-500/50 overflow-hidden shadow-2xl shadow-purple-500/20">
                    {/* Video icon in center */}
                    <div className="absolute inset-0 flex items-center justify-center">
                        <MonitorPlay className="h-16 w-16 text-slate-600" />
                    </div>

                    {/* Scanning line horizontal */}
                    <div className="absolute inset-0 overflow-hidden">
                        <div className="absolute w-full h-1 bg-gradient-to-r from-transparent via-purple-400 to-transparent animate-scan-horizontal" />
                    </div>

                    {/* Grid overlay */}
                    <div className="absolute inset-0 opacity-30">
                        <div className="grid grid-cols-4 grid-rows-3 h-full">
                            {[...Array(12)].map((_, i) => (
                                <div key={i} className="border border-purple-500/20" />
                            ))}
                        </div>
                    </div>

                    {/* Frame counter */}
                    <div className="absolute bottom-2 right-2 bg-black/80 px-2 py-1 rounded text-xs font-mono text-purple-400">
                        {analysisProgress.framesProcessed > 0 ? (
                            <span>
                                Frame {analysisProgress.framesProcessed}
                                {analysisProgress.totalFrames > 0 && ` / ${analysisProgress.totalFrames}`}
                            </span>
                        ) : (
                            <span className="animate-pulse">Scanning...</span>
                        )}
                    </div>

                    {/* Recording indicator */}
                    <div className="absolute top-2 left-2 flex items-center gap-1.5 bg-black/80 px-2 py-1 rounded">
                        <div className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
                        <span className="text-xs text-red-400 font-bold">ANALYZING</span>
                    </div>
                </div>
            </div>

            <div className="mt-6 text-center">
                <h3 className="text-lg font-bold text-purple-400 flex items-center gap-2 justify-center">
                    <ScanLine className="h-5 w-5" />
                    Analyzing Video Frames
                </h3>

                {/* Progress indicator */}
                {analysisProgress.totalFrames > 0 && (
                    <div className="mt-4 w-64">
                        <div className="h-2 bg-slate-800 rounded-full overflow-hidden">
                            <div
                                className="h-full bg-gradient-to-r from-purple-600 to-purple-400 rounded-full transition-all duration-300"
                                style={{ width: `${(analysisProgress.framesProcessed / analysisProgress.totalFrames) * 100}%` }}
                            />
                        </div>
                    </div>
                )}

                <p className="text-sm text-slate-400 mt-3">Extracting frames for officer detection...</p>
            </div>
        </div>
    );

    // Officer Detection Animation - Face scanning effect
    const OfficerDetectionVisual = () => (
        <div className="relative flex flex-col items-center justify-center p-8">
            {/* Circular radar-like scanner */}
            <div className="relative w-48 h-48">
                {/* Radar circles */}
                <div className="absolute inset-0 rounded-full border border-green-500/30" />
                <div className="absolute inset-4 rounded-full border border-green-500/20" />
                <div className="absolute inset-8 rounded-full border border-green-500/10" />

                {/* Rotating sweep */}
                <div className="absolute inset-0 animate-spin" style={{ animationDuration: '3s' }}>
                    <div className="absolute top-1/2 left-1/2 w-1/2 h-0.5 bg-gradient-to-r from-green-400 to-transparent origin-left" />
                </div>

                {/* Sweep glow */}
                <div className="absolute inset-0 animate-spin" style={{ animationDuration: '3s' }}>
                    <div className="absolute top-0 left-1/2 w-1/2 h-1/2 origin-bottom-left bg-gradient-to-r from-green-500/20 to-transparent"
                         style={{ clipPath: 'polygon(0 100%, 100% 0, 100% 100%)' }} />
                </div>

                {/* Center icon */}
                <div className="absolute inset-0 flex items-center justify-center">
                    <div className="w-16 h-16 rounded-full bg-gradient-to-br from-green-600 to-green-800 flex items-center justify-center border-2 border-green-400 shadow-lg shadow-green-500/30">
                        <Shield className="h-8 w-8 text-green-100" />
                    </div>
                </div>

                {/* Detection pings */}
                {stats.faces > 0 && [...Array(Math.min(stats.faces, 5))].map((_, i) => (
                    <div
                        key={i}
                        className="absolute w-3 h-3 bg-green-400 rounded-full animate-ping"
                        style={{
                            top: `${20 + Math.random() * 60}%`,
                            left: `${20 + Math.random() * 60}%`,
                            animationDelay: `${i * 0.5}s`,
                            animationDuration: '2s'
                        }}
                    />
                ))}
            </div>

            <div className="mt-6 text-center">
                <h3 className="text-lg font-bold text-green-400 flex items-center gap-2 justify-center">
                    <User className="h-5 w-5" />
                    Detecting Officers
                </h3>

                {stats.faces > 0 && (
                    <div className="mt-3 px-4 py-2 bg-green-500/20 rounded-lg border border-green-500/30 inline-flex items-center gap-2">
                        <span className="text-2xl font-bold text-green-400">{stats.faces}</span>
                        <span className="text-green-300">officer{stats.faces !== 1 ? 's' : ''} detected</span>
                    </div>
                )}

                <p className="text-sm text-slate-400 mt-3">
                    Scanning for police uniforms and faces...
                </p>
            </div>
        </div>
    );

    // Stage Visual Selector - Shows appropriate animation for current stage
    const StageVisual = () => {
        // Only show stage visuals when active and no current frame/candidates
        if (status !== 'active' || currentFrame || candidates.length > 0 || scrapedMedia.length > 0) {
            return null;
        }

        switch (processingStage) {
            case 'initializing':
            case 'url_analysis':
                return <UrlAnalysisVisual />;
            case 'content_detection':
                return detectedContent ? <ContentDetectionVisual /> : <UrlAnalysisVisual />;
            case 'downloading':
                return <DownloadVisual />;
            case 'video_analysis':
                return <VideoAnalysisVisual />;
            case 'officer_detection':
                return <OfficerDetectionVisual />;
            default:
                return <UrlAnalysisVisual />;
        }
    };

    return (
        <div className="min-h-screen bg-slate-950 text-slate-200 p-3 sm:p-6 font-mono">
            {/* Connection Status Bar */}
            <ConnectionStatusBar />

            {/* Error Banner with context-aware styling */}
            {errorInfo && status !== 'connecting' && (
                <div className={`mb-6 p-4 rounded-lg flex items-center justify-between ${
                    status === 'error'
                        ? 'bg-red-900/30 border border-red-500/50'
                        : 'bg-yellow-900/30 border border-yellow-500/50'
                }`}>
                    <div className="flex items-center gap-3">
                        {errorInfo.type === ErrorType.CONNECTION_LOST || errorInfo.type === ErrorType.CONNECTION_FAILED ? (
                            <WifiOff className="h-5 w-5 text-red-400" />
                        ) : errorInfo.type === ErrorType.RATE_LIMITED ? (
                            <Clock className="h-5 w-5 text-yellow-400" />
                        ) : errorInfo.type === ErrorType.STALE_CONNECTION ? (
                            <Activity className="h-5 w-5 text-yellow-400" />
                        ) : (
                            <AlertTriangle className={`h-5 w-5 ${status === 'error' ? 'text-red-400' : 'text-yellow-400'}`} />
                        )}
                        <div>
                            <p className={`font-bold ${status === 'error' ? 'text-red-400' : 'text-yellow-400'}`}>
                                {errorInfo.title}
                            </p>
                            <p className={`text-sm ${status === 'error' ? 'text-red-300' : 'text-yellow-300'}`}>
                                {errorInfo.message}
                            </p>
                            {reconnectAttempts > 0 && reconnectAttempts < MAX_RECONNECT_ATTEMPTS && (
                                <p className="text-xs text-slate-400 mt-1">
                                    Reconnect attempt {reconnectAttempts}/{MAX_RECONNECT_ATTEMPTS}...
                                </p>
                            )}
                        </div>
                    </div>
                    <div className="flex gap-2">
                        {errorInfo.recoverable && (
                            <Button
                                onClick={handleRetry}
                                variant="outline"
                                className={`${status === 'error' ? 'border-red-500/50 text-red-400 hover:bg-red-500/20' : 'border-yellow-500/50 text-yellow-400 hover:bg-yellow-500/20'}`}
                            >
                                <RefreshCw className="h-4 w-4 mr-2" />
                                Retry
                            </Button>
                        )}
                        {status !== 'error' && (
                            <Button
                                onClick={clearError}
                                variant="ghost"
                                className="text-slate-400 hover:text-slate-200"
                            >
                                <X className="h-4 w-4" />
                            </Button>
                        )}
                    </div>
                </div>
            )}

            {/* Header / HUD */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-2 sm:gap-4 mb-4 sm:mb-6">
                <Card className="bg-slate-900 border-slate-800 p-3 sm:p-4 flex items-center gap-2 sm:gap-4">
                    <div className={`p-3 ${statusDisplay.bgColor} rounded-full ${statusDisplay.color}`}>
                        {status === 'error' ? (
                            <AlertTriangle className="h-6 w-6" />
                        ) : (
                            <Activity className={`h-6 w-6 ${status === 'active' || status === 'connecting' ? 'animate-pulse' : ''}`} />
                        )}
                    </div>
                    <div className="min-w-0">
                        <p className="text-[10px] sm:text-xs text-slate-500 uppercase tracking-wider">Status</p>
                        <p className={`font-bold text-sm sm:text-lg ${statusDisplay.color} truncate`}>
                            {statusDisplay.text}
                        </p>
                    </div>
                </Card>

                <Card className="bg-slate-900 border-slate-800 p-3 sm:p-4 flex items-center gap-2 sm:gap-4">
                    <div className="p-2 sm:p-3 bg-green-500/10 rounded-full text-green-400">
                        <Shield className="h-4 w-4 sm:h-6 sm:w-6" />
                    </div>
                    <div className="min-w-0">
                        <p className="text-[10px] sm:text-xs text-slate-500 uppercase tracking-wider">Officers</p>
                        <p className="font-bold text-sm sm:text-lg text-slate-100">{stats.faces}</p>
                    </div>
                </Card>

                <Card className="bg-slate-900 border-slate-800 p-3 sm:p-4 flex items-center gap-2 sm:gap-4">
                    <div className="p-2 sm:p-3 bg-purple-500/10 rounded-full text-purple-400">
                        <Cpu className="h-4 w-4 sm:h-6 sm:w-6" />
                    </div>
                    <div className="min-w-0">
                        <p className="text-[10px] sm:text-xs text-slate-500 uppercase tracking-wider">Confidence</p>
                        <p className="font-bold text-sm sm:text-lg text-slate-100">{(stats.confidence_avg * 100).toFixed(1)}%</p>
                    </div>
                </Card>

                <Card className="bg-slate-900 border-slate-800 p-3 sm:p-4 flex items-center gap-2 sm:gap-4">
                    <div className="p-2 sm:p-3 bg-indigo-500/10 rounded-full text-indigo-400">
                        <ZoomIn className="h-4 w-4 sm:h-6 sm:w-6" />
                    </div>
                    <div className="min-w-0">
                        <p className="text-[10px] sm:text-xs text-slate-500 uppercase tracking-wider">AI Recon</p>
                        {reconData ? (
                            <div className="flex flex-col">
                                <span className={`font-bold text-lg ${reconData.score > 50 ? 'text-green-400' : 'text-yellow-400'}`}>
                                    {reconData.score}/100
                                </span>
                                <span className="text-[10px] text-slate-400">{reconData.category}</span>
                            </div>
                        ) : (
                            <p className="font-bold text-sm text-slate-500 italic">Waiting...</p>
                        )}
                    </div>
                </Card>
            </div>

            {/* Finish Early Button - shown when processing is active and we have some candidates */}
            {status === 'active' && candidates.length > 0 && (
                <div className="mb-4 flex justify-center">
                    <Button
                        onClick={handleFinishEarly}
                        variant="outline"
                        className="border-yellow-500/50 text-yellow-400 hover:bg-yellow-500/20 hover:text-yellow-300"
                    >
                        <StopCircle className="h-4 w-4 mr-2" />
                        Finish Early ({candidates.length} officers detected)
                    </Button>
                </div>
            )}

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 sm:gap-6 h-[500px] lg:h-[700px]">
                {/* Terminal Log */}
                <Card className="bg-slate-900 border-slate-800 col-span-1 flex flex-col h-full overflow-hidden shadow-2xl shadow-blue-900/5">
                    <div className="p-3 border-b border-slate-800 bg-slate-950 flex items-center justify-between">
                        <div className="flex items-center gap-2">
                            <Terminal className="h-4 w-4 text-slate-400" />
                            <span className="text-xs font-semibold text-slate-400">SYSTEM LOG</span>
                        </div>
                        <span className="text-[10px] text-slate-600">{logs.length} entries</span>
                    </div>
                    <div
                        ref={logContainerRef}
                        onScroll={handleLogScroll}
                        className="flex-1 overflow-y-auto p-4 font-mono text-xs space-y-1"
                    >
                        {logs.length === 0 && (
                            <div className="text-slate-500 italic p-4 text-center opacity-50">
                                Waiting for connection...
                            </div>
                        )}
                        {logs.slice(-50).map((log, i) => (
                            <div key={i} className="flex gap-2 py-0.5">
                                <span className="text-slate-600 flex-shrink-0">[{log.time}]</span>
                                <span className={`flex-shrink-0 ${
                                    log.source === 'Error' ? 'text-red-400' :
                                    log.source === 'AI' ? 'text-green-400' :
                                    log.source === 'Warning' ? 'text-yellow-400' :
                                    'text-blue-400'
                                } font-bold`}>
                                    {log.source}:
                                </span>
                                <span className="text-slate-300 break-words">{log.message}</span>
                            </div>
                        ))}
                        <div ref={logEndRef} />
                    </div>
                </Card>

                {/* Main Visualizer */}
                <Card className="bg-slate-900 border-slate-800 col-span-1 lg:col-span-2 flex flex-col h-full relative overflow-hidden">
                    <div className="p-3 border-b border-slate-800 bg-slate-950 flex justify-between items-center">
                        <div className="flex items-center gap-2">
                            <Cpu className="h-4 w-4 text-green-400" />
                            <span className="text-xs font-semibold text-green-400">LIVE ANALYSIS FEED</span>
                        </div>
                        {status === 'active' && <span className="animate-pulse h-2 w-2 rounded-full bg-green-500"></span>}
                    </div>

                    <div className="flex-1 p-6 overflow-y-auto">

                        {/* Live Frame Scan Overlay */}
                        {status === 'active' && currentFrame && (
                            <div className="mb-6 relative w-full h-64 bg-black rounded-lg overflow-hidden border border-green-500/30 shadow-[0_0_15px_rgba(34,197,94,0.2)]">
                                <img
                                    src={getImageUrl(currentFrame.url)}
                                    className="w-full h-full object-contain opacity-80"
                                    alt="Analyzing Frame"
                                />
                                {/* Scanning Line Animation */}
                                <div className="absolute inset-0 bg-gradient-to-b from-transparent via-green-500/10 to-transparent animate-scan pointer-events-none"></div>
                                <div className="absolute top-2 left-2 bg-black/80 text-green-400 px-2 py-1 text-xs font-bold border border-green-500/50 flex items-center gap-2">
                                    <Activity className="h-3 w-3 animate-pulse" />
                                    SCANNING: {currentFrame.timestamp}
                                </div>
                            </div>
                        )}

                        {/* Scraped Media Gallery */}
                        {scrapedMedia.length > 0 && (
                            <div className="mb-8">
                                <h3 className="text-xs font-bold text-slate-500 uppercase mb-3">Ingested Content ({scrapedMedia.length})</h3>
                                <div className="flex gap-2 overflow-x-auto pb-2 scrollbar-thin scrollbar-thumb-slate-700">
                                    {scrapedMedia.map((media, i) => (
                                        <div key={i} className="flex-shrink-0 w-32 h-24 bg-slate-950 border border-slate-800 rounded overflow-hidden relative group">
                                            <img src={getImageUrl(media.url)} className="w-full h-full object-cover opacity-70 group-hover:opacity-100 transition-opacity" alt="Scraped" />
                                            <div className="absolute inset-0 bg-gradient-to-t from-black/80 to-transparent flex items-end p-1">
                                                <span className="text-[10px] text-slate-300 truncate w-full">{media.filename}</span>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}

                        {/* Stage-specific animated visual */}
                        <StageVisual />

                        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
                            {/* Fallback message only shown if StageVisual doesn't render */}
                            {candidates.length === 0 && scrapedMedia.length === 0 && !currentFrame && status === 'active' &&
                             processingStage === 'finalizing' && (
                                <div className="col-span-full h-32 flex flex-col items-center justify-center text-slate-600 animate-pulse">
                                    <FileCheck className="h-12 w-12 mb-4 opacity-50" />
                                    <p>Finalizing analysis...</p>
                                </div>
                            )}

                            {candidates.map((c) => (
                                <Card key={c.id} className={`bg-slate-950 border ${c.reviewed ? (c.decision === 'yes' ? 'border-green-500/50' : 'border-red-500/30 opacity-50') : 'border-slate-700'} overflow-hidden transition-all`}>
                                    {/* Officer Images - Face and Body */}
                                    <div className="relative bg-slate-900">
                                        <div className="flex">
                                            {/* Face Crop (Primary) */}
                                            <div className="flex-1 aspect-square bg-slate-800 relative">
                                                <img
                                                    src={getImageUrl(c.face_url || c.image_url)}
                                                    className="w-full h-full object-cover"
                                                    alt="Face"
                                                    onError={(e) => {
                                                        e.target.src = getImageUrl(c.image_url);
                                                    }}
                                                />
                                                <div className="absolute bottom-1 left-1 bg-black/80 px-1.5 py-0.5 rounded text-[10px] text-slate-300">
                                                    Face
                                                </div>
                                            </div>
                                            {/* Body Crop (if available) */}
                                            {c.body_url && (
                                                <div className="w-1/3 bg-slate-800 relative border-l border-slate-700">
                                                    <img
                                                        src={getImageUrl(c.body_url)}
                                                        className="w-full h-full object-cover object-top"
                                                        alt="Body"
                                                    />
                                                    <div className="absolute bottom-1 left-1 bg-black/80 px-1.5 py-0.5 rounded text-[10px] text-slate-300">
                                                        Body
                                                    </div>
                                                </div>
                                            )}
                                        </div>
                                        {/* Timestamp & Confidence Badge */}
                                        <div className="absolute top-2 left-2 flex gap-1">
                                            <span className="bg-black/80 px-2 py-0.5 rounded text-[10px] text-white font-mono">
                                                {c.timestamp}
                                            </span>
                                            <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                                                c.confidence >= 0.8 ? 'bg-green-500/90 text-white' :
                                                c.confidence >= 0.6 ? 'bg-yellow-500/90 text-black' :
                                                'bg-red-500/90 text-white'
                                            }`}>
                                                {(c.confidence * 100).toFixed(0)}%
                                            </span>
                                        </div>
                                        {c.quality?.is_blurry && (
                                            <div className="absolute top-2 right-2 bg-yellow-500/90 text-black px-2 py-0.5 rounded text-[10px] font-bold flex items-center gap-1">
                                                <AlertTriangle className="h-3 w-3" /> Blurry
                                            </div>
                                        )}
                                    </div>

                                    <div className="p-3 space-y-3">
                                        {/* Badge/Shoulder Number */}
                                        <div>
                                            <label className="text-[10px] uppercase text-slate-500 font-bold block mb-1">
                                                Shoulder Number / Badge
                                            </label>
                                            <input
                                                type="text"
                                                defaultValue={c.badge || ""}
                                                placeholder="e.g. U1234"
                                                className="w-full bg-slate-900 border border-slate-700 rounded px-2 py-1.5 text-sm text-slate-200 font-mono focus:border-blue-500 focus:ring-1 focus:ring-blue-500/50 outline-none"
                                                onChange={(e) => {
                                                    setCandidates(prev => prev.map(cand =>
                                                        cand.id === c.id ? { ...cand, badge: e.target.value } : cand
                                                    ));
                                                }}
                                            />
                                        </div>

                                        {/* Officer Name (surname from uniform) */}
                                        <div>
                                            <label className="text-[10px] uppercase text-slate-500 font-bold block mb-1">
                                                Officer Name
                                                <span className="ml-1 text-slate-600 font-normal">(surname on uniform)</span>
                                            </label>
                                            <input
                                                type="text"
                                                defaultValue={c.officer_name || ""}
                                                placeholder="e.g. SMITH"
                                                className="w-full bg-slate-900 border border-slate-700 rounded px-2 py-1.5 text-sm text-slate-200 focus:border-blue-500 focus:ring-1 focus:ring-blue-500/50 outline-none uppercase"
                                                onChange={(e) => {
                                                    setCandidates(prev => prev.map(cand =>
                                                        cand.id === c.id ? { ...cand, officer_name: e.target.value.toUpperCase() } : cand
                                                    ));
                                                }}
                                            />
                                        </div>

                                        {/* Force Selection */}
                                        <div>
                                            <label className="text-[10px] uppercase text-slate-500 font-bold block mb-1">
                                                Police Force
                                                {(c.force || c.meta?.uniform_guess) && (
                                                    <span className="ml-2 text-green-400 font-normal">(AI detected)</span>
                                                )}
                                            </label>
                                            <select
                                                className="w-full bg-slate-900 border border-slate-700 rounded px-2 py-1.5 text-sm text-slate-200 focus:border-blue-500 outline-none"
                                                value={c.force || c.meta?.uniform_guess || ""}
                                                onChange={(e) => {
                                                    setCandidates(prev => prev.map(cand =>
                                                        cand.id === c.id ? { ...cand, force: e.target.value } : cand
                                                    ));
                                                }}
                                            >
                                                {UK_POLICE_FORCES.map(force => (
                                                    <option key={force.value} value={force.value}>
                                                        {force.label}
                                                    </option>
                                                ))}
                                            </select>
                                        </div>

                                        {/* Rank Selection */}
                                        <div>
                                            <label className="text-[10px] uppercase text-slate-500 font-bold block mb-1">
                                                Rank
                                                {(c.rank || c.meta?.rank_guess) && (
                                                    <span className="ml-2 text-green-400 font-normal">(AI detected)</span>
                                                )}
                                            </label>
                                            <select
                                                className="w-full bg-slate-900 border border-slate-700 rounded px-2 py-1.5 text-sm text-slate-200 focus:border-blue-500 outline-none"
                                                value={c.rank || c.meta?.rank_guess || ""}
                                                onChange={(e) => {
                                                    setCandidates(prev => prev.map(cand =>
                                                        cand.id === c.id ? { ...cand, rank: e.target.value } : cand
                                                    ));
                                                }}
                                            >
                                                {UK_POLICE_RANKS.map(rank => (
                                                    <option key={rank.value} value={rank.value}>
                                                        {rank.label}
                                                    </option>
                                                ))}
                                            </select>
                                        </div>

                                        {/* Approve/Delete Actions */}
                                        {!c.reviewed ? (
                                            <div className="flex gap-2 pt-2">
                                                <Button
                                                    size="sm"
                                                    onClick={() => handleDecision(c.id, 'no')}
                                                    variant="outline"
                                                    className="flex-1 border-red-500/50 hover:bg-red-500/20 text-red-400 hover:text-red-300 h-9"
                                                >
                                                    <X className="h-4 w-4 mr-1" />
                                                    Delete
                                                </Button>
                                                <Button
                                                    size="sm"
                                                    onClick={() => handleDecision(c.id, 'yes')}
                                                    className="flex-1 bg-green-600 hover:bg-green-500 text-white h-9"
                                                >
                                                    <Check className="h-4 w-4 mr-1" />
                                                    Approve
                                                </Button>
                                            </div>
                                        ) : (
                                            <div className="space-y-2">
                                                <div className={`text-center py-2 text-sm font-bold uppercase rounded ${
                                                    c.decision === 'yes'
                                                        ? 'bg-green-500/20 text-green-400 border border-green-500/30'
                                                        : 'bg-red-500/20 text-red-400 border border-red-500/30'
                                                }`}>
                                                    {c.decision === 'yes' ? (
                                                        <span className="flex items-center justify-center gap-1">
                                                            <CheckCircle className="h-4 w-4" /> Approved
                                                        </span>
                                                    ) : (
                                                        <span className="flex items-center justify-center gap-1">
                                                            <X className="h-4 w-4" /> Deleted
                                                        </span>
                                                    )}
                                                </div>
                                                {/* Undo button */}
                                                <Button
                                                    size="sm"
                                                    variant="ghost"
                                                    onClick={() => handleUndoDecision(c.id)}
                                                    className="w-full text-slate-400 hover:text-slate-200 hover:bg-slate-800 h-8"
                                                >
                                                    <Undo2 className="h-3 w-3 mr-1" />
                                                    Undo
                                                </Button>
                                            </div>
                                        )}
                                    </div>
                                </Card>
                            ))}
                        </div>
                    </div>
                </Card>
            </div>

            {/* Scan Complete Summary */}
            {status === 'complete' && (
                <div className="mt-6 space-y-4">
                    {/* Summary Stats Card */}
                    <Card className="bg-gradient-to-br from-green-900/30 to-slate-900 border-green-500/30 p-6">
                        <div className="flex items-center gap-3 mb-4">
                            <div className="p-3 bg-green-500/20 rounded-full">
                                <FileCheck className="h-8 w-8 text-green-400" />
                            </div>
                            <div>
                                <h3 className="text-xl font-bold text-green-400">Scan Complete</h3>
                                <p className="text-slate-400 text-sm">Analysis finished successfully</p>
                            </div>
                        </div>

                        {/* Quick Stats */}
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                            <div className="bg-slate-800/50 rounded-lg p-3 text-center">
                                <Shield className="h-5 w-5 text-blue-400 mx-auto mb-1" />
                                <p className="text-2xl font-bold text-white">{candidates.filter(c => c.decision === 'yes').length}</p>
                                <p className="text-xs text-slate-400">Officers Approved</p>
                            </div>
                            <div className="bg-slate-800/50 rounded-lg p-3 text-center">
                                <ImageIcon className="h-5 w-5 text-purple-400 mx-auto mb-1" />
                                <p className="text-2xl font-bold text-white">{scrapedMedia.length}</p>
                                <p className="text-xs text-slate-400">Images Processed</p>
                            </div>
                            <div className="bg-slate-800/50 rounded-lg p-3 text-center">
                                <User className="h-5 w-5 text-yellow-400 mx-auto mb-1" />
                                <p className="text-2xl font-bold text-white">{candidates.length}</p>
                                <p className="text-xs text-slate-400">Total Detections</p>
                            </div>
                            <div className="bg-slate-800/50 rounded-lg p-3 text-center">
                                <Cpu className="h-5 w-5 text-green-400 mx-auto mb-1" />
                                <p className="text-2xl font-bold text-white">{(stats.confidence_avg * 100).toFixed(0)}%</p>
                                <p className="text-xs text-slate-400">Avg Confidence</p>
                            </div>
                        </div>

                        {/* Article Metadata - AI Analyzed */}
                        {articleMetadata && (
                            <div className="bg-gradient-to-br from-blue-900/30 to-slate-800/30 rounded-lg p-4 mb-6 border border-blue-700/50">
                                <h4 className="text-sm font-semibold text-blue-300 mb-3 flex items-center gap-2">
                                    <Cpu className="h-4 w-4" /> Article Analysis
                                </h4>

                                {/* Source Info */}
                                <div className="mb-4">
                                    <div className="text-lg font-semibold text-white mb-1">
                                        {articleMetadata.source_name}
                                    </div>
                                    <div className="text-sm text-slate-300 line-clamp-2">
                                        {articleMetadata.article_title}
                                    </div>
                                    <div className="flex items-center gap-4 mt-2 text-xs text-slate-400">
                                        <span className="flex items-center gap-1">
                                            <ImageIcon className="h-3 w-3" />
                                            {articleMetadata.image_count} images found
                                        </span>
                                        {articleMetadata.publication_date && (
                                            <span className="flex items-center gap-1">
                                                <Calendar className="h-3 w-3" />
                                                {new Date(articleMetadata.publication_date).toLocaleDateString()}
                                            </span>
                                        )}
                                    </div>
                                </div>

                                {/* AI-Extracted Event Details */}
                                {(articleMetadata.event_name || articleMetadata.location) && (
                                    <div className="bg-slate-800/50 rounded-lg p-3 mb-3">
                                        <div className="text-xs text-blue-400 font-medium mb-2">EVENT DETAILS</div>
                                        {articleMetadata.event_name && (
                                            <div className="text-sm font-medium text-white mb-1">
                                                {articleMetadata.event_name}
                                            </div>
                                        )}
                                        <div className="flex flex-wrap gap-3 text-xs text-slate-300">
                                            {articleMetadata.event_date && (
                                                <span className="flex items-center gap-1">
                                                    <Calendar className="h-3 w-3 text-blue-400" />
                                                    {articleMetadata.event_date}
                                                </span>
                                            )}
                                            {articleMetadata.location && (
                                                <span className="flex items-center gap-1">
                                                    <MapPin className="h-3 w-3 text-blue-400" />
                                                    {articleMetadata.location}
                                                </span>
                                            )}
                                            {articleMetadata.estimated_attendance && (
                                                <span className="flex items-center gap-1">
                                                    <User className="h-3 w-3 text-blue-400" />
                                                    {articleMetadata.estimated_attendance}
                                                </span>
                                            )}
                                        </div>
                                    </div>
                                )}

                                {/* AI Summary */}
                                {articleMetadata.summary && (
                                    <div className="mb-3">
                                        <div className="text-xs text-blue-400 font-medium mb-1">AI SUMMARY</div>
                                        <p className="text-sm text-slate-300 leading-relaxed">
                                            {articleMetadata.summary}
                                        </p>
                                    </div>
                                )}

                                {/* Police Presence */}
                                {articleMetadata.police_presence && (
                                    <div className="bg-red-900/20 rounded-lg p-3 mb-3 border border-red-700/30">
                                        <div className="text-xs text-red-400 font-medium mb-1 flex items-center gap-1">
                                            <Shield className="h-3 w-3" /> POLICE ACTIVITY
                                        </div>
                                        <p className="text-sm text-slate-300">
                                            {articleMetadata.police_presence}
                                        </p>
                                    </div>
                                )}

                                {/* Key Details */}
                                {articleMetadata.key_details && articleMetadata.key_details.length > 0 && (
                                    <div>
                                        <div className="text-xs text-blue-400 font-medium mb-2">KEY POINTS</div>
                                        <ul className="text-xs text-slate-400 space-y-1">
                                            {articleMetadata.key_details.map((detail, i) => (
                                                <li key={i} className="flex items-start gap-2">
                                                    <span className="text-blue-400 mt-0.5">•</span>
                                                    <span>{detail}</span>
                                                </li>
                                            ))}
                                        </ul>
                                    </div>
                                )}
                            </div>
                        )}

                        {/* Recon Data Summary (fallback if no article metadata) */}
                        {reconData && !articleMetadata && (
                            <div className="bg-slate-800/30 rounded-lg p-4 mb-6 border border-slate-700">
                                <h4 className="text-sm font-semibold text-slate-300 mb-3 flex items-center gap-2">
                                    <ZoomIn className="h-4 w-4" /> Source Analysis
                                </h4>
                                <div className="grid grid-cols-2 gap-4 text-sm">
                                    {reconData.meta?.date && (
                                        <div className="flex items-center gap-2 text-slate-400">
                                            <Calendar className="h-4 w-4" />
                                            <span>{reconData.meta.date}</span>
                                        </div>
                                    )}
                                    {reconData.meta?.location && (
                                        <div className="flex items-center gap-2 text-slate-400">
                                            <MapPin className="h-4 w-4" />
                                            <span>{reconData.meta.location}</span>
                                        </div>
                                    )}
                                    {reconData.category && (
                                        <div className="text-slate-400">
                                            <span className="text-slate-500">Type:</span> {reconData.category}
                                        </div>
                                    )}
                                    {reconData.score !== undefined && (
                                        <div className="text-slate-400">
                                            <span className="text-slate-500">Relevance:</span> {reconData.score}/100
                                        </div>
                                    )}
                                </div>
                            </div>
                        )}

                        {/* Action Button */}
                        <Button
                            onClick={() => {
                                // Pass approved candidates along with media ID
                                const approvedCandidates = candidates.filter(c => c.decision === 'yes' || !c.reviewed);
                                onComplete(mediaId, approvedCandidates);
                            }}
                            className="w-full bg-green-600 hover:bg-green-500 text-white py-6 text-lg font-semibold"
                            size="lg"
                        >
                            <FileCheck className="h-5 w-5 mr-2" />
                            View Full Report
                        </Button>
                    </Card>
                </div>
            )}
        </div>
    );
}

// Custom animation styles - add to your global CSS or tailwind config
// These animations power the stage visualizers
const animationStyles = `
@keyframes fly-packet {
    0% { left: 0; opacity: 0; transform: translateY(-50%) scale(0.5); }
    10% { opacity: 1; transform: translateY(-50%) scale(1); }
    90% { opacity: 1; transform: translateY(-50%) scale(1); }
    100% { left: 100%; opacity: 0; transform: translateY(-50%) scale(0.5); }
}

@keyframes scan-vertical {
    0% { top: 0; }
    50% { top: 100%; }
    100% { top: 0; }
}

@keyframes scan-horizontal {
    0% { top: 0; }
    100% { top: 100%; }
}

@keyframes shimmer {
    0% { transform: translateX(-100%); }
    100% { transform: translateX(100%); }
}

@keyframes bounce-slow {
    0%, 100% { transform: translateY(0); }
    50% { transform: translateY(-10px); }
}

.animate-fly-packet {
    animation: fly-packet 1.5s ease-in-out infinite;
}

.animate-scan-vertical {
    animation: scan-vertical 2s ease-in-out infinite;
}

.animate-scan-horizontal {
    animation: scan-horizontal 2s linear infinite;
}

.animate-shimmer {
    animation: shimmer 2s infinite;
}

.animate-bounce-slow {
    animation: bounce-slow 2s ease-in-out infinite;
}
`;

// Inject animation styles into document head
if (typeof document !== 'undefined') {
    const styleId = 'live-analysis-animations';
    if (!document.getElementById(styleId)) {
        const styleSheet = document.createElement('style');
        styleSheet.id = styleId;
        styleSheet.textContent = animationStyles;
        document.head.appendChild(styleSheet);
    }
}

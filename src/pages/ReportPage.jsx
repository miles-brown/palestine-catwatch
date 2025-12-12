import { useEffect, useState, useRef } from 'react';
import { useParams, Link } from 'react-router-dom';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Printer, ArrowLeft, Shield, AlertTriangle, Clock, User, Video, Image as ImageIcon, MapPin, Calendar, ExternalLink, CheckCircle, Heart, FileText, Users, Camera } from 'lucide-react';
import VideoPlayer from '@/components/VideoPlayer';
import UniformAnalysisCard from '@/components/UniformAnalysisCard';
import { API_BASE, getMediaUrl, sanitizeMediaPath } from '../utils/api';

export default function ReportPage() {
    const { mediaId } = useParams();
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [selectedOfficer, setSelectedOfficer] = useState(null);
    const [activeTab, setActiveTab] = useState('video'); // 'video' or 'officers'
    const videoPlayerRef = useRef(null);

    useEffect(() => {
        fetch(`${API_BASE}/media/${mediaId}/report`)
            .then(res => {
                if (!res.ok) throw new Error("Failed to fetch report");
                return res.json();
            })
            .then(setData)
            .catch(err => setError(err.message))
            .finally(() => setLoading(false));
    }, [mediaId]);

    const handleMarkerClick = (marker) => {
        // Find and highlight the corresponding officer
        const officer = data?.officers.find(o => o.id === marker.officer_id);
        if (officer) {
            setSelectedOfficer(officer);
            setActiveTab('officers');
            // Scroll to officer card
            setTimeout(() => {
                document.getElementById(`officer-${officer.id}`)?.scrollIntoView({
                    behavior: 'smooth',
                    block: 'center'
                });
            }, 100);
        }
    };

    const handleOfficerTimestampClick = (timestamp) => {
        setActiveTab('video');
        // VideoPlayer will handle seeking via its timeline
    };

    // Use imported getMediaUrl for secure path handling
    // Local alias for internal URL handling with http check
    const getLocalMediaUrl = (url) => {
        if (!url) return '';
        if (url.startsWith('http://') || url.startsWith('https://')) {
            return url;
        }
        const cleanPath = sanitizeMediaPath(url);
        if (!cleanPath) return '';
        return `${API_BASE}/data/${cleanPath}`;
    };

    // Use centralized utility for crop URLs
    const getCropUrl = getMediaUrl;

    if (loading) {
        return (
            <div className="min-h-screen bg-gray-50 flex items-center justify-center">
                <div className="text-center">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-green-600 mx-auto mb-4"></div>
                    <p className="text-gray-600">Loading Analysis Report...</p>
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="min-h-screen bg-gray-50 flex items-center justify-center">
                <div className="text-center">
                    <AlertTriangle className="h-12 w-12 text-red-500 mx-auto mb-4" />
                    <h2 className="text-xl font-bold text-gray-900 mb-2">Error Loading Report</h2>
                    <p className="text-red-500 mb-4">{error}</p>
                    <Link to="/upload">
                        <Button>Back to Upload</Button>
                    </Link>
                </div>
            </div>
        );
    }

    if (!data) {
        return (
            <div className="min-h-screen bg-gray-50 flex items-center justify-center">
                <div className="text-center">
                    <p className="text-gray-600">No data found for this report.</p>
                    <Link to="/upload">
                        <Button className="mt-4">Back to Upload</Button>
                    </Link>
                </div>
            </div>
        );
    }

    const { media, protest, stats, officers, timeline } = data;
    const isVideo = media.type === 'video';

    return (
        <div className="min-h-screen bg-gray-50 print:bg-white">
            {/* Navigation Header - Hidden on Print */}
            <div className="bg-white border-b border-gray-200 print:hidden sticky top-0 z-30">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3 flex justify-between items-center">
                    <Link to="/upload">
                        <Button variant="ghost" size="sm">
                            <ArrowLeft className="h-4 w-4 mr-2" /> Back to Upload
                        </Button>
                    </Link>
                    <div className="flex items-center gap-2">
                        <span className="text-sm text-gray-500">Report #{media.id}</span>
                        <Button onClick={() => window.print()} size="sm">
                            <Printer className="h-4 w-4 mr-2" /> Print
                        </Button>
                    </div>
                </div>
            </div>

            {/* Main Content */}
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 print:py-0 print:px-0">
                {/* Report Header */}
                <div className="bg-slate-900 text-white rounded-t-xl p-6 print:rounded-none print:bg-gray-100 print:text-black">
                    <div className="flex flex-col md:flex-row md:justify-between md:items-start gap-4">
                        <div>
                            <div className="flex items-center gap-2 mb-2">
                                {isVideo ? (
                                    <Video className="h-5 w-5 text-green-400 print:text-green-600" />
                                ) : (
                                    <ImageIcon className="h-5 w-5 text-blue-400 print:text-blue-600" />
                                )}
                                <span className="text-sm text-gray-400 print:text-gray-600 uppercase tracking-wider">
                                    {media.type} Analysis
                                </span>
                            </div>
                            <h1 className="text-2xl md:text-3xl font-bold mb-2">Analysis Report</h1>
                            <p className="text-slate-400 print:text-gray-600 text-sm">
                                ID: {media.id} | {new Date(media.timestamp).toLocaleString()}
                            </p>
                        </div>
                        <div className="text-left md:text-right">
                            <h2 className="text-xl font-bold text-green-400 print:text-green-700">
                                {protest.name}
                            </h2>
                            <p className="text-sm text-slate-400 print:text-gray-600">
                                {protest.location}
                            </p>
                            {protest.date && (
                                <p className="text-sm text-slate-500 print:text-gray-500">
                                    {new Date(protest.date).toLocaleDateString()}
                                </p>
                            )}
                        </div>
                    </div>
                </div>

                {/* Stats Bar */}
                <div className="grid grid-cols-3 bg-white border-x border-b border-gray-200">
                    <div className="p-4 text-center border-r border-gray-200">
                        <p className="text-xs uppercase text-gray-500 font-bold mb-1">Officers Identified</p>
                        <p className="text-2xl md:text-3xl font-bold text-slate-800">{stats.total_officers}</p>
                    </div>
                    <div className="p-4 text-center border-r border-gray-200">
                        <p className="text-xs uppercase text-gray-500 font-bold mb-1">Total Appearances</p>
                        <p className="text-2xl md:text-3xl font-bold text-slate-800">{stats.total_appearances}</p>
                    </div>
                    <div className="p-4 text-center bg-gray-50">
                        <p className="text-xs uppercase text-gray-500 font-bold mb-1">Timeline Markers</p>
                        <p className="text-2xl md:text-3xl font-bold text-yellow-600">{timeline?.length || 0}</p>
                    </div>
                </div>

                {/* Tab Navigation - Hidden on Print */}
                {isVideo && timeline?.length > 0 && (
                    <div className="bg-white border-x border-gray-200 px-4 print:hidden">
                        <div className="flex gap-4 border-b border-gray-200">
                            <button
                                onClick={() => setActiveTab('video')}
                                className={`py-3 px-4 font-medium text-sm border-b-2 transition ${
                                    activeTab === 'video'
                                        ? 'border-green-600 text-green-600'
                                        : 'border-transparent text-gray-500 hover:text-gray-700'
                                }`}
                            >
                                <Video className="h-4 w-4 inline mr-2" />
                                Video Timeline
                            </button>
                            <button
                                onClick={() => setActiveTab('officers')}
                                className={`py-3 px-4 font-medium text-sm border-b-2 transition ${
                                    activeTab === 'officers'
                                        ? 'border-green-600 text-green-600'
                                        : 'border-transparent text-gray-500 hover:text-gray-700'
                                }`}
                            >
                                <Shield className="h-4 w-4 inline mr-2" />
                                Officers ({officers.length})
                            </button>
                        </div>
                    </div>
                )}

                {/* Video Player Section */}
                {isVideo && (activeTab === 'video' || !timeline?.length) && (
                    <div className="bg-white border-x border-b border-gray-200 p-4 print:hidden">
                        <VideoPlayer
                            ref={videoPlayerRef}
                            url={media.url}
                            timeline={timeline || []}
                            onMarkerClick={handleMarkerClick}
                            apiBase={API_BASE}
                        />

                        {/* Enhanced Timeline Strip */}
                        {timeline && timeline.length > 0 && (
                            <div className="mt-4 border-t border-gray-200 pt-4">
                                <div className="flex items-center justify-between mb-3">
                                    <h4 className="text-sm font-semibold text-gray-700 flex items-center gap-2">
                                        <Clock className="h-4 w-4" />
                                        Detection Timeline ({timeline.length} events)
                                    </h4>
                                    <div className="flex items-center gap-2 text-xs text-gray-500">
                                        <span className="flex items-center gap-1">
                                            <div className="w-3 h-3 rounded-full bg-green-500"></div>
                                            Officer detected
                                        </span>
                                    </div>
                                </div>

                                {/* Scrollable Timeline */}
                                <div className="relative">
                                    <div className="overflow-x-auto pb-2">
                                        <div className="flex gap-2 min-w-max">
                                            {timeline.map((marker, idx) => {
                                                const officer = officers.find(o => o.id === marker.officer_id);
                                                const cropUrl = officer?.crop_path ? getCropUrl(officer.crop_path) : null;

                                                return (
                                                    <button
                                                        key={idx}
                                                        onClick={() => handleMarkerClick(marker)}
                                                        className={`flex-shrink-0 p-2 rounded-lg border transition-all hover:shadow-md ${
                                                            selectedOfficer?.id === marker.officer_id
                                                                ? 'border-green-500 bg-green-50 ring-2 ring-green-200'
                                                                : 'border-gray-200 bg-white hover:border-green-300'
                                                        }`}
                                                        title={`${marker.timestamp} - ${marker.action || 'Officer detected'}`}
                                                    >
                                                        <div className="flex items-center gap-2">
                                                            {cropUrl ? (
                                                                <img
                                                                    src={cropUrl}
                                                                    alt=""
                                                                    className="w-10 h-10 rounded-full object-cover border border-gray-200"
                                                                    onError={(e) => {
                                                                        e.target.style.display = 'none';
                                                                    }}
                                                                />
                                                            ) : (
                                                                <div className="w-10 h-10 rounded-full bg-gray-100 flex items-center justify-center">
                                                                    <User className="h-5 w-5 text-gray-400" />
                                                                </div>
                                                            )}
                                                            <div className="text-left">
                                                                <div className="text-xs font-mono font-medium text-gray-900">
                                                                    {marker.timestamp}
                                                                </div>
                                                                <div className="text-xs text-gray-500 truncate max-w-[80px]">
                                                                    {marker.badge || `#${marker.officer_id}`}
                                                                </div>
                                                            </div>
                                                        </div>
                                                    </button>
                                                );
                                            })}
                                        </div>
                                    </div>

                                    {/* Scroll indicators */}
                                    {timeline.length > 5 && (
                                        <>
                                            <div className="absolute left-0 top-0 bottom-2 w-8 bg-gradient-to-r from-white to-transparent pointer-events-none"></div>
                                            <div className="absolute right-0 top-0 bottom-2 w-8 bg-gradient-to-l from-white to-transparent pointer-events-none"></div>
                                        </>
                                    )}
                                </div>

                                {/* Timeline Summary by Officer */}
                                <div className="mt-4 grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2">
                                    {officers.slice(0, 8).map((officer, idx) => {
                                        const officerEvents = timeline.filter(m => m.officer_id === officer.id);
                                        if (officerEvents.length === 0) return null;

                                        return (
                                            <button
                                                key={officer.id}
                                                onClick={() => {
                                                    setSelectedOfficer(officer);
                                                    setActiveTab('officers');
                                                    setTimeout(() => {
                                                        document.getElementById(`officer-${officer.id}`)?.scrollIntoView({
                                                            behavior: 'smooth',
                                                            block: 'center'
                                                        });
                                                    }, 100);
                                                }}
                                                className={`p-2 rounded-lg text-left transition-all ${
                                                    selectedOfficer?.id === officer.id
                                                        ? 'bg-green-100 border-green-500'
                                                        : 'bg-gray-50 hover:bg-gray-100'
                                                } border`}
                                            >
                                                <div className="flex items-center gap-2">
                                                    <Shield className="h-4 w-4 text-green-600 flex-shrink-0" />
                                                    <div className="min-w-0">
                                                        <div className="text-xs font-medium text-gray-900 truncate">
                                                            {officer.badge || `Officer #${idx + 1}`}
                                                        </div>
                                                        <div className="text-xs text-gray-500">
                                                            {officerEvents.length} appearance{officerEvents.length !== 1 ? 's' : ''}
                                                        </div>
                                                    </div>
                                                </div>
                                            </button>
                                        );
                                    })}
                                </div>
                            </div>
                        )}
                    </div>
                )}

                {/* Officers Grid */}
                {(activeTab === 'officers' || !isVideo || !timeline?.length) && (
                    <div className="bg-white border-x border-b border-gray-200 rounded-b-xl p-6 print:rounded-none">
                        <h3 className="text-lg font-bold text-slate-900 mb-6 flex items-center gap-2">
                            <Shield className="h-5 w-5 text-green-600" />
                            Identified Officers
                        </h3>

                        {officers.length === 0 ? (
                            <div className="text-center py-12">
                                <User className="h-12 w-12 text-gray-300 mx-auto mb-4" />
                                <p className="text-gray-500">No officers were identified in this footage.</p>
                            </div>
                        ) : (
                            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
                                {officers.map((officer, i) => (
                                    <div
                                        key={officer.id}
                                        id={`officer-${officer.id}`}
                                        className={`border rounded-lg overflow-hidden transition-all break-inside-avoid ${
                                            selectedOfficer?.id === officer.id
                                                ? 'border-green-500 ring-2 ring-green-200'
                                                : 'border-gray-200 hover:border-gray-300'
                                        }`}
                                    >
                                        {/* Officer Image */}
                                        <div className="aspect-square bg-gray-100 relative">
                                            {officer.crop_path ? (
                                                <img
                                                    src={getCropUrl(officer.crop_path)}
                                                    className="w-full h-full object-cover"
                                                    alt={`Officer ${i + 1}`}
                                                    onError={(e) => {
                                                        e.target.style.display = 'none';
                                                        e.target.nextSibling.style.display = 'flex';
                                                    }}
                                                />
                                            ) : null}
                                            <div
                                                className={`w-full h-full items-center justify-center text-gray-400 ${
                                                    officer.crop_path ? 'hidden' : 'flex'
                                                }`}
                                            >
                                                <User className="h-16 w-16" />
                                            </div>
                                            <div className="absolute top-2 left-2 bg-black/70 text-white text-xs px-2 py-1 rounded">
                                                Officer #{i + 1}
                                            </div>
                                            {officer.total_appearances_in_video > 1 && (
                                                <div className="absolute top-2 right-2 bg-yellow-500 text-black text-xs px-2 py-1 rounded font-bold">
                                                    {officer.total_appearances_in_video} appearances
                                                </div>
                                            )}
                                        </div>

                                        {/* Officer Details */}
                                        <div className="p-4 space-y-3">
                                            <div>
                                                <span className="text-xs text-gray-500 uppercase font-bold">Badge Number</span>
                                                <p className="font-mono font-medium text-lg">
                                                    {officer.badge || "Unknown"}
                                                </p>
                                            </div>

                                            <div className="grid grid-cols-2 gap-2">
                                                <div>
                                                    <span className="text-xs text-gray-500 uppercase font-bold">Force</span>
                                                    <p className="text-sm">{officer.force || "Unknown"}</p>
                                                </div>
                                                <div>
                                                    <span className="text-xs text-gray-500 uppercase font-bold">Role</span>
                                                    <p className="text-sm">{officer.role || "Unknown"}</p>
                                                </div>
                                            </div>

                                            {/* Timestamps for this officer */}
                                            {officer.timestamps && officer.timestamps.length > 0 && (
                                                <div className="pt-2 border-t border-gray-100">
                                                    <span className="text-xs text-gray-500 uppercase font-bold flex items-center gap-1 mb-2">
                                                        <Clock className="h-3 w-3" />
                                                        Timestamps
                                                    </span>
                                                    <div className="flex flex-wrap gap-1">
                                                        {officer.timestamps.slice(0, 5).map((ts, idx) => (
                                                            <button
                                                                key={idx}
                                                                onClick={() => handleOfficerTimestampClick(ts.timestamp)}
                                                                className="text-xs bg-gray-100 hover:bg-green-100 text-gray-700 hover:text-green-700 px-2 py-1 rounded font-mono transition print:bg-gray-200"
                                                                title={ts.action || 'Jump to timestamp'}
                                                            >
                                                                {ts.timestamp}
                                                            </button>
                                                        ))}
                                                        {officer.timestamps.length > 5 && (
                                                            <span className="text-xs text-gray-400 px-2 py-1">
                                                                +{officer.timestamps.length - 5} more
                                                            </span>
                                                        )}
                                                    </div>
                                                </div>
                                            )}

                                            {/* Uniform Analysis Card */}
                                            <div className="pt-2 border-t border-gray-100 print:hidden">
                                                <UniformAnalysisCard
                                                    officerId={officer.id}
                                                    appearanceId={officer.timestamps?.[0]?.appearance_id || officer.id}
                                                    cropPath={officer.crop_path}
                                                    compact={true}
                                                />
                                            </div>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                )}

                {/* Print-only: Timeline Summary */}
                <div className="hidden print:block bg-white p-6 border border-gray-200 mt-4">
                    <h3 className="text-lg font-bold mb-4">Detection Timeline</h3>
                    <table className="w-full text-sm">
                        <thead>
                            <tr className="border-b">
                                <th className="text-left py-2">Timestamp</th>
                                <th className="text-left py-2">Officer</th>
                                <th className="text-left py-2">Badge</th>
                                <th className="text-left py-2">Action</th>
                            </tr>
                        </thead>
                        <tbody>
                            {timeline?.map((marker, idx) => (
                                <tr key={idx} className="border-b">
                                    <td className="py-2 font-mono">{marker.timestamp}</td>
                                    <td className="py-2">#{marker.officer_id}</td>
                                    <td className="py-2">{marker.badge || '-'}</td>
                                    <td className="py-2 text-gray-600">{marker.action || '-'}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>

                {/* Thank You & Summary Section */}
                <div className="bg-gradient-to-br from-green-50 to-slate-50 rounded-xl p-6 mt-6 border border-green-200">
                    <div className="flex items-start gap-4">
                        <div className="p-3 bg-green-100 rounded-full">
                            <Heart className="h-6 w-6 text-green-600" />
                        </div>
                        <div className="flex-1">
                            <h3 className="text-lg font-bold text-slate-900 mb-2">
                                Thank You for Your Contribution
                            </h3>
                            <p className="text-slate-600 text-sm mb-4">
                                Your submission helps document police conduct at Palestine solidarity demonstrations.
                                This evidence contributes to transparency and accountability in public order policing.
                            </p>

                            {/* Summary Stats */}
                            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
                                <div className="bg-white rounded-lg p-3 border border-slate-200 text-center">
                                    <Shield className="h-5 w-5 text-blue-500 mx-auto mb-1" />
                                    <p className="text-xl font-bold text-slate-800">{stats.total_officers}</p>
                                    <p className="text-xs text-slate-500">Officers Identified</p>
                                </div>
                                <div className="bg-white rounded-lg p-3 border border-slate-200 text-center">
                                    <Camera className="h-5 w-5 text-purple-500 mx-auto mb-1" />
                                    <p className="text-xl font-bold text-slate-800">{stats.total_appearances}</p>
                                    <p className="text-xs text-slate-500">Total Appearances</p>
                                </div>
                                <div className="bg-white rounded-lg p-3 border border-slate-200 text-center">
                                    <FileText className="h-5 w-5 text-green-500 mx-auto mb-1" />
                                    <p className="text-xl font-bold text-slate-800">1</p>
                                    <p className="text-xs text-slate-500">Source Analyzed</p>
                                </div>
                                <div className="bg-white rounded-lg p-3 border border-slate-200 text-center">
                                    <Users className="h-5 w-5 text-yellow-500 mx-auto mb-1" />
                                    <p className="text-xl font-bold text-slate-800">{timeline?.length || 0}</p>
                                    <p className="text-xs text-slate-500">Timeline Events</p>
                                </div>
                            </div>

                            {/* Context Info */}
                            <div className="bg-white rounded-lg p-4 border border-slate-200">
                                <h4 className="text-sm font-semibold text-slate-700 mb-3">Submission Details</h4>
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
                                    <div className="flex items-center gap-2 text-slate-600">
                                        <Calendar className="h-4 w-4 text-slate-400" />
                                        <span className="font-medium">Protest Date:</span>
                                        <span>{protest.date ? new Date(protest.date).toLocaleDateString('en-GB', { day: 'numeric', month: 'long', year: 'numeric' }) : 'Unknown'}</span>
                                    </div>
                                    <div className="flex items-center gap-2 text-slate-600">
                                        <MapPin className="h-4 w-4 text-slate-400" />
                                        <span className="font-medium">Location:</span>
                                        <span>{protest.location || 'Unknown'}</span>
                                    </div>
                                    <div className="flex items-center gap-2 text-slate-600">
                                        {isVideo ? <Video className="h-4 w-4 text-slate-400" /> : <ImageIcon className="h-4 w-4 text-slate-400" />}
                                        <span className="font-medium">Media Type:</span>
                                        <span className="capitalize">{media.type}</span>
                                    </div>
                                    <div className="flex items-center gap-2 text-slate-600">
                                        <Clock className="h-4 w-4 text-slate-400" />
                                        <span className="font-medium">Processed:</span>
                                        <span>{new Date(media.timestamp).toLocaleString('en-GB')}</span>
                                    </div>
                                </div>
                            </div>

                            {/* Action Buttons */}
                            <div className="flex flex-wrap gap-3 mt-4">
                                <Link to="/upload">
                                    <Button className="bg-green-600 hover:bg-green-700 text-white">
                                        <CheckCircle className="h-4 w-4 mr-2" />
                                        Submit More Evidence
                                    </Button>
                                </Link>
                                <Link to="/dashboard">
                                    <Button variant="outline" className="border-slate-300">
                                        View Dashboard
                                    </Button>
                                </Link>
                                <Button variant="outline" className="border-slate-300" onClick={() => window.print()}>
                                    <Printer className="h-4 w-4 mr-2" />
                                    Print Report
                                </Button>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Footer */}
                <div className="bg-slate-900 rounded-xl p-6 text-center mt-6 print:bg-gray-100 print:text-black">
                    <p className="text-slate-400 print:text-gray-600 text-sm">
                        Generated by <span className="font-semibold text-white print:text-black">Palestine Accountability Campaign</span>
                    </p>
                    <p className="text-slate-500 print:text-gray-500 text-xs mt-2">
                        {new Date().toLocaleString('en-GB')} | Report #{media.id}
                    </p>
                    <p className="text-slate-600 print:text-gray-400 text-xs mt-3">
                        This report is for documentation and research purposes only.
                    </p>
                </div>
            </div>
        </div>
    );
}

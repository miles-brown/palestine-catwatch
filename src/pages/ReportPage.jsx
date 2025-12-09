
import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Printer, ArrowLeft, Shield, AlertTriangle } from 'lucide-react';

let API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";
if (!API_BASE.startsWith("http")) {
    API_BASE = `https://${API_BASE}`;
}

export default function ReportPage() {
    const { mediaId } = useParams();
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

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

    if (loading) return <div className="p-8 text-center">Loading Report...</div>;
    if (error) return <div className="p-8 text-center text-red-500">Error: {error}</div>;
    if (!data) return <div className="p-8 text-center">No data found.</div>;

    const { media, protest, stats, officers } = data;

    return (
        <div className="min-h-screen bg-gray-50 p-8 print:bg-white print:p-0">
            {/* No Print Header */}
            <div className="max-w-4xl mx-auto mb-8 flex justify-between items-center print:hidden">
                <Link to="/upload">
                    <Button variant="ghost">
                        <ArrowLeft className="h-4 w-4 mr-2" /> Back to Upload
                    </Button>
                </Link>
                <Button onClick={() => window.print()}>
                    <Printer className="h-4 w-4 mr-2" /> Print Report
                </Button>
            </div>

            {/* Report Content */}
            <div className="max-w-4xl mx-auto bg-white shadow-lg rounded-xl overflow-hidden print:shadow-none">
                {/* Header */}
                <div className="bg-slate-900 text-white p-8 print:bg-gray-100 print:text-black">
                    <div className="flex justify-between items-start">
                        <div>
                            <h1 className="text-3xl font-bold mb-2">Analysis Report</h1>
                            <p className="text-slate-400 print:text-gray-600">ID: {media.id} • {new Date(media.timestamp).toLocaleString()}</p>
                        </div>
                        <div className="text-right">
                            <h2 className="text-xl font-bold text-green-400 print:text-black">{protest.name}</h2>
                            <p className="text-sm text-slate-400 print:text-gray-600">{protest.location}</p>
                        </div>
                    </div>
                </div>

                {/* Stats */}
                <div className="grid grid-cols-3 border-b border-gray-200">
                    <div className="p-6 text-center border-r border-gray-200">
                        <p className="text-xs uppercase text-gray-500 font-bold mb-1">Total Identified</p>
                        <p className="text-3xl font-bold text-slate-800">{stats.total_officers}</p>
                    </div>
                    <div className="p-6 text-center border-r border-gray-200">
                        <p className="text-xs uppercase text-gray-500 font-bold mb-1">Total Sightings</p>
                        <p className="text-3xl font-bold text-slate-800">{stats.total_appearances}</p>
                    </div>
                    <div className="p-6 text-center bg-gray-50">
                        <p className="text-xs uppercase text-gray-500 font-bold mb-1">Source</p>
                        <p className="text-sm font-medium text-slate-700 truncate max-w-[200px]" title={media.url}>
                            {media.type.toUpperCase()}
                        </p>
                    </div>
                </div>

                {/* Officers Grid */}
                <div className="p-8">
                    <h3 className="text-lg font-bold text-slate-900 mb-6 flex items-center gap-2">
                        <Shield className="h-5 w-5 text-green-600" />
                        Identified Officers
                    </h3>

                    {officers.length === 0 ? (
                        <p className="text-gray-500 italic">No officers were definitively identified in this footage.</p>
                    ) : (
                        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-6">
                            {officers.map((officer, i) => (
                                <div key={officer.id} className="border border-gray-200 rounded-lg overflow-hidden break-inside-avoid">
                                    <div className="aspect-square bg-gray-100 relative">
                                        {officer.crop_path ? (
                                            <img
                                                src={`${API_BASE}/data/${officer.crop_path.split('data/')[1]}`}
                                                className="w-full h-full object-cover"
                                                alt={`Officer ${i + 1}`}
                                            />
                                        ) : (
                                            <div className="w-full h-full flex items-center justify-center text-gray-400">
                                                No Image
                                            </div>
                                        )}
                                        <div className="absolute top-2 left-2 bg-black/70 text-white text-xs px-2 py-1 rounded">
                                            Officer #{i + 1}
                                        </div>
                                    </div>
                                    <div className="p-4 space-y-2">
                                        <div>
                                            <span className="text-xs text-gray-500 uppercase font-bold">Badge Number</span>
                                            <p className="font-mono font-medium">{officer.badge || "Unknown"}</p>
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
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>

                {/* Footer */}
                <div className="bg-gray-50 p-6 text-center text-xs text-gray-500 border-t border-gray-200">
                    Generated by Palestine Catwatch AI • {new Date().toLocaleString()}
                </div>
            </div>
        </div>
    );
}

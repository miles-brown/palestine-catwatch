import { useEffect, useState, useRef } from 'react';
import { io } from 'socket.io-client';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Terminal, Cpu, Shield, AlertTriangle, Check, X, Server, Activity } from 'lucide-react';

let API_URL = import.meta.env.VITE_API_BASE || 'http://localhost:8000';
if (!API_URL.startsWith("http")) {
    API_URL = `https://${API_URL}`;
}

export default function LiveAnalysis({ taskId, onComplete }) {
    const [logs, setLogs] = useState([]);
    const [candidates, setCandidates] = useState([]);
    const [status, setStatus] = useState('connecting'); // connecting, active, complete, error
    const [stats, setStats] = useState({ faces: 0, objects: 0, confidence_avg: 0 });
    const logEndRef = useRef(null);
    const socketRef = useRef(null);

    useEffect(() => {
        // Connect to WebSocket
        const socket = io(API_URL, {
            path: '/socket.io',
            transports: ['websocket'],
        });
        socketRef.current = socket;

        socket.on('connect', () => {
            addLog('System', 'Connected to analysis server.');
            setStatus('active');
            socket.emit('join_task', taskId);
        });

        socket.on('disconnect', () => {
            addLog('System', 'Disconnected from server.');
        });

        socket.on('log_message', (data) => {
            addLog('System', data.message);
        });

        // Custom events from backend
        socket.on('log', (msg) => {
            addLog('Info', msg);
        });


        socket.on('candidate_officer', (data) => {
            addLog('AI', `Candidate detected with ${(data.confidence * 100).toFixed(1)}% confidence.`);
            setCandidates(prev => [...prev, { ...data, id: Date.now(), reviewed: false }]);
            setStats(s => ({ ...s, faces: s.faces + 1, confidence_avg: (s.confidence_avg + data.confidence) / 2 }));
        });

        socket.on('complete', (msg) => {
            addLog('System', msg);
            setStatus('complete');
        });

        return () => {
            socket.disconnect();
        };
    }, [taskId]);

    // Auto-scroll logs
    useEffect(() => {
        logEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [logs]);

    const addLog = (source, message) => {
        setLogs(prev => [...prev, { time: new Date().toLocaleTimeString(), source, message }]);
    };

    const handledecision = (id, decision) => {
        // In a real app, send API call to update DB
        console.log(`User decision for ${id}: ${decision}`);
        setCandidates(prev => prev.map(c => c.id === id ? { ...c, reviewed: true, decision } : c));
    };

    return (
        <div className="min-h-screen bg-slate-950 text-slate-200 p-6 font-mono">
            {/* Header / HUD */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
                <Card className="bg-slate-900 border-slate-800 p-4 flex items-center gap-4">
                    <div className="p-3 bg-blue-500/10 rounded-full text-blue-400">
                        <Activity className="h-6 w-6 animate-pulse" />
                    </div>
                    <div>
                        <p className="text-xs text-slate-500 uppercase tracking-wider">Status</p>
                        <p className="font-bold text-lg text-blue-400">
                            {status === 'active' ? 'PROCESSING' : status.toUpperCase()}
                        </p>
                    </div>
                </Card>

                <Card className="bg-slate-900 border-slate-800 p-4 flex items-center gap-4">
                    <div className="p-3 bg-green-500/10 rounded-full text-green-400">
                        <Shield className="h-6 w-6" />
                    </div>
                    <div>
                        <p className="text-xs text-slate-500 uppercase tracking-wider">Officers Found</p>
                        <p className="font-bold text-lg text-slate-100">{stats.faces}</p>
                    </div>
                </Card>

                <Card className="bg-slate-900 border-slate-800 p-4 flex items-center gap-4">
                    <div className="p-3 bg-purple-500/10 rounded-full text-purple-400">
                        <Cpu className="h-6 w-6" />
                    </div>
                    <div>
                        <p className="text-xs text-slate-500 uppercase tracking-wider">Avg Confidence</p>
                        <p className="font-bold text-lg text-slate-100">{(stats.confidence_avg * 100).toFixed(1)}%</p>
                    </div>
                </Card>

                <Card className="bg-slate-900 border-slate-800 p-4 flex items-center gap-4">
                    <div className="p-3 bg-orange-500/10 rounded-full text-orange-400">
                        <Server className="h-6 w-6" />
                    </div>
                    <div>
                        <p className="text-xs text-slate-500 uppercase tracking-wider">Task ID</p>
                        <p className="font-bold text-sm text-slate-100 truncate w-32">{taskId}</p>
                    </div>
                </Card>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 h-[700px]">
                {/* Terminal Log */}
                <Card className="bg-slate-900 border-slate-800 col-span-1 flex flex-col h-full overflow-hidden shadow-2xl shadow-blue-900/5">
                    <div className="p-3 border-b border-slate-800 bg-slate-950 flex items-center gap-2">
                        <Terminal className="h-4 w-4 text-slate-400" />
                        <span className="text-xs font-semibold text-slate-400">SYSTEM LOG</span>
                    </div>
                    <div className="flex-1 overflow-y-auto p-4 font-mono text-xs space-y-2">
                        {logs.length === 0 && (
                            <div className="text-slate-500 italic p-4 text-center opacity-50">
                                Waiting for connection... <br />
                                If this persists, check your network or server logs.
                            </div>
                        )}
                        {logs.map((log, i) => (
                            <div key={i} className="flex gap-2">
                                <span className="text-slate-600">[{log.time}]</span>
                                <span className={`${log.source === 'Error' ? 'text-red-400' : 'text-blue-400'} font-bold`}>
                                    {log.source}:
                                </span>
                                <span className="text-slate-300">{log.message}</span>
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
                        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
                            {candidates.length === 0 && status === 'active' && (
                                <div className="col-span-full h-64 flex flex-col items-center justify-center text-slate-600 animate-pulse">
                                    <Cpu className="h-12 w-12 mb-4 opacity-50" />
                                    <p>Analyzing stream for targets...</p>
                                </div>
                            )}

                            {candidates.map((c) => (
                                <Card key={c.id} className={`bg-slate-950 border ${c.reviewed ? (c.decision === 'yes' ? 'border-green-500/50' : 'border-red-500/50') : 'border-slate-700'} overflow-hidden`}>
                                    <div className="relative aspect-video bg-slate-900 group">
                                        <img src={`${API_URL}${c.image_url}`} className="w-full h-full object-cover" alt="Candidate" />
                                        <div className="absolute top-2 left-2 bg-black/70 px-2 py-1 rounded text-xs text-white">
                                            {c.timestamp}
                                        </div>
                                        {c.quality?.is_blurry && (
                                            <div className="absolute top-2 right-2 bg-yellow-500/90 text-black px-2 py-1 rounded text-xs font-bold flex items-center gap-1">
                                                <AlertTriangle className="h-3 w-3" /> BLURRY
                                            </div>
                                        )}
                                    </div>
                                    <div className="p-3 space-y-3">
                                        {/* Status Bar */}
                                        <div className="flex justify-between items-center text-xs">
                                            <span className="text-slate-400">Confidence</span>
                                            <span className="font-bold text-green-400">{(c.confidence * 100).toFixed(0)}%</span>
                                        </div>

                                        {/* Analysis Data */}
                                        <div className="space-y-2 bg-slate-900 p-2 rounded border border-slate-800">
                                            {/* Badge OCR */}
                                            <div>
                                                <label className="text-[10px] uppercase text-slate-500 font-bold block mb-1">Badge Number (OCR)</label>
                                                <input
                                                    type="text"
                                                    defaultValue={c.badge || ""}
                                                    placeholder="Not detected"
                                                    className="w-full bg-slate-950 border border-slate-700 rounded px-2 py-1 text-xs text-slate-200 focus:border-blue-500 outline-none"
                                                />
                                            </div>

                                            {/* Uniform / Force */}
                                            <div className="grid grid-cols-2 gap-2">
                                                <div>
                                                    <label className="text-[10px] uppercase text-slate-500 font-bold block mb-1">Force</label>
                                                    <select className="w-full bg-slate-950 border border-slate-700 rounded px-1 py-1 text-xs text-slate-200 outline-none">
                                                        <option>{c.meta?.uniform_guess || "Unknown"}</option>
                                                        <option>Metropolitan Police</option>
                                                        <option>City of London</option>
                                                        <option>BTP</option>
                                                        <option>Other</option>
                                                    </select>
                                                </div>
                                                <div>
                                                    <label className="text-[10px] uppercase text-slate-500 font-bold block mb-1">Rank</label>
                                                    <select className="w-full bg-slate-950 border border-slate-700 rounded px-1 py-1 text-xs text-slate-200 outline-none">
                                                        <option>{c.meta?.rank_guess || "Unknown"}</option>
                                                        <option>Constable</option>
                                                        <option>Sergeant</option>
                                                        <option>Inspector</option>
                                                        <option>Commander</option>
                                                    </select>
                                                </div>
                                            </div>
                                        </div>

                                        {/* Actions */}
                                        {!c.reviewed ? (
                                            <div className="flex gap-2 pt-1">
                                                <Button size="sm" onClick={() => handledecision(c.id, 'no')} variant="outline" className="flex-1 border-red-900/30 hover:bg-red-900/20 text-red-400 hover:text-red-300 h-8 text-xs">
                                                    <X className="h-3 w-3 mr-1" />
                                                    Discard
                                                </Button>
                                                <Button size="sm" onClick={() => handledecision(c.id, 'yes')} className="flex-1 bg-green-600/20 hover:bg-green-600/30 text-green-400 border border-green-600/30 h-8 text-xs">
                                                    <Check className="h-3 w-3 mr-1" />
                                                    Confirm
                                                </Button>
                                            </div>
                                        ) : (
                                            <div className={`text-center py-1 text-xs font-bold uppercase ${c.decision === 'yes' ? 'text-green-500' : 'text-red-500'}`}>
                                                {c.decision === 'yes' ? 'Confirmed Officer' : 'Discarded'}
                                            </div>
                                        )}
                                    </div>
                                </Card>
                            ))}
                        </div>
                    </div>
                </Card>
            </div>

            {status === 'complete' && (
                <div className="mt-6 flex justify-end">
                    <Button onClick={onComplete} className="bg-blue-600 hover:bg-blue-500">
                        Generate Report & Return
                    </Button>
                </div>
            )}
        </div>
    );
}

// Add these to tailwind config or global css if not present:
// .bg-slate-* colors (if using standard tailwind they are there)

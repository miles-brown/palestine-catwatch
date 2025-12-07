import { useState, useEffect } from 'react';
import { Upload, FileVideo, Image as ImageIcon, CheckCircle, AlertCircle, Link as LinkIcon, FileUp } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import IngestQuestionnaire from '@/components/IngestQuestionnaire';

const API_BASE = "http://localhost:8000";

const UploadPage = () => {
    // Shared State
    const [activeTab, setActiveTab] = useState('upload'); // 'upload' | 'link'
    const [submitStatus, setSubmitStatus] = useState(null); // 'idle' | 'loading'
    const [status, setStatus] = useState(null); // 'success' | 'error'
    const [message, setMessage] = useState('');

    // Upload State
    const [file, setFile] = useState(null);
    const [mediaType, setMediaType] = useState('image');
    const [selectedProtestId, setSelectedProtestId] = useState('');

    // Dummy protests data for demonstration. In a real app, this would be fetched from an API.
    const [protests, setProtests] = useState([
        { id: '1', name: 'Climate Justice Rally', date: '2023-10-26' },
        { id: '2', name: 'Housing Rights March', date: '2023-11-15' },
        { id: '3', name: 'Healthcare for All Protest', date: '2023-12-01' },
    ]);

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
            setStatus(null);
            // Auto-detect type
            const type = e.target.files[0].type;
            if (type.startsWith('video/')) setMediaType('video');
            else if (type.startsWith('image/')) setMediaType('image');
        }
    };

    const handleDrop = (e) => {
        e.preventDefault();
        if (e.dataTransfer.files && e.dataTransfer.files[0]) {
            setFile(e.dataTransfer.files[0]);
            setStatus(null);
            const type = e.dataTransfer.files[0].type;
            if (type.startsWith('video/')) setMediaType('video');
            else if (type.startsWith('image/')) setMediaType('image');
        }
    };

    const handleFileUpload = async (e) => {
        e.preventDefault();
        if (!file) return;

        if (!selectedProtestId) {
            alert("Please select a protest first.");
            return;
        }

        setSubmitStatus('loading');
        setStatus(null);

        const formData = new FormData();
        formData.append('file', file);
        formData.append('type', mediaType);
        formData.append('protest_id', selectedProtestId);

        try {
            const response = await fetch(`${API_BASE}/upload`, {
                method: 'POST',
                body: formData,
            });

            if (!response.ok) throw new Error('Upload failed');

            const data = await response.json();
            setStatus('success');
            setMessage(`Upload successful! ID: ${data.media_id}. Processing started...`);
            setFile(null);
            setSelectedProtestId('');
        } catch (error) {
            console.error(error);
            setStatus('error');
            setMessage('Failed to upload file. Please try again.');
        } finally {
            setSubmitStatus(null);
        }
    };

    // --- URL Ingest Logic ---
    const handleUrlSubmit = async (answers) => {
        setSubmitStatus('loading');
        try {
            const response = await fetch(`${API_BASE}/ingest/url`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    url: answers.url,
                    protest_id: answers.protestId ? parseInt(answers.protestId) : null,
                    answers: answers
                }),
            });

            if (!response.ok) throw new Error('Ingest failed');
            const data = await response.json();

            setStatus('success');
            setMessage(`Ingestion started! ${data.message}`);
        } catch (error) {
            console.error(error);
            setStatus('error');
            setMessage('Failed to start ingestion. Check the URL or server logs.');
        } finally {
            setSubmitStatus(null);
        }
    };

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
                <div className="bg-white p-1 rounded-xl shadow-sm border border-gray-200 inline-flex">
                    <button
                        onClick={() => { setActiveTab('upload'); setStatus(null); setMessage(''); }}
                        className={`px-6 py-2 rounded-lg font-medium flex items-center gap-2 transition-colors ${activeTab === 'upload' ? 'bg-green-100 text-green-800' : 'text-gray-600 hover:bg-gray-50'
                            }`}
                    >
                        <FileUp className="h-4 w-4" />
                        Upload File
                    </button>
                    <button
                        onClick={() => { setActiveTab('link'); setStatus(null); setMessage(''); }}
                        className={`px-6 py-2 rounded-lg font-medium flex items-center gap-2 transition-colors ${activeTab === 'link' ? 'bg-green-100 text-green-800' : 'text-gray-600 hover:bg-gray-50'
                            }`}
                    >
                        <LinkIcon className="h-4 w-4" />
                        Submit Web Link
                    </button>
                </div>
            </div>

            <Card className="p-8">
                {/* Status Message */}
                {(status || (submitStatus === 'loading')) && (
                    <div className={`mb-6 p-4 rounded-lg flex items-center gap-2 ${status === 'success' ? 'bg-green-100 text-green-800' : (status === 'error' ? 'bg-red-100 text-red-800' : 'bg-blue-100 text-blue-800')}`}>
                        {status === 'success' ? <CheckCircle className="h-5 w-5" /> : (status === 'error' ? <AlertCircle className="h-5 w-5" /> : <div className="animate-spin h-5 w-5 border-2 border-current border-t-transparent rounded-full" />)}
                        {submitStatus === 'loading' ? 'Processing...' : message}
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

                        {/* Protest Selection */}
                        <div className="bg-gray-50 p-4 rounded-lg border border-gray-200">
                            <label className="block text-sm font-medium text-gray-700 mb-1">Related Protest</label>
                            <select
                                required
                                value={selectedProtestId}
                                onChange={(e) => setSelectedProtestId(e.target.value)}
                                className="w-full p-2 border border-gray-300 rounded-md bg-white focus:ring-green-500 focus:border-green-500"
                            >
                                <option value="">Select a protest...</option>
                                {protests.map(p => (
                                    <option key={p.id} value={p.id}>{p.name} ({new Date(p.date).toLocaleDateString()})</option>
                                ))}
                            </select>
                        </div>
                        <br />
                        {/* Submit Button */}
                        <Button
                            type="submit"
                            className="w-full bg-green-700 hover:bg-green-800 text-white py-6 text-lg"
                            disabled={!file || !selectedProtestId || submitStatus === 'loading'}
                        >
                            {submitStatus === 'loading' ? 'Uploading...' : 'Submit Evidence'}
                        </Button>
                    </form>
                ) : (
                    <IngestQuestionnaire
                        protests={protests}
                        onSubmit={handleUrlSubmit}
                        isSubmitting={submitStatus === 'loading'}
                    />
                )}
            </Card>
        </div>
    );
};

export default UploadPage;


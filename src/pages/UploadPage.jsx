import { useState } from 'react';
import { Upload, FileVideo, Image as ImageIcon, CheckCircle, AlertCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';

const API_BASE = "http://localhost:8000";

const UploadPage = () => {
    const [file, setFile] = useState(null);
    const [mediaType, setMediaType] = useState('image');
    const [selectedProtestId, setSelectedProtestId] = useState('');
    const [submitStatus, setSubmitStatus] = useState(null); // 'idle' | 'loading'
    const [status, setStatus] = useState(null); // 'success' | 'error'
    const [message, setMessage] = useState('');

    // Dummy protests data for demonstration. In a real app, this would be fetched from an API.
    const [protests, setProtests] = useState([
        { id: '1', name: 'Climate Justice Rally', date: '2023-10-26' },
        { id: '2', name: 'Housing Rights March', date: '2023-11-15' },
        { id: '3', name: 'Healthcare for All Protest', date: '2023-12-01' },
    ]);

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

    const handleSubmit = async (e) => {
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
            setSelectedProtestId(''); // Clear selected protest after successful upload
        } catch (error) {
            console.error(error);
            setStatus('error');
            setMessage('Failed to upload file. Please try again.');
        } finally {
            setSubmitStatus(null);
        }
    };

    return (
        <div className="max-w-3xl mx-auto px-4 py-12">
            <div className="text-center mb-8">
                <h1 className="text-3xl font-bold text-gray-900 mb-2">Upload Evidence</h1>
                <p className="text-gray-600">
                    Securely upload photos or footage of police activity for analysis.
                </p>
            </div>

            <Card className="p-8">
                <form onSubmit={handleSubmit} className="space-y-6">
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

                    {/* Status Message */}
                    {status && (
                        <div className={`p-4 rounded-lg flex items-center gap-2 ${status === 'success' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                            }`}>
                            {status === 'success' ? <CheckCircle className="h-5 w-5" /> : <AlertCircle className="h-5 w-5" />}
                            {message}
                        </div>
                    )}

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
            </Card>
        </div>
    );
};

export default UploadPage;
```

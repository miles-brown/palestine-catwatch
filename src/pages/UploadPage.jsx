import { useState } from 'react';
import { Upload, FileVideo, Image as ImageIcon, CheckCircle, AlertCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';

const API_BASE = "http://localhost:8000";

const UploadPage = () => {
    const [file, setFile] = useState(null);
    const [mediaType, setMediaType] = useState('image');
    const [uploading, setUploading] = useState(false);
    const [status, setStatus] = useState(null); // 'success' | 'error'
    const [message, setMessage] = useState('');

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

        setUploading(true);
        setStatus(null);

        const formData = new FormData();
        formData.append('file', file);
        formData.append('type', mediaType);
        formData.append('protest_id', 1); // Hardcoded for now, or select from list

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
        } catch (error) {
            console.error(error);
            setStatus('error');
            setMessage('Failed to upload file. Please try again.');
        } finally {
            setUploading(false);
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

                    {/* Submit Button */}
                    <Button
                        type="submit"
                        className="w-full bg-green-700 hover:bg-green-800 text-white py-6 text-lg"
                        disabled={!file || uploading}
                    >
                        {uploading ? 'Uploading & Processing...' : 'Submit Evidence'}
                    </Button>
                </form>
            </Card>
        </div>
    );
};

export default UploadPage;

import { useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Upload, Search, Users, AlertTriangle, CheckCircle,
  Loader2, X, Camera
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import PasswordGate from '@/components/PasswordGate';

let API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";
if (!API_BASE.startsWith("http")) {
  API_BASE = `https://${API_BASE}`;
}

const FaceSearchPage = () => {
  const [selectedFile, setSelectedFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState(null);
  const [error, setError] = useState(null);

  const handleFileSelect = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      setSelectedFile(file);
      setPreviewUrl(URL.createObjectURL(file));
      setResults(null);
      setError(null);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    const file = e.dataTransfer.files?.[0];
    if (file && file.type.startsWith('image/')) {
      setSelectedFile(file);
      setPreviewUrl(URL.createObjectURL(file));
      setResults(null);
      setError(null);
    }
  };

  const handleSearch = async () => {
    if (!selectedFile) return;

    setLoading(true);
    setError(null);
    setResults(null);

    const formData = new FormData();
    formData.append('file', selectedFile);

    try {
      const response = await fetch(`${API_BASE}/search/face`, {
        method: 'POST',
        body: formData
      });

      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        throw new Error(errData.detail || 'Search failed');
      }

      const data = await response.json();
      setResults(data);

    } catch (err) {
      setError(err.message || 'Failed to search');
    } finally {
      setLoading(false);
    }
  };

  const clearSearch = () => {
    setSelectedFile(null);
    setPreviewUrl(null);
    setResults(null);
    setError(null);
  };

  return (
    <PasswordGate>
      <div className="min-h-screen bg-gray-50">
        {/* Header */}
        <div className="bg-white border-b-2 border-green-700">
          <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
            <div className="text-center">
              <h1 className="text-3xl font-bold text-gray-900">
                Face Search
              </h1>
              <p className="text-gray-600 mt-2">
                Upload an image to find matching officers in the database
              </p>
            </div>
          </div>
        </div>

        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            {/* Upload Section */}
            <Card className="p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">
                Upload Image
              </h2>

              {/* Drag & Drop Zone */}
              <div
                className={`border-2 border-dashed rounded-xl p-8 text-center transition-colors ${
                  previewUrl
                    ? 'border-green-500 bg-green-50'
                    : 'border-gray-300 hover:border-gray-400'
                }`}
                onDragOver={(e) => e.preventDefault()}
                onDrop={handleDrop}
              >
                <input
                  type="file"
                  id="face-upload"
                  className="hidden"
                  accept="image/*"
                  onChange={handleFileSelect}
                />

                {previewUrl ? (
                  <div className="space-y-4">
                    <img
                      src={previewUrl}
                      alt="Selected"
                      className="max-h-64 mx-auto rounded-lg shadow-md"
                    />
                    <p className="text-sm text-gray-600">{selectedFile?.name}</p>
                    <button
                      onClick={clearSearch}
                      className="text-sm text-red-600 hover:text-red-700 flex items-center gap-1 mx-auto"
                    >
                      <X className="h-4 w-4" />
                      Clear
                    </button>
                  </div>
                ) : (
                  <label htmlFor="face-upload" className="cursor-pointer">
                    <Camera className="h-16 w-16 text-gray-400 mx-auto mb-4" />
                    <span className="text-lg font-medium text-gray-900 block">
                      Click to upload or drag and drop
                    </span>
                    <span className="text-sm text-gray-500 mt-1 block">
                      JPG, PNG, WebP (best results with clear faces)
                    </span>
                  </label>
                )}
              </div>

              {/* Search Button */}
              <Button
                onClick={handleSearch}
                disabled={!selectedFile || loading}
                className="w-full mt-4 bg-green-700 hover:bg-green-800 text-white py-4"
              >
                {loading ? (
                  <span className="flex items-center gap-2">
                    <Loader2 className="h-5 w-5 animate-spin" />
                    Searching...
                  </span>
                ) : (
                  <span className="flex items-center gap-2">
                    <Search className="h-5 w-5" />
                    Search Database
                  </span>
                )}
              </Button>

              {/* Error Message */}
              {error && (
                <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg flex items-center gap-2 text-red-700">
                  <AlertTriangle className="h-5 w-5" />
                  {error}
                </div>
              )}
            </Card>

            {/* Results Section */}
            <Card className="p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">
                Search Results
              </h2>

              {loading ? (
                <div className="py-12 text-center">
                  <Loader2 className="h-12 w-12 animate-spin text-green-600 mx-auto" />
                  <p className="text-gray-500 mt-4">Analyzing face and searching database...</p>
                </div>
              ) : results ? (
                results.total_matches > 0 ? (
                  <div className="space-y-4">
                    <div className="flex items-center gap-2 text-green-700 mb-4">
                      <CheckCircle className="h-5 w-5" />
                      <span className="font-medium">Found {results.total_matches} potential matches</span>
                    </div>

                    <div className="space-y-3 max-h-96 overflow-y-auto">
                      {results.matches.map((match) => {
                        const cropUrl = match.crop_path
                          ? `${API_BASE}/data/${match.crop_path.replace('../data/', '').replace(/^\/+/, '')}`
                          : null;

                        return (
                          <div
                            key={match.id}
                            className={`flex items-center gap-4 p-3 rounded-lg border ${
                              match.is_strong_match
                                ? 'bg-green-50 border-green-200'
                                : 'bg-gray-50 border-gray-200'
                            }`}
                          >
                            {cropUrl ? (
                              <img
                                src={cropUrl}
                                alt="Officer"
                                className="w-14 h-14 rounded-full object-cover border-2 border-white shadow"
                              />
                            ) : (
                              <div className="w-14 h-14 rounded-full bg-gray-200 flex items-center justify-center">
                                <Users className="h-6 w-6 text-gray-400" />
                              </div>
                            )}

                            <div className="flex-1">
                              <div className="font-medium text-gray-900">
                                {match.badge_number || `Officer #${match.id}`}
                              </div>
                              <div className="text-sm text-gray-500">
                                {match.force || 'Unknown Force'}
                              </div>
                            </div>

                            <div className="text-right">
                              <div className={`text-lg font-bold ${
                                match.confidence > 70 ? 'text-green-600' :
                                match.confidence > 50 ? 'text-yellow-600' : 'text-gray-500'
                              }`}>
                                {match.confidence}%
                              </div>
                              <div className="text-xs text-gray-500">
                                {match.is_strong_match ? 'Strong Match' : 'Possible Match'}
                              </div>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                ) : (
                  <div className="py-12 text-center text-gray-500">
                    <Users className="h-12 w-12 mx-auto mb-3 opacity-50" />
                    <p className="text-lg">No matches found</p>
                    <p className="text-sm mt-1">
                      The face in your image doesn't match any officers in the database.
                    </p>
                  </div>
                )
              ) : (
                <div className="py-12 text-center text-gray-500">
                  <Search className="h-12 w-12 mx-auto mb-3 opacity-50" />
                  <p className="text-lg">Upload an image to search</p>
                  <p className="text-sm mt-1">
                    For best results, use a clear image with the face visible.
                  </p>
                </div>
              )}
            </Card>
          </div>

          {/* Tips */}
          <Card className="mt-8 p-6 bg-blue-50 border-blue-200">
            <h3 className="font-semibold text-blue-800 mb-2">Tips for Better Results</h3>
            <ul className="text-sm text-blue-700 space-y-1">
              <li>- Use images with clear, well-lit faces</li>
              <li>- Frontal face images work best</li>
              <li>- Avoid heavily cropped or blurry images</li>
              <li>- The face should be a significant portion of the image</li>
            </ul>
          </Card>
        </div>
      </div>
    </PasswordGate>
  );
};

export default FaceSearchPage;

import { useState } from 'react';
import { Button } from './ui/button';
import { Shield, Video, Image, FileText } from 'lucide-react';
import Turnstile from './Turnstile';

const IngestQuestionnaire = ({ protests, onSubmit, isSubmitting }) => {
    const [answers, setAnswers] = useState({
        url: '',
        hasPoliceImagery: true,  // Default to yes - most submissions will have this
        contentTypes: {
            video: false,
            images: false,
            article: false,
        },
        protestId: '',
    });
    const [turnstileToken, setTurnstileToken] = useState(null);
    const [error, setError] = useState('');

    const handleChange = (key, value) => {
        setAnswers(prev => ({ ...prev, [key]: value }));
    };

    const handleContentTypeChange = (type, checked) => {
        setAnswers(prev => ({
            ...prev,
            contentTypes: {
                ...prev.contentTypes,
                [type]: checked,
            }
        }));
    };

    const handleSubmit = (e) => {
        e.preventDefault();
        setError('');

        if (!turnstileToken) {
            setError('Please complete the security check');
            return;
        }

        // Transform to backend-compatible format
        const submissionData = {
            url: answers.url,
            hasPoliceImagery: answers.hasPoliceImagery,
            hasVideo: answers.contentTypes.video,
            hasImages: answers.contentTypes.images,
            hasArticle: answers.contentTypes.article,
            protestId: answers.protestId,
            turnstile_token: turnstileToken,
        };

        onSubmit(submissionData);
    };

    return (
        <form onSubmit={handleSubmit} className="space-y-6">

            {/* URL Input */}
            <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Source URL</label>
                <input
                    type="url"
                    required
                    placeholder="https://youtube.com/watch?v=... or news article URL"
                    className="w-full p-3 border border-gray-300 rounded-md shadow-sm focus:ring-green-500 focus:border-green-500"
                    value={answers.url}
                    onChange={(e) => handleChange('url', e.target.value)}
                />
                <p className="text-xs text-gray-500 mt-1">
                    Supports YouTube, Rumble, X/Twitter, news sites, and image galleries.
                </p>
            </div>

            <div className="bg-gray-50 p-6 rounded-lg border border-gray-200 space-y-5">
                <h3 className="font-semibold text-gray-900 flex items-center gap-2">
                    <Shield className="h-4 w-4 text-blue-600" />
                    Content Classification
                </h3>

                {/* Police Imagery Question - Yes/No Toggle */}
                <div className="space-y-2">
                    <label className="block text-sm font-medium text-gray-700">
                        Does this URL contain imagery of policing at Palestine protests?
                    </label>
                    <div className="flex gap-4">
                        <button
                            type="button"
                            onClick={() => handleChange('hasPoliceImagery', true)}
                            className={`flex-1 py-3 px-4 rounded-lg border-2 font-medium transition-all ${
                                answers.hasPoliceImagery
                                    ? 'border-green-500 bg-green-50 text-green-700'
                                    : 'border-gray-200 bg-white text-gray-600 hover:border-gray-300'
                            }`}
                        >
                            Yes
                        </button>
                        <button
                            type="button"
                            onClick={() => handleChange('hasPoliceImagery', false)}
                            className={`flex-1 py-3 px-4 rounded-lg border-2 font-medium transition-all ${
                                !answers.hasPoliceImagery
                                    ? 'border-red-500 bg-red-50 text-red-700'
                                    : 'border-gray-200 bg-white text-gray-600 hover:border-gray-300'
                            }`}
                        >
                            No
                        </button>
                    </div>
                </div>

                {/* Content Type Checkboxes */}
                <div className="space-y-2">
                    <label className="block text-sm font-medium text-gray-700">
                        This page contains:
                    </label>
                    <div className="grid grid-cols-3 gap-3">
                        {/* Video */}
                        <label
                            className={`flex flex-col items-center gap-2 p-4 rounded-lg border-2 cursor-pointer transition-all ${
                                answers.contentTypes.video
                                    ? 'border-blue-500 bg-blue-50'
                                    : 'border-gray-200 bg-white hover:border-gray-300'
                            }`}
                        >
                            <input
                                type="checkbox"
                                checked={answers.contentTypes.video}
                                onChange={(e) => handleContentTypeChange('video', e.target.checked)}
                                className="sr-only"
                            />
                            <Video className={`h-6 w-6 ${answers.contentTypes.video ? 'text-blue-600' : 'text-gray-400'}`} />
                            <span className={`text-sm font-medium ${answers.contentTypes.video ? 'text-blue-700' : 'text-gray-600'}`}>
                                Video
                            </span>
                        </label>

                        {/* Images */}
                        <label
                            className={`flex flex-col items-center gap-2 p-4 rounded-lg border-2 cursor-pointer transition-all ${
                                answers.contentTypes.images
                                    ? 'border-green-500 bg-green-50'
                                    : 'border-gray-200 bg-white hover:border-gray-300'
                            }`}
                        >
                            <input
                                type="checkbox"
                                checked={answers.contentTypes.images}
                                onChange={(e) => handleContentTypeChange('images', e.target.checked)}
                                className="sr-only"
                            />
                            <Image className={`h-6 w-6 ${answers.contentTypes.images ? 'text-green-600' : 'text-gray-400'}`} />
                            <span className={`text-sm font-medium ${answers.contentTypes.images ? 'text-green-700' : 'text-gray-600'}`}>
                                Images
                            </span>
                        </label>

                        {/* News Article */}
                        <label
                            className={`flex flex-col items-center gap-2 p-4 rounded-lg border-2 cursor-pointer transition-all ${
                                answers.contentTypes.article
                                    ? 'border-purple-500 bg-purple-50'
                                    : 'border-gray-200 bg-white hover:border-gray-300'
                            }`}
                        >
                            <input
                                type="checkbox"
                                checked={answers.contentTypes.article}
                                onChange={(e) => handleContentTypeChange('article', e.target.checked)}
                                className="sr-only"
                            />
                            <FileText className={`h-6 w-6 ${answers.contentTypes.article ? 'text-purple-600' : 'text-gray-400'}`} />
                            <span className={`text-sm font-medium ${answers.contentTypes.article ? 'text-purple-700' : 'text-gray-600'}`}>
                                Article
                            </span>
                        </label>
                    </div>
                    <p className="text-xs text-gray-500">Select all that apply. AI will auto-detect if unsure.</p>
                </div>

                {/* Protest ID */}
                <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Related Protest</label>
                    <select
                        className="w-full p-2 border border-gray-300 rounded-md bg-white focus:ring-green-500 focus:border-green-500"
                        value={answers.protestId}
                        onChange={(e) => handleChange('protestId', e.target.value)}
                    >
                        <option value="">-- Auto-detect from content --</option>
                        {protests.map(p => (
                            <option key={p.id} value={p.id}>
                                {p.name} ({new Date(p.date).toLocaleDateString()})
                            </option>
                        ))}
                    </select>
                    <p className="text-xs text-gray-500 mt-1">
                        Leave blank to let AI extract date and location from the content.
                    </p>
                </div>
            </div>

            {/* Turnstile CAPTCHA */}
            <div className="py-2 flex justify-center">
                <Turnstile
                    onVerify={(token) => setTurnstileToken(token)}
                    onExpire={() => setTurnstileToken(null)}
                    onError={() => setError('Security check failed. Please try again.')}
                    theme="light"
                />
            </div>

            {error && (
                <div className="p-3 bg-red-100 border border-red-300 rounded-lg text-red-700 text-sm">
                    {error}
                </div>
            )}

            <Button
                disabled={isSubmitting || !turnstileToken}
                type="submit"
                className="w-full bg-green-700 hover:bg-green-800 text-white py-6 text-lg"
            >
                {isSubmitting ? 'Analyzing URL...' : 'Submit for Analysis'}
            </Button>

        </form>
    );
};

export default IngestQuestionnaire;

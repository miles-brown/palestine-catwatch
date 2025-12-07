import { useState } from 'react';
import { Button } from './ui/button';
import { AlertTriangle, Shield, Video, CheckCircle } from 'lucide-react';

const IngestQuestionnaire = ({ protests, onSubmit, isSubmitting }) => {
    const [answers, setAnswers] = useState({
        url: '',
        useful: false,
        hasImages: false,
        hasPolice: false,
        protestId: '',
        captcha: ''
    });

    const [captchaChallenge] = useState({ q: "2 + 3 = ?", a: "5" });

    const handleChange = (key, value) => {
        setAnswers(prev => ({ ...prev, [key]: value }));
    };

    const handleSubmit = (e) => {
        e.preventDefault();
        if (answers.captcha.trim() !== captchaChallenge.a) {
            alert("Incorrect Captcha. Please try again.");
            return;
        }
        onSubmit(answers);
    };

    return (
        <form onSubmit={handleSubmit} className="space-y-6">

            {/* URL Input */}
            <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Source URL</label>
                <input
                    type="url"
                    required
                    placeholder="https://youtube.com/watch?v=..."
                    className="w-full p-3 border border-gray-300 rounded-md shadow-sm focus:ring-green-500 focus:border-green-500"
                    value={answers.url}
                    onChange={(e) => handleChange('url', e.target.value)}
                />
                <p className="text-xs text-gray-500 mt-1">Supports YouTube, Rumble, and major news sites.</p>
            </div>

            <div className="bg-gray-50 p-6 rounded-lg border border-gray-200 space-y-4">
                <h3 className="font-semibold text-gray-900 flex items-center gap-2">
                    <Shield className="h-4 w-4 text-blue-600" />
                    Intelligence Verification
                </h3>

                {/* Useful? */}
                <div className="flex items-start gap-3">
                    <input
                        type="checkbox"
                        id="useful"
                        checked={answers.useful}
                        onChange={(e) => handleChange('useful', e.target.checked)}
                        className="mt-1 h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-600"
                    />
                    <label htmlFor="useful" className="text-sm text-gray-700 leading-snug">
                        This URL contains media useful to the monitoring effort.
                    </label>
                </div>

                {/* Has Images? */}
                <div className="flex items-start gap-3">
                    <input
                        type="checkbox"
                        id="hasImages"
                        checked={answers.hasImages}
                        onChange={(e) => handleChange('hasImages', e.target.checked)}
                        className="mt-1 h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-600"
                    />
                    <label htmlFor="hasImages" className="text-sm text-gray-700 leading-snug">
                        The URL contains images that should be archived?
                    </label>
                </div>

                {/* Has Police? */}
                <div className="flex items-start gap-3">
                    <input
                        type="checkbox"
                        id="hasPolice"
                        checked={answers.hasPolice}
                        onChange={(e) => handleChange('hasPolice', e.target.checked)}
                        className="mt-1 h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-600"
                    />
                    <label htmlFor="hasPolice" className="text-sm text-gray-700 leading-snug">
                        The link contains embedded video of police officers present at protests?
                    </label>
                </div>

                {/* Protest ID */}
                <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1 mt-4">Related Protest</label>
                    <select
                        className="w-full p-2 border border-gray-300 rounded-md bg-white"
                        value={answers.protestId}
                        onChange={(e) => handleChange('protestId', e.target.value)}
                    >
                        <option value="">-- I don't know / Auto-detect --</option>
                        {protests.map(p => (
                            <option key={p.id} value={p.id}>{p.name} ({new Date(p.date).toLocaleDateString()})</option>
                        ))}
                    </select>
                    <p className="text-xs text-gray-500 mt-1">Leave blank to let AI deduce location/date from video metadata.</p>
                </div>
            </div>

            {/* Captcha */}
            <div className="bg-white p-4 border border-gray-200 rounded-lg max-w-xs">
                <label className="block text-sm font-medium text-gray-700 mb-1">Human Verification</label>
                <div className="flex items-center gap-3">
                    <span className="font-mono text-lg font-bold bg-gray-100 px-3 py-1 rounded border">{captchaChallenge.q}</span>
                    <input
                        type="text"
                        required
                        className="w-20 p-2 border border-gray-300 rounded-md text-center"
                        placeholder="?"
                        value={answers.captcha}
                        onChange={(e) => handleChange('captcha', e.target.value)}
                    />
                </div>
            </div>

            <Button disabled={isSubmitting} type="submit" className="w-full bg-green-700 hover:bg-green-800 text-white py-6 text-lg">
                {isSubmitting ? 'Queueing Analysis...' : 'Submit Intelligence'}
            </Button>

        </form>
    );
};

export default IngestQuestionnaire;

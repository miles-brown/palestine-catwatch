import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Check, X, GitMerge, Zap, User } from 'lucide-react';
import { getMediaUrl } from '../utils/api';

// Use shared getMediaUrl for image URLs (handles R2 and local paths)
const getImageUrl = (url) => getMediaUrl(url) || '';

/**
 * MergeSuggestionCard - Shows a suggested merge between two officers
 *
 * Displays two officer photos side by side with confidence score
 * and accept/reject buttons.
 */
export default function MergeSuggestionCard({
    suggestion,
    officers,
    onAccept,
    onReject,
    disabled = false
}) {
    const officerA = officers.find(o =>
        (o.officer_id || o.id) === suggestion.officer_a_id ||
        o.appearance_id === suggestion.appearance_a_id
    );
    const officerB = officers.find(o =>
        (o.officer_id || o.id) === suggestion.officer_b_id ||
        o.appearance_id === suggestion.appearance_b_id
    );

    const confidence = suggestion.confidence || 0;
    const isAutoMerge = suggestion.auto_merge || confidence >= 0.95;

    // Get crop URL with fallbacks and proper URL handling
    const getCropUrl = (officer, suggestionCrop) => {
        let path = null;
        if (suggestionCrop) {
            path = suggestionCrop;
        } else if (officer) {
            path = officer.face_crop_path || officer.body_crop_path || officer.image_crop_path;
        }
        return path ? getImageUrl(path) : null;
    };

    const cropA = getCropUrl(officerA, suggestion.crop_a);
    const cropB = getCropUrl(officerB, suggestion.crop_b);

    // Get badge display
    const getBadge = (officer) => {
        if (!officer) return 'Unknown';
        return officer.badge_override || officer.ocr_badge_result || officer.badge || 'Unknown';
    };

    return (
        <Card className={`overflow-hidden transition-all
            ${isAutoMerge
                ? 'border-2 border-yellow-500/50 bg-yellow-500/5'
                : 'border border-slate-700 bg-slate-900'}
        `}>
            {/* Header */}
            <div className={`px-4 py-2 flex items-center justify-between
                ${isAutoMerge ? 'bg-yellow-500/10' : 'bg-slate-800'}
            `}>
                <div className="flex items-center gap-2">
                    {isAutoMerge ? (
                        <Zap className="h-4 w-4 text-yellow-400" />
                    ) : (
                        <GitMerge className="h-4 w-4 text-blue-400" />
                    )}
                    <span className={`text-sm font-bold ${isAutoMerge ? 'text-yellow-400' : 'text-blue-400'}`}>
                        {isAutoMerge ? 'AUTO-MERGE' : 'MERGE'} SUGGESTION
                    </span>
                </div>
                <span className={`text-sm font-bold ${
                    confidence >= 0.95 ? 'text-green-400' :
                    confidence >= 0.9 ? 'text-yellow-400' :
                    'text-blue-400'
                }`}>
                    {(confidence * 100).toFixed(0)}% Match
                </span>
            </div>

            {/* Content */}
            <div className="p-4">
                {/* Photos side by side */}
                <div className="flex items-center justify-center gap-4 mb-4">
                    {/* Officer A */}
                    <div className="flex-1 max-w-[140px]">
                        <div className="aspect-square bg-slate-800 rounded-lg overflow-hidden border border-slate-700">
                            {cropA ? (
                                <img
                                    src={cropA}
                                    alt="Officer A"
                                    className="w-full h-full object-cover"
                                />
                            ) : (
                                <div className="w-full h-full flex items-center justify-center">
                                    <User className="h-10 w-10 text-slate-600" />
                                </div>
                            )}
                        </div>
                        <div className="mt-2 text-center">
                            <p className="text-xs text-slate-500">Badge</p>
                            <p className="text-sm font-mono text-white truncate">
                                {getBadge(officerA)}
                            </p>
                            {officerA?.timestamp && (
                                <p className="text-xs text-slate-500">@ {officerA.timestamp}</p>
                            )}
                        </div>
                    </div>

                    {/* Merge Arrow */}
                    <div className="flex flex-col items-center">
                        <div className={`p-2 rounded-full ${isAutoMerge ? 'bg-yellow-500/20' : 'bg-blue-500/20'}`}>
                            <GitMerge className={`h-6 w-6 ${isAutoMerge ? 'text-yellow-400' : 'text-blue-400'}`} />
                        </div>
                        <div className="text-xs text-slate-500 mt-1">
                            SAME?
                        </div>
                    </div>

                    {/* Officer B */}
                    <div className="flex-1 max-w-[140px]">
                        <div className="aspect-square bg-slate-800 rounded-lg overflow-hidden border border-slate-700">
                            {cropB ? (
                                <img
                                    src={cropB}
                                    alt="Officer B"
                                    className="w-full h-full object-cover"
                                />
                            ) : (
                                <div className="w-full h-full flex items-center justify-center">
                                    <User className="h-10 w-10 text-slate-600" />
                                </div>
                            )}
                        </div>
                        <div className="mt-2 text-center">
                            <p className="text-xs text-slate-500">Badge</p>
                            <p className="text-sm font-mono text-white truncate">
                                {getBadge(officerB)}
                            </p>
                            {officerB?.timestamp && (
                                <p className="text-xs text-slate-500">@ {officerB.timestamp}</p>
                            )}
                        </div>
                    </div>
                </div>

                {/* Actions */}
                <div className="flex gap-2">
                    <Button
                        onClick={onAccept}
                        disabled={disabled}
                        className={`flex-1 ${
                            isAutoMerge
                                ? 'bg-yellow-600 hover:bg-yellow-500'
                                : 'bg-green-600 hover:bg-green-500'
                        }`}
                    >
                        <Check className="h-4 w-4 mr-2" />
                        {isAutoMerge ? 'Accept Auto-Merge' : 'Merge'}
                    </Button>
                    <Button
                        onClick={onReject}
                        disabled={disabled}
                        variant="outline"
                        className="flex-1 border-red-500/50 text-red-400 hover:bg-red-500/20"
                    >
                        <X className="h-4 w-4 mr-2" />
                        Keep Separate
                    </Button>
                </div>
            </div>
        </Card>
    );
}

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { X, AlertTriangle, GitBranch, User, Check, Clock } from 'lucide-react';
import { API_BASE, getMediaUrl } from '../utils/api';

// Use shared getMediaUrl for image URLs (handles R2 and local paths)
const getImageUrl = (url) => getMediaUrl(url) || '';

/**
 * UnmergeModal - Split incorrectly merged officers
 *
 * Shows all appearances for a merged officer and lets users
 * select which ones should be separated into a new officer.
 */
export default function UnmergeModal({
    officer,
    appearances,
    onConfirm,
    onCancel,
    isLoading = false
}) {
    const [selectedIds, setSelectedIds] = useState(new Set());

    const toggleSelection = (appearanceId) => {
        setSelectedIds(prev => {
            const next = new Set(prev);
            if (next.has(appearanceId)) {
                next.delete(appearanceId);
            } else {
                next.add(appearanceId);
            }
            return next;
        });
    };

    const selectAll = () => {
        // Can't select all - must leave at least one in original
        const allIds = appearances.map(a => a.appearance_id || a.id);
        setSelectedIds(new Set(allIds.slice(1)));
    };

    const selectNone = () => {
        setSelectedIds(new Set());
    };

    const handleConfirm = () => {
        if (selectedIds.size > 0 && selectedIds.size < appearances.length) {
            onConfirm(Array.from(selectedIds));
        }
    };

    const canConfirm = selectedIds.size > 0 && selectedIds.size < appearances.length;

    // Get badge display
    const getBadge = (appearance) => {
        return appearance.badge_override || appearance.ocr_badge_result || appearance.badge || 'Unknown';
    };

    // Get crop URL with proper URL handling
    const getCropUrl = (appearance) => {
        const path = appearance.face_crop_path || appearance.body_crop_path || appearance.image_crop_path;
        return path ? getImageUrl(path) : null;
    };

    return (
        <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4">
            <div className="bg-slate-900 rounded-xl shadow-2xl max-w-4xl w-full max-h-[90vh] flex flex-col">
                {/* Header */}
                <div className="flex items-center justify-between px-6 py-4 border-b border-slate-700">
                    <div className="flex items-center gap-3">
                        <div className="p-2 rounded-lg bg-orange-500/20">
                            <GitBranch className="h-5 w-5 text-orange-400" />
                        </div>
                        <div>
                            <h2 className="text-lg font-bold text-white">Unmerge Officer</h2>
                            <p className="text-sm text-slate-400">
                                Select appearances to separate into a new officer
                            </p>
                        </div>
                    </div>
                    <button
                        onClick={onCancel}
                        className="p-2 text-slate-400 hover:text-white hover:bg-slate-700 rounded-lg"
                    >
                        <X className="h-5 w-5" />
                    </button>
                </div>

                {/* Warning */}
                <div className="px-6 py-3 bg-amber-500/10 border-b border-amber-500/20">
                    <div className="flex items-start gap-3">
                        <AlertTriangle className="h-5 w-5 text-amber-400 flex-shrink-0 mt-0.5" />
                        <div className="text-sm text-amber-200">
                            <strong>This action will create a new officer record.</strong>
                            <p className="text-amber-300/80 mt-1">
                                Selected appearances will be moved to the new officer.
                                You must leave at least one appearance with the original officer.
                            </p>
                        </div>
                    </div>
                </div>

                {/* Current Officer Summary */}
                <div className="px-6 py-4 border-b border-slate-700 bg-slate-800/50">
                    <div className="flex items-center gap-4">
                        <div className="h-16 w-16 rounded-lg overflow-hidden bg-slate-700">
                            {officer.primary_crop_path ? (
                                <img
                                    src={getImageUrl(officer.primary_crop_path)}
                                    alt="Officer"
                                    className="w-full h-full object-cover"
                                />
                            ) : (
                                <div className="w-full h-full flex items-center justify-center">
                                    <User className="h-8 w-8 text-slate-500" />
                                </div>
                            )}
                        </div>
                        <div>
                            <p className="text-white font-medium">
                                {officer.name_override || officer.name || officer.ai_name || 'Unknown Officer'}
                            </p>
                            <p className="text-sm text-slate-400">
                                Badge: {officer.badge_override || officer.badge || 'Unknown'}
                            </p>
                            <p className="text-sm text-slate-500">
                                {appearances.length} appearances merged
                            </p>
                        </div>
                    </div>
                </div>

                {/* Selection Controls */}
                <div className="px-6 py-3 border-b border-slate-700 flex items-center justify-between">
                    <div className="text-sm text-slate-400">
                        <span className="text-white font-medium">{selectedIds.size}</span> of{' '}
                        <span className="text-white">{appearances.length}</span> appearances selected
                    </div>
                    <div className="flex gap-2">
                        <button
                            onClick={selectNone}
                            className="text-sm text-slate-400 hover:text-white"
                        >
                            Clear all
                        </button>
                        <span className="text-slate-600">|</span>
                        <button
                            onClick={selectAll}
                            className="text-sm text-slate-400 hover:text-white"
                        >
                            Select max
                        </button>
                    </div>
                </div>

                {/* Appearances Grid */}
                <div className="flex-1 overflow-y-auto p-6">
                    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4">
                        {appearances.map((appearance, index) => {
                            const id = appearance.appearance_id || appearance.id;
                            const isSelected = selectedIds.has(id);
                            const isDisabled = !isSelected && selectedIds.size >= appearances.length - 1;
                            const cropUrl = getCropUrl(appearance);

                            return (
                                <Card
                                    key={id}
                                    onClick={() => !isDisabled && toggleSelection(id)}
                                    className={`relative cursor-pointer overflow-hidden transition-all ${
                                        isSelected
                                            ? 'ring-2 ring-orange-500 bg-orange-500/10'
                                            : isDisabled
                                                ? 'opacity-50 cursor-not-allowed'
                                                : 'hover:ring-2 hover:ring-slate-500'
                                    }`}
                                >
                                    {/* Selection Checkbox */}
                                    <div className={`absolute top-2 right-2 z-10 h-6 w-6 rounded-full
                                                     flex items-center justify-center border-2 transition-all ${
                                        isSelected
                                            ? 'bg-orange-500 border-orange-500'
                                            : 'bg-slate-800/80 border-slate-500'
                                    }`}>
                                        {isSelected && <Check className="h-4 w-4 text-white" />}
                                    </div>

                                    {/* Index Badge */}
                                    <div className="absolute top-2 left-2 z-10 px-2 py-0.5 rounded
                                                    bg-slate-900/80 text-xs text-slate-300">
                                        #{index + 1}
                                    </div>

                                    {/* Photo */}
                                    <div className="aspect-square bg-slate-800">
                                        {cropUrl ? (
                                            <img
                                                src={cropUrl}
                                                alt={`Appearance ${index + 1}`}
                                                className="w-full h-full object-cover"
                                            />
                                        ) : (
                                            <div className="w-full h-full flex items-center justify-center">
                                                <User className="h-10 w-10 text-slate-600" />
                                            </div>
                                        )}
                                    </div>

                                    {/* Info */}
                                    <div className="p-2 bg-slate-800">
                                        <p className="text-xs text-slate-400 truncate">
                                            Badge: {getBadge(appearance)}
                                        </p>
                                        {appearance.timestamp && (
                                            <p className="text-xs text-slate-500 flex items-center gap-1 mt-1">
                                                <Clock className="h-3 w-3" />
                                                {appearance.timestamp}
                                            </p>
                                        )}
                                    </div>

                                    {/* Selected Overlay */}
                                    {isSelected && (
                                        <div className="absolute inset-0 bg-orange-500/10 pointer-events-none" />
                                    )}
                                </Card>
                            );
                        })}
                    </div>
                </div>

                {/* Result Preview */}
                {selectedIds.size > 0 && (
                    <div className="px-6 py-3 border-t border-slate-700 bg-slate-800/50">
                        <div className="flex items-center gap-4 text-sm">
                            <div className="flex items-center gap-2">
                                <div className="w-3 h-3 rounded-full bg-blue-500" />
                                <span className="text-slate-400">Original officer:</span>
                                <span className="text-white">
                                    {appearances.length - selectedIds.size} appearances
                                </span>
                            </div>
                            <div className="text-slate-600">→</div>
                            <div className="flex items-center gap-2">
                                <div className="w-3 h-3 rounded-full bg-orange-500" />
                                <span className="text-slate-400">New officer:</span>
                                <span className="text-orange-400">
                                    {selectedIds.size} appearances
                                </span>
                            </div>
                        </div>
                    </div>
                )}

                {/* Actions */}
                <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-slate-700">
                    <Button
                        variant="outline"
                        onClick={onCancel}
                        disabled={isLoading}
                        className="border-slate-600"
                    >
                        Cancel
                    </Button>
                    <Button
                        onClick={handleConfirm}
                        disabled={!canConfirm || isLoading}
                        className="bg-orange-600 hover:bg-orange-500"
                    >
                        {isLoading ? (
                            <>
                                <div className="h-4 w-4 border-2 border-white/30 border-t-white
                                                rounded-full animate-spin mr-2" />
                                Processing...
                            </>
                        ) : (
                            <>
                                <GitBranch className="h-4 w-4 mr-2" />
                                Unmerge {selectedIds.size} Appearance{selectedIds.size !== 1 ? 's' : ''}
                            </>
                        )}
                    </Button>
                </div>

                {/* Validation Message */}
                {selectedIds.size === 0 && (
                    <div className="px-6 pb-4 text-center text-sm text-slate-400">
                        Select at least one appearance to separate
                    </div>
                )}
                {selectedIds.size >= appearances.length && (
                    <div className="px-6 pb-4 text-center text-sm text-amber-400">
                        You must leave at least one appearance with the original officer
                    </div>
                )}
            </div>
        </div>
    );
}

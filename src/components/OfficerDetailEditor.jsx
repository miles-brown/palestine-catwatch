import { useState, useCallback, useMemo } from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import {
    ChevronLeft, ChevronRight, Check, X, User, GitMerge,
    Camera, Clock, Shield, Award, FileText, Save
} from 'lucide-react';
import EditableNameField from './EditableNameField';

// UK Police Forces
const UK_POLICE_FORCES = [
    { value: "", label: "Select Force..." },
    { value: "Metropolitan Police Service", label: "Metropolitan Police" },
    { value: "City of London Police", label: "City of London Police" },
    { value: "British Transport Police", label: "British Transport Police" },
    { value: "Greater Manchester Police", label: "Greater Manchester Police" },
    { value: "West Midlands Police", label: "West Midlands Police" },
    { value: "West Yorkshire Police", label: "West Yorkshire Police" },
    { value: "Merseyside Police", label: "Merseyside Police" },
    { value: "South Yorkshire Police", label: "South Yorkshire Police" },
    { value: "Thames Valley Police", label: "Thames Valley Police" },
    { value: "Hampshire Constabulary", label: "Hampshire Constabulary" },
    { value: "Kent Police", label: "Kent Police" },
    { value: "Essex Police", label: "Essex Police" },
    { value: "Sussex Police", label: "Sussex Police" },
    { value: "Surrey Police", label: "Surrey Police" },
    { value: "Avon and Somerset Police", label: "Avon and Somerset" },
    { value: "Devon and Cornwall Police", label: "Devon and Cornwall" },
    { value: "Dorset Police", label: "Dorset Police" },
    { value: "South Wales Police", label: "South Wales Police" },
    { value: "Police Scotland", label: "Police Scotland" },
    { value: "Police Service of Northern Ireland", label: "PSNI" },
    { value: "Unknown", label: "Unknown" },
];

// UK Police Ranks
const UK_POLICE_RANKS = [
    { value: "", label: "Select Rank..." },
    { value: "Police Constable", label: "Police Constable (PC)" },
    { value: "Sergeant", label: "Sergeant (Sgt)" },
    { value: "Inspector", label: "Inspector (Insp)" },
    { value: "Chief Inspector", label: "Chief Inspector (CI)" },
    { value: "Superintendent", label: "Superintendent (Supt)" },
    { value: "Chief Superintendent", label: "Chief Superintendent" },
    { value: "PCSO", label: "PCSO" },
    { value: "Special Constable", label: "Special Constable" },
    { value: "Unknown", label: "Unknown" },
];

// Role/Unit Options
const ROLE_OPTIONS = [
    { value: "PSU", label: "PSU" },
    { value: "TSG", label: "TSG" },
    { value: "FIT", label: "FIT (Evidence)" },
    { value: "Liaison", label: "Liaison" },
    { value: "Medic", label: "Medic" },
    { value: "Dog Handler", label: "Dog Handler" },
    { value: "Mounted", label: "Mounted" },
    { value: "Firearms", label: "Firearms" },
    { value: "Commander", label: "Commander" },
];

/**
 * OfficerDetailEditor - Deep editing modal for individual officers
 *
 * Provides:
 * - Large photo with all appearances
 * - Editable name field with AI/OCR suggestion
 * - Badge number with OCR confidence
 * - Force dropdown with AI suggestion
 * - Rank dropdown with AI suggestion
 * - Role/Unit tags
 * - Observer notes
 */
export default function OfficerDetailEditor({ officers, onComplete, onBack }) {
    const [currentIndex, setCurrentIndex] = useState(0);
    const [edits, setEdits] = useState({});
    const [saving, setSaving] = useState(false);

    const currentOfficer = officers[currentIndex];
    const officerId = currentOfficer?.officer_id || currentOfficer?.id || currentOfficer?.appearance_id;
    const officerEdits = edits[officerId] || {};

    // Update a field for current officer
    const updateField = useCallback((field, value) => {
        setEdits(prev => ({
            ...prev,
            [officerId]: {
                ...prev[officerId],
                [field]: value
            }
        }));
    }, [officerId]);

    // Toggle role selection
    const toggleRole = useCallback((role) => {
        const currentRoles = officerEdits.roles || currentOfficer?.roles || [];
        const newRoles = currentRoles.includes(role)
            ? currentRoles.filter(r => r !== role)
            : [...currentRoles, role];
        updateField('roles', newRoles);
    }, [officerEdits, currentOfficer, updateField]);

    // Navigation
    const goNext = useCallback(() => {
        if (currentIndex < officers.length - 1) {
            setCurrentIndex(prev => prev + 1);
        }
    }, [currentIndex, officers.length]);

    const goPrev = useCallback(() => {
        if (currentIndex > 0) {
            setCurrentIndex(prev => prev - 1);
        }
    }, [currentIndex]);

    // Get effective value (edit > officer value)
    const getEffective = (field, aiField = null) => {
        const edit = officerEdits[`${field}_override`] ?? officerEdits[field];
        if (edit !== undefined && edit !== null) return edit;

        if (currentOfficer) {
            // Check override first
            if (currentOfficer[`${field}_override`]) return currentOfficer[`${field}_override`];
            // Then OCR
            if (currentOfficer[`ocr_${field}_result`]) return currentOfficer[`ocr_${field}_result`];
            // Then AI
            if (aiField && currentOfficer[aiField]) return currentOfficer[aiField];
            // Then base field
            if (currentOfficer[field]) return currentOfficer[field];
        }
        return '';
    };

    // Get crop URL
    const getCropUrl = (officer) => {
        if (!officer) return null;
        return officer.face_crop_path || officer.body_crop_path || officer.image_crop_path;
    };

    // Progress percentage
    const progress = ((currentIndex + 1) / officers.length) * 100;

    // Check if current has edits
    const hasEdits = Object.keys(officerEdits).length > 0;

    if (!currentOfficer) {
        return (
            <div className="min-h-screen bg-slate-950 flex items-center justify-center">
                <p className="text-slate-400">No officers to edit</p>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-slate-950 text-slate-200 p-4 md:p-6">
            <div className="max-w-4xl mx-auto">
                {/* Progress Bar */}
                <div className="mb-6">
                    <div className="flex justify-between text-sm text-slate-400 mb-2">
                        <span>Officer {currentIndex + 1} of {officers.length}</span>
                        <span>{Math.round(progress)}% complete</span>
                    </div>
                    <div className="h-2 bg-slate-800 rounded-full overflow-hidden">
                        <div
                            className="h-full bg-green-500 transition-all duration-300"
                            style={{ width: `${progress}%` }}
                        />
                    </div>
                </div>

                {/* Main Editor Card */}
                <Card className="bg-slate-900 border-slate-800 overflow-hidden">
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-0">
                        {/* Left: Photo Section */}
                        <div className="bg-slate-950 p-4 md:p-6">
                            {/* Primary Image */}
                            <div className="aspect-square bg-slate-800 rounded-xl overflow-hidden mb-4 relative">
                                {getCropUrl(currentOfficer) ? (
                                    <img
                                        src={getCropUrl(currentOfficer)}
                                        className="w-full h-full object-cover"
                                        alt={`Officer ${currentIndex + 1}`}
                                    />
                                ) : (
                                    <div className="w-full h-full flex items-center justify-center">
                                        <User className="h-24 w-24 text-slate-600" />
                                    </div>
                                )}

                                {/* Officer number badge */}
                                <div className="absolute top-3 left-3 bg-black/75 px-3 py-1 rounded-full text-white text-sm font-bold">
                                    #{currentIndex + 1}
                                </div>

                                {/* Merged badge */}
                                {currentOfficer.isMerged && (
                                    <div className="absolute top-3 right-3 bg-blue-600 px-2 py-1 rounded-full text-white text-xs flex items-center gap-1">
                                        <GitMerge className="h-3 w-3" />
                                        Merged
                                    </div>
                                )}

                                {/* Edit indicator */}
                                {hasEdits && (
                                    <div className="absolute bottom-3 right-3 bg-yellow-600 px-2 py-1 rounded-full text-white text-xs flex items-center gap-1">
                                        <FileText className="h-3 w-3" />
                                        Edited
                                    </div>
                                )}
                            </div>

                            {/* Other Appearances (if merged or multiple) */}
                            {currentOfficer.all_crops?.length > 1 && (
                                <div>
                                    <p className="text-xs text-slate-500 uppercase font-bold mb-2 flex items-center gap-2">
                                        <Camera className="h-3 w-3" />
                                        All Appearances ({currentOfficer.all_crops.length})
                                    </p>
                                    <div className="flex gap-2 overflow-x-auto pb-2">
                                        {currentOfficer.all_crops.map((crop, idx) => (
                                            <div
                                                key={idx}
                                                className="flex-shrink-0 w-16 h-16 rounded-lg overflow-hidden border border-slate-700 relative"
                                            >
                                                <img
                                                    src={crop.path}
                                                    className="w-full h-full object-cover"
                                                    alt={`Appearance ${idx + 1}`}
                                                />
                                                {crop.timestamp && (
                                                    <div className="absolute bottom-0 left-0 right-0 bg-black/75 text-[10px] text-white text-center py-0.5">
                                                        {crop.timestamp}
                                                    </div>
                                                )}
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {/* AI Detection Summary */}
                            <div className="mt-4 p-3 bg-slate-800/50 rounded-lg">
                                <p className="text-xs text-slate-500 uppercase font-bold mb-2">
                                    AI Detection
                                </p>
                                <div className="grid grid-cols-2 gap-2 text-sm">
                                    <div>
                                        <span className="text-slate-500">Confidence:</span>
                                        <span className={`ml-2 font-bold ${
                                            (currentOfficer.confidence || 0) >= 0.8 ? 'text-green-400' :
                                            (currentOfficer.confidence || 0) >= 0.6 ? 'text-yellow-400' :
                                            'text-red-400'
                                        }`}>
                                            {((currentOfficer.confidence || 0) * 100).toFixed(0)}%
                                        </span>
                                    </div>
                                    {currentOfficer.timestamp && (
                                        <div className="flex items-center gap-1">
                                            <Clock className="h-3 w-3 text-slate-500" />
                                            <span className="text-white">{currentOfficer.timestamp}</span>
                                        </div>
                                    )}
                                </div>
                            </div>
                        </div>

                        {/* Right: Form Fields */}
                        <div className="p-4 md:p-6 space-y-5">
                            <h2 className="text-xl font-bold text-white mb-6 flex items-center gap-2">
                                <Shield className="h-5 w-5 text-green-400" />
                                Edit Officer Details
                            </h2>

                            {/* Officer Name (from uniform label) */}
                            <EditableNameField
                                value={getEffective('name', 'ai_name')}
                                aiSuggestion={currentOfficer.ai_name || currentOfficer.ocr_name_result}
                                aiConfidence={currentOfficer.ai_name_confidence || currentOfficer.ocr_name_confidence}
                                onChange={(val) => updateField('name_override', val)}
                                placeholder="e.g. PC WILLIAMS"
                            />

                            {/* Badge Number */}
                            <div>
                                <label className="text-xs text-slate-500 uppercase font-bold mb-1 block">
                                    Shoulder Number / Badge
                                    {currentOfficer.ocr_badge_result && (
                                        <span className="ml-2 text-green-400 font-normal text-[10px]">
                                            OCR detected ({((currentOfficer.ocr_badge_confidence || 0) * 100).toFixed(0)}%)
                                        </span>
                                    )}
                                </label>
                                <input
                                    type="text"
                                    value={getEffective('badge', 'ocr_badge_result')}
                                    onChange={(e) => updateField('badge_override', e.target.value.toUpperCase())}
                                    placeholder="e.g. U1234, MPS456"
                                    className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-3
                                               text-white font-mono text-lg focus:border-blue-500 focus:ring-1
                                               focus:ring-blue-500/50 outline-none transition"
                                />
                                {currentOfficer.ocr_badge_result && !officerEdits.badge_override && (
                                    <p className="text-xs text-slate-500 mt-1">
                                        AI suggestion: <span className="text-green-400 font-mono">{currentOfficer.ocr_badge_result}</span>
                                    </p>
                                )}
                            </div>

                            {/* Police Force */}
                            <div>
                                <label className="text-xs text-slate-500 uppercase font-bold mb-1 block">
                                    Police Force
                                    {currentOfficer.ai_force && (
                                        <span className="ml-2 text-green-400 font-normal text-[10px]">
                                            AI detected
                                        </span>
                                    )}
                                </label>
                                <select
                                    value={getEffective('force', 'ai_force')}
                                    onChange={(e) => updateField('force_override', e.target.value)}
                                    className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-3
                                               text-white focus:border-blue-500 outline-none transition appearance-none cursor-pointer"
                                >
                                    {UK_POLICE_FORCES.map(force => (
                                        <option key={force.value} value={force.value}>
                                            {force.label}
                                        </option>
                                    ))}
                                </select>
                                {currentOfficer.ai_force && !officerEdits.force_override && (
                                    <p className="text-xs text-slate-500 mt-1">
                                        AI suggestion: <span className="text-green-400">{currentOfficer.ai_force}</span>
                                    </p>
                                )}
                            </div>

                            {/* Rank */}
                            <div>
                                <label className="text-xs text-slate-500 uppercase font-bold mb-1 block">
                                    Rank
                                    {currentOfficer.ai_rank && (
                                        <span className="ml-2 text-green-400 font-normal text-[10px]">
                                            AI detected
                                        </span>
                                    )}
                                </label>
                                <select
                                    value={getEffective('rank', 'ai_rank')}
                                    onChange={(e) => updateField('rank_override', e.target.value)}
                                    className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-3
                                               text-white focus:border-blue-500 outline-none transition appearance-none cursor-pointer"
                                >
                                    {UK_POLICE_RANKS.map(rank => (
                                        <option key={rank.value} value={rank.value}>
                                            {rank.label}
                                        </option>
                                    ))}
                                </select>
                                {currentOfficer.ai_rank && !officerEdits.rank_override && (
                                    <p className="text-xs text-slate-500 mt-1">
                                        AI suggestion: <span className="text-green-400">{currentOfficer.ai_rank}</span>
                                    </p>
                                )}
                            </div>

                            {/* Role/Unit Tags */}
                            <div>
                                <label className="text-xs text-slate-500 uppercase font-bold mb-2 block flex items-center gap-2">
                                    <Award className="h-3 w-3" />
                                    Role / Unit
                                </label>
                                <div className="flex flex-wrap gap-2">
                                    {ROLE_OPTIONS.map(role => {
                                        const currentRoles = officerEdits.roles || currentOfficer?.roles || [];
                                        const selected = currentRoles.includes(role.value);
                                        return (
                                            <button
                                                key={role.value}
                                                type="button"
                                                onClick={() => toggleRole(role.value)}
                                                className={`px-3 py-1.5 rounded-full text-sm font-medium transition ${
                                                    selected
                                                        ? 'bg-green-600 text-white'
                                                        : 'bg-slate-800 text-slate-400 hover:bg-slate-700 border border-slate-700'
                                                }`}
                                            >
                                                {role.label}
                                            </button>
                                        );
                                    })}
                                </div>
                            </div>

                            {/* Notes */}
                            <div>
                                <label className="text-xs text-slate-500 uppercase font-bold mb-1 block flex items-center gap-2">
                                    <FileText className="h-3 w-3" />
                                    Observer Notes
                                </label>
                                <textarea
                                    value={officerEdits.notes ?? currentOfficer?.notes ?? ''}
                                    onChange={(e) => updateField('notes', e.target.value)}
                                    placeholder="Any additional observations about this officer..."
                                    rows={3}
                                    className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-3
                                               text-white text-sm focus:border-blue-500 focus:ring-1
                                               focus:ring-blue-500/50 outline-none transition resize-none"
                                />
                            </div>
                        </div>
                    </div>

                    {/* Navigation Footer */}
                    <div className="border-t border-slate-800 p-4 flex justify-between items-center bg-slate-900">
                        <Button
                            variant="ghost"
                            onClick={goPrev}
                            disabled={currentIndex === 0}
                            className="text-slate-400 hover:text-white"
                        >
                            <ChevronLeft className="h-5 w-5 mr-1" />
                            Previous
                        </Button>

                        {/* Progress dots */}
                        <div className="hidden sm:flex gap-1.5 max-w-xs overflow-hidden">
                            {officers.slice(
                                Math.max(0, currentIndex - 3),
                                Math.min(officers.length, currentIndex + 4)
                            ).map((o, idx) => {
                                const actualIdx = Math.max(0, currentIndex - 3) + idx;
                                const oId = o.officer_id || o.id || o.appearance_id;
                                return (
                                    <button
                                        key={oId}
                                        onClick={() => setCurrentIndex(actualIdx)}
                                        className={`w-2 h-2 rounded-full transition ${
                                            actualIdx === currentIndex
                                                ? 'bg-green-500 w-6'
                                                : edits[oId]
                                                    ? 'bg-yellow-500'
                                                    : 'bg-slate-700 hover:bg-slate-600'
                                        }`}
                                    />
                                );
                            })}
                        </div>

                        {currentIndex < officers.length - 1 ? (
                            <Button
                                onClick={goNext}
                                className="bg-green-600 hover:bg-green-500"
                            >
                                {hasEdits ? 'Save & ' : ''}Next
                                <ChevronRight className="h-5 w-5 ml-1" />
                            </Button>
                        ) : (
                            <Button
                                onClick={() => onComplete(edits)}
                                className="bg-green-600 hover:bg-green-500"
                                disabled={saving}
                            >
                                <Check className="h-5 w-5 mr-1" />
                                Finish Editing
                            </Button>
                        )}
                    </div>
                </Card>

                {/* Back Button */}
                <div className="mt-4 text-center">
                    <Button
                        variant="ghost"
                        onClick={onBack}
                        className="text-slate-500 hover:text-slate-300"
                    >
                        <ChevronLeft className="h-4 w-4 mr-2" />
                        Back to Review Panel
                    </Button>
                </div>
            </div>
        </div>
    );
}

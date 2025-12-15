import { useState, useRef, useEffect } from 'react';
import { Pencil, Sparkles, Eye, Check, X } from 'lucide-react';

/**
 * EditableNameField - Click-to-edit field for officer names
 *
 * Shows AI/OCR suggested name with confidence indicator.
 * Becomes editable when clicked. Auto-formats as uppercase.
 */
export default function EditableNameField({
    value,
    aiSuggestion,
    aiConfidence,
    ocrSuggestion,
    ocrConfidence,
    onChange,
    placeholder = "Click to add name...",
    className = ""
}) {
    const [isEditing, setIsEditing] = useState(false);
    const [editValue, setEditValue] = useState(value || '');
    const inputRef = useRef(null);

    // Focus input when entering edit mode
    useEffect(() => {
        if (isEditing && inputRef.current) {
            inputRef.current.focus();
            inputRef.current.select();
        }
    }, [isEditing]);

    // Update local state when value prop changes
    useEffect(() => {
        if (!isEditing) {
            setEditValue(value || '');
        }
    }, [value, isEditing]);

    const handleClick = () => {
        setIsEditing(true);
    };

    const handleChange = (e) => {
        // Auto-uppercase for uniform name format (e.g., "PC WILLIAMS")
        setEditValue(e.target.value.toUpperCase());
    };

    const handleSave = () => {
        setIsEditing(false);
        if (editValue !== value) {
            onChange(editValue.trim());
        }
    };

    const handleCancel = () => {
        setIsEditing(false);
        setEditValue(value || '');
    };

    const handleKeyDown = (e) => {
        if (e.key === 'Enter') {
            handleSave();
        } else if (e.key === 'Escape') {
            handleCancel();
        }
    };

    const handleBlur = () => {
        // Small delay to allow button clicks to register
        setTimeout(() => {
            if (isEditing) {
                handleSave();
            }
        }, 150);
    };

    const applySuggestion = (suggestion) => {
        setEditValue(suggestion.toUpperCase());
        onChange(suggestion.toUpperCase());
        setIsEditing(false);
    };

    // Determine the best suggestion to show
    const bestSuggestion = ocrConfidence > (aiConfidence || 0)
        ? { text: ocrSuggestion, confidence: ocrConfidence, source: 'OCR' }
        : aiSuggestion
            ? { text: aiSuggestion, confidence: aiConfidence, source: 'AI' }
            : null;

    // Display value - prioritize current value, then show suggestion or placeholder
    const displayValue = value || '';
    const showSuggestion = !value && bestSuggestion?.text;
    const isManuallyEdited = value && value !== aiSuggestion && value !== ocrSuggestion;

    if (isEditing) {
        return (
            <div className={`relative ${className}`}>
                <input
                    ref={inputRef}
                    type="text"
                    value={editValue}
                    onChange={handleChange}
                    onKeyDown={handleKeyDown}
                    onBlur={handleBlur}
                    placeholder="PC SURNAME"
                    className="w-full px-3 py-2 bg-slate-800 border-2 border-blue-500
                               rounded-lg text-white font-mono text-lg tracking-wide
                               focus:outline-none focus:ring-2 focus:ring-blue-400"
                />
                <div className="absolute right-2 top-1/2 -translate-y-1/2 flex gap-1">
                    <button
                        onClick={handleSave}
                        className="p-1 text-green-400 hover:bg-green-500/20 rounded"
                        title="Save"
                    >
                        <Check className="h-4 w-4" />
                    </button>
                    <button
                        onClick={handleCancel}
                        className="p-1 text-red-400 hover:bg-red-500/20 rounded"
                        title="Cancel"
                    >
                        <X className="h-4 w-4" />
                    </button>
                </div>

                {/* Suggestions dropdown when editing */}
                {(aiSuggestion || ocrSuggestion) && (
                    <div className="absolute top-full left-0 right-0 mt-1 bg-slate-800
                                    border border-slate-600 rounded-lg shadow-lg z-10 overflow-hidden">
                        <div className="px-3 py-1.5 text-xs text-slate-400 border-b border-slate-700">
                            Suggestions
                        </div>
                        {ocrSuggestion && (
                            <button
                                onClick={() => applySuggestion(ocrSuggestion)}
                                className="w-full px-3 py-2 flex items-center justify-between
                                           hover:bg-slate-700 text-left"
                            >
                                <div className="flex items-center gap-2">
                                    <Eye className="h-4 w-4 text-purple-400" />
                                    <span className="text-white font-mono">{ocrSuggestion}</span>
                                </div>
                                <span className={`text-xs px-2 py-0.5 rounded ${
                                    ocrConfidence >= 0.8 ? 'bg-green-500/20 text-green-400' :
                                    ocrConfidence >= 0.6 ? 'bg-yellow-500/20 text-yellow-400' :
                                    'bg-red-500/20 text-red-400'
                                }`}>
                                    OCR {(ocrConfidence * 100).toFixed(0)}%
                                </span>
                            </button>
                        )}
                        {aiSuggestion && aiSuggestion !== ocrSuggestion && (
                            <button
                                onClick={() => applySuggestion(aiSuggestion)}
                                className="w-full px-3 py-2 flex items-center justify-between
                                           hover:bg-slate-700 text-left"
                            >
                                <div className="flex items-center gap-2">
                                    <Sparkles className="h-4 w-4 text-blue-400" />
                                    <span className="text-white font-mono">{aiSuggestion}</span>
                                </div>
                                <span className={`text-xs px-2 py-0.5 rounded ${
                                    aiConfidence >= 0.8 ? 'bg-green-500/20 text-green-400' :
                                    aiConfidence >= 0.6 ? 'bg-yellow-500/20 text-yellow-400' :
                                    'bg-red-500/20 text-red-400'
                                }`}>
                                    AI {(aiConfidence * 100).toFixed(0)}%
                                </span>
                            </button>
                        )}
                    </div>
                )}
            </div>
        );
    }

    return (
        <div
            onClick={handleClick}
            className={`group cursor-pointer ${className}`}
        >
            <div className="relative px-3 py-2 bg-slate-800/50 border border-slate-700
                            rounded-lg hover:border-blue-500/50 hover:bg-slate-800 transition-all">
                {displayValue ? (
                    <div className="flex items-center justify-between">
                        <span className="text-white font-mono text-lg tracking-wide">
                            {displayValue}
                        </span>
                        <div className="flex items-center gap-2">
                            {/* Source indicator */}
                            {isManuallyEdited ? (
                                <span className="text-xs px-2 py-0.5 rounded bg-slate-600 text-slate-300">
                                    Manual
                                </span>
                            ) : value === ocrSuggestion && ocrConfidence ? (
                                <span className={`text-xs px-2 py-0.5 rounded flex items-center gap-1 ${
                                    ocrConfidence >= 0.8 ? 'bg-purple-500/20 text-purple-400' :
                                    'bg-purple-500/10 text-purple-300'
                                }`}>
                                    <Eye className="h-3 w-3" />
                                    OCR {(ocrConfidence * 100).toFixed(0)}%
                                </span>
                            ) : value === aiSuggestion && aiConfidence ? (
                                <span className={`text-xs px-2 py-0.5 rounded flex items-center gap-1 ${
                                    aiConfidence >= 0.8 ? 'bg-blue-500/20 text-blue-400' :
                                    'bg-blue-500/10 text-blue-300'
                                }`}>
                                    <Sparkles className="h-3 w-3" />
                                    AI {(aiConfidence * 100).toFixed(0)}%
                                </span>
                            ) : null}
                            <Pencil className="h-4 w-4 text-slate-500 group-hover:text-blue-400 transition-colors" />
                        </div>
                    </div>
                ) : showSuggestion ? (
                    <div className="flex items-center justify-between">
                        <span className="text-slate-400 font-mono text-lg tracking-wide italic">
                            {bestSuggestion.text}
                        </span>
                        <div className="flex items-center gap-2">
                            <span className={`text-xs px-2 py-0.5 rounded flex items-center gap-1 ${
                                bestSuggestion.confidence >= 0.8
                                    ? bestSuggestion.source === 'OCR'
                                        ? 'bg-purple-500/20 text-purple-400'
                                        : 'bg-blue-500/20 text-blue-400'
                                    : 'bg-slate-600 text-slate-400'
                            }`}>
                                {bestSuggestion.source === 'OCR'
                                    ? <Eye className="h-3 w-3" />
                                    : <Sparkles className="h-3 w-3" />
                                }
                                {bestSuggestion.source} suggestion
                            </span>
                            <Pencil className="h-4 w-4 text-slate-500 group-hover:text-blue-400 transition-colors" />
                        </div>
                    </div>
                ) : (
                    <div className="flex items-center justify-between">
                        <span className="text-slate-500 italic">{placeholder}</span>
                        <Pencil className="h-4 w-4 text-slate-500 group-hover:text-blue-400 transition-colors" />
                    </div>
                )}
            </div>
        </div>
    );
}

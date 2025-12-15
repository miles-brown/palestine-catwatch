# Enhanced Report Generation - Implementation Plan

**Version:** 1.1
**Date:** 2024-12-14

---

## Executive Summary

This plan expands the current report functionality into a comprehensive, multi-stage verification workflow where report generation becomes the **final action** after all officer confirmations, OCR corrections, merging of duplicates, and manual edits are complete. The report will be visually compelling, data-driven, and serve as a professional evidence document.

---

## Current State Analysis

### Existing Flow
```
URL/File Upload → LiveAnalysis (WebSocket) → Quick Review → Navigate to ReportPage
```

### Current Limitations
1. **Premature Report Generation**: Report is viewable immediately, even before user confirms officers
2. **Lost Edits**: User edits (badge, force, rank) in LiveAnalysis are only in React state, not persisted
3. **No OCR Integration**: Badge detection is disabled (`reader = None` in analyzer.py)
4. **No Name Detection**: Officer names from uniform labels not extracted
5. **No Duplicate Handling**: Same officer detected multiple times creates separate entries
6. **Basic Visuals**: Report is functional but lacks visual impact
7. **No Verification Workflow**: No clear "confirm this is a police officer" step
8. **Missing Data Context**: No aggregated insights, patterns, or analytics in report

---

## Proposed Architecture

### New Multi-Stage Flow
```
Upload → LiveAnalysis → Officer Review & Merge Panel → Detail Editing → Report Preview → Final Submit
                              │                              │                 │
                              ▼                              ▼                 ▼
                        Auto-Merge >90%              OCR + Manual Edit    Generate PDF
                        Manual Merge/Unmerge         Name/Badge/Force     Export Options
                        Approve/Reject               Role/Rank
```

---

## Core Features

### 1. Officer Merge System

#### 1.1 Auto-Merge Suggestions (>90% Match)

When the same officer is detected in multiple frames, the system should automatically suggest merges based on face embedding similarity.

**Algorithm:**
```python
# In backend/ai/analyzer.py

def calculate_embedding_similarity(emb1, emb2):
    """Calculate cosine similarity between two face embeddings"""
    return np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))

def find_merge_candidates(officers, threshold=0.90):
    """
    Find officers that are likely the same person.
    Returns list of merge suggestions with confidence scores.
    """
    merge_suggestions = []

    for i, officer1 in enumerate(officers):
        for j, officer2 in enumerate(officers[i+1:], start=i+1):
            similarity = calculate_embedding_similarity(
                officer1['embedding'],
                officer2['embedding']
            )
            if similarity >= threshold:
                merge_suggestions.append({
                    'officer_a_id': officer1['id'],
                    'officer_b_id': officer2['id'],
                    'confidence': similarity,
                    'auto_merge': similarity >= 0.95,  # Auto-merge if very high confidence
                    'suggested': True
                })

    return merge_suggestions
```

**Visual Design - Merge Suggestion Card:**
```
┌─────────────────────────────────────────────────────────────────────┐
│  ⚡ AUTO-MERGE SUGGESTION (95% Match)                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────┐         ═══════          ┌─────────────┐          │
│  │             │         MERGE?           │             │          │
│  │  [PHOTO 1]  │   ───────────────────▶   │  [PHOTO 2]  │          │
│  │             │                          │             │          │
│  │  @ 00:12    │        95% MATCH         │  @ 02:45    │          │
│  └─────────────┘                          └─────────────┘          │
│                                                                     │
│  Badge: U1234                             Badge: U1234              │
│  Force: MPS (AI)                          Force: MPS (AI)           │
│                                                                     │
│          [✓ Accept Merge]      [✗ Keep Separate]                   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

**Visual Design - Manual Merge Selection:**
```
┌─────────────────────────────────────────────────────────────────────┐
│  SELECT OFFICERS TO MERGE                                           │
│  Click officers you believe are the same person                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐               │
│  │ ☑ SEL  │  │ ☑ SEL  │  │         │  │         │               │
│  │ [img]  │  │ [img]  │  │ [img]  │  │ [img]  │               │
│  │ U1234  │  │ U1234  │  │ ABC123 │  │ XYZ789 │               │
│  └─────────┘  └─────────┘  └─────────┘  └─────────┘               │
│                                                                     │
│  2 officers selected                                                │
│                                                                     │
│  [Merge Selected (2)]  [Cancel Selection]                          │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

#### 1.2 Merged Officer View

When officers are merged, they become a single card with multiple photos.

```
┌─────────────────────────────────────────────────────────────────────┐
│  OFFICER #1                                           [🔗 Merged]   │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────┐  SOURCE IMAGES (3)                               │
│  │              │  ┌────┐ ┌────┐ ┌────┐                            │
│  │   BEST       │  │0:12│ │1:45│ │2:45│  ◀ Click to view          │
│  │   PHOTO      │  └────┘ └────┘ └────┘                            │
│  │              │                                                   │
│  └──────────────┘  Name: PC WILLIAMS                               │
│                    Badge: U1234                                     │
│                    Force: Metropolitan Police                       │
│                    Rank: Police Constable                           │
│                                                                     │
│  [Edit Details]  [View All Appearances]  [⊖ Unmerge]               │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

#### 1.3 Unmerge Functionality

If a merge was incorrect, users can unmerge back to separate officers.

```
┌─────────────────────────────────────────────────────────────────────┐
│  UNMERGE OFFICER                                                    │
│  Select which images to separate into individual officers           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Currently merged images:                                           │
│                                                                     │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐                             │
│  │ ☑ Keep │  │ ☐ Split │  │ ☐ Split │                             │
│  │ [img]  │  │ [img]  │  │ [img]  │                             │
│  │ @ 0:12 │  │ @ 1:45 │  │ @ 2:45 │                             │
│  └─────────┘  └─────────┘  └─────────┘                             │
│                                                                     │
│  This will create 2 separate officers:                              │
│  • Officer A: 1 image (kept)                                        │
│  • Officer B: 2 images (split)                                      │
│                                                                     │
│  [Confirm Unmerge]  [Cancel]                                        │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

### 2. Officer Name Detection (Uniform Label OCR)

#### 2.1 Name Extraction from Uniform

British police officers often have name labels on their uniforms (e.g., "PC WILLIAMS", "SGT JONES"). We'll use OCR + AI to detect these.

**Implementation:**
```python
# backend/ai/uniform_analyzer.py - Extended prompt

UNIFORM_ANALYSIS_PROMPT = """Analyze this image of a UK police officer. Extract:

1. **Name Label**: Look for their name badge/label on uniform (usually format: "PC SURNAME" or "SGT JONES")
   - Return the full text visible (e.g., "PC WILLIAMS")
   - Confidence level for this reading

2. **Shoulder Number/Badge**: The alphanumeric identifier (e.g., "U1234", "MPS456")
   - Return exact characters visible
   - Confidence level

3. **Force Identification**: Determine police force from uniform markings, patches, etc.

4. **Rank**: From epaulettes, stripes, pips, etc.

Return JSON:
{
    "name_label": {
        "text": "PC WILLIAMS" | null,
        "confidence": 0.0-1.0
    },
    "shoulder_number": {
        "text": "U1234" | null,
        "confidence": 0.0-1.0
    },
    "force": {
        "name": "Metropolitan Police Service" | null,
        "confidence": 0.0-1.0
    },
    "rank": {
        "name": "Police Constable" | null,
        "confidence": 0.0-1.0
    }
}
"""
```

**OCR Pipeline for Name Labels:**
```python
# backend/ai/name_detector.py

import easyocr
import re

def detect_officer_name(crop_path: str) -> dict:
    """
    Detect officer name from uniform label using OCR.
    Returns dict with detected name and confidence.
    """
    reader = get_ocr_reader()
    results = reader.readtext(crop_path, detail=1)

    # Common UK police name label patterns
    name_patterns = [
        r'^(PC|SGT|INSP|CI|SUPT|DC|DS|DI)\s+[A-Z]+$',  # PC WILLIAMS
        r'^[A-Z]+\s+(PC|SGT|INSP)$',                     # WILLIAMS PC
        r'^[A-Z]{2,}\s+\d+$',                             # Name with number
    ]

    best_match = None
    best_confidence = 0.0

    for bbox, text, conf in results:
        clean_text = text.upper().strip()

        for pattern in name_patterns:
            if re.match(pattern, clean_text) and conf > best_confidence:
                best_match = clean_text
                best_confidence = conf
                break

    return {
        'text': best_match,
        'confidence': best_confidence,
        'source': 'ocr'
    }
```

#### 2.2 Editable Name Field UI

The name field shows AI/OCR suggestion but becomes editable on click.

```jsx
// src/components/EditableNameField.jsx

export function EditableNameField({ officer, onUpdate }) {
    const [isEditing, setIsEditing] = useState(false);
    const [value, setValue] = useState(officer.name_override || officer.ai_name || '');
    const inputRef = useRef(null);

    const hasAiSuggestion = officer.ai_name && !officer.name_override;
    const confidence = officer.ai_name_confidence;

    useEffect(() => {
        if (isEditing && inputRef.current) {
            inputRef.current.focus();
            inputRef.current.select();
        }
    }, [isEditing]);

    const handleSave = () => {
        setIsEditing(false);
        if (value !== (officer.name_override || officer.ai_name || '')) {
            onUpdate({ name_override: value || null });
        }
    };

    return (
        <div className="relative">
            <label className="text-xs text-slate-500 uppercase font-bold mb-1 block">
                Officer Name
                {hasAiSuggestion && (
                    <span className="ml-2 text-green-400 font-normal text-[10px]">
                        AI detected ({(confidence * 100).toFixed(0)}%)
                    </span>
                )}
            </label>

            {isEditing ? (
                <input
                    ref={inputRef}
                    type="text"
                    value={value}
                    onChange={(e) => setValue(e.target.value.toUpperCase())}
                    onBlur={handleSave}
                    onKeyDown={(e) => e.key === 'Enter' && handleSave()}
                    placeholder="e.g. PC WILLIAMS"
                    className="w-full bg-slate-900 border border-blue-500 rounded px-3 py-2
                               text-white font-medium focus:ring-2 focus:ring-blue-500/50 outline-none"
                />
            ) : (
                <div
                    onClick={() => setIsEditing(true)}
                    className={`w-full px-3 py-2 rounded cursor-text transition
                        ${value
                            ? 'bg-slate-800 text-white font-medium'
                            : 'bg-slate-900 text-slate-500 italic border border-dashed border-slate-700'
                        }
                        hover:border-blue-500 hover:border-solid`}
                >
                    {value || 'Click to add name...'}
                    {hasAiSuggestion && !officer.name_override && (
                        <span className="ml-2 text-xs text-green-500">(AI)</span>
                    )}
                </div>
            )}
        </div>
    );
}
```

---

### 3. Officer Review Panel (Enhanced with Merge)

```jsx
// src/components/OfficerReviewPanel.jsx

export default function OfficerReviewPanel({ mediaId, officers, mergeSuggestions, onComplete }) {
    const [decisions, setDecisions] = useState(
        officers.reduce((acc, o) => ({ ...acc, [o.id]: o.confidence >= 0.8 }), {})
    );
    const [mergedGroups, setMergedGroups] = useState([]);
    const [selectedForMerge, setSelectedForMerge] = useState([]);
    const [showMergeSuggestions, setShowMergeSuggestions] = useState(true);

    // Process auto-merges (>95% confidence)
    useEffect(() => {
        const autoMerges = mergeSuggestions.filter(s => s.auto_merge);
        // Apply auto-merges...
    }, [mergeSuggestions]);

    const handleManualMerge = () => {
        if (selectedForMerge.length < 2) return;

        // Create merge group
        const newGroup = {
            id: `merge_${Date.now()}`,
            officer_ids: selectedForMerge,
            primary_id: selectedForMerge[0], // First selected becomes primary
        };

        setMergedGroups(prev => [...prev, newGroup]);
        setSelectedForMerge([]);
    };

    const handleUnmerge = (groupId) => {
        setMergedGroups(prev => prev.filter(g => g.id !== groupId));
    };

    return (
        <div className="min-h-screen bg-slate-950 p-6">
            <div className="max-w-7xl mx-auto">
                {/* Header */}
                <div className="text-center mb-8">
                    <h1 className="text-3xl font-bold text-white mb-2">
                        Officer Verification & Merge
                    </h1>
                    <p className="text-slate-400">
                        Review detections, merge duplicates, and confirm officers
                    </p>
                </div>

                {/* Merge Suggestions Panel */}
                {showMergeSuggestions && mergeSuggestions.length > 0 && (
                    <div className="mb-8">
                        <div className="flex items-center justify-between mb-4">
                            <h2 className="text-lg font-bold text-yellow-400 flex items-center gap-2">
                                <Zap className="h-5 w-5" />
                                Merge Suggestions ({mergeSuggestions.length})
                            </h2>
                            <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => setShowMergeSuggestions(false)}
                            >
                                Dismiss All
                            </Button>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            {mergeSuggestions.map((suggestion, idx) => (
                                <MergeSuggestionCard
                                    key={idx}
                                    suggestion={suggestion}
                                    officers={officers}
                                    onAccept={() => handleMergeAccept(suggestion)}
                                    onReject={() => handleMergeReject(suggestion)}
                                />
                            ))}
                        </div>
                    </div>
                )}

                {/* Manual Merge Selection Bar */}
                {selectedForMerge.length > 0 && (
                    <div className="sticky top-4 z-10 mb-6 p-4 bg-blue-900/50 border border-blue-500 rounded-xl flex items-center justify-between">
                        <div className="flex items-center gap-3">
                            <GitMerge className="h-5 w-5 text-blue-400" />
                            <span className="text-blue-200">
                                {selectedForMerge.length} officers selected for merge
                            </span>
                        </div>
                        <div className="flex gap-2">
                            <Button
                                variant="ghost"
                                onClick={() => setSelectedForMerge([])}
                                className="text-blue-300"
                            >
                                Cancel
                            </Button>
                            <Button
                                onClick={handleManualMerge}
                                className="bg-blue-600 hover:bg-blue-500"
                                disabled={selectedForMerge.length < 2}
                            >
                                Merge Selected ({selectedForMerge.length})
                            </Button>
                        </div>
                    </div>
                )}

                {/* Quick Actions */}
                <div className="flex flex-wrap gap-3 mb-6 justify-center">
                    <Button onClick={() => handleApproveAllAbove(0.8)} variant="outline">
                        <CheckCircle className="h-4 w-4 mr-2" />
                        Approve All 80%+
                    </Button>
                    <Button onClick={() => handleApproveAllAbove(0.6)} variant="outline">
                        Approve All 60%+
                    </Button>
                    <Button
                        onClick={() => setDecisions({})}
                        variant="ghost"
                        className="text-red-400"
                    >
                        Reject All
                    </Button>
                    <div className="w-px h-8 bg-slate-700" />
                    <Button
                        variant="outline"
                        className="border-blue-500 text-blue-400"
                        onClick={() => setSelectedForMerge([])}
                    >
                        <GitMerge className="h-4 w-4 mr-2" />
                        Manual Merge Mode
                    </Button>
                </div>

                {/* Merged Officers Section */}
                {mergedGroups.length > 0 && (
                    <div className="mb-8">
                        <h3 className="text-sm font-bold text-green-400 uppercase mb-4">
                            Merged Officers ({mergedGroups.length})
                        </h3>
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                            {mergedGroups.map((group) => (
                                <MergedOfficerCard
                                    key={group.id}
                                    group={group}
                                    officers={officers}
                                    onUnmerge={() => handleUnmerge(group.id)}
                                />
                            ))}
                        </div>
                    </div>
                )}

                {/* Individual Officers Grid */}
                <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
                    {officers
                        .filter(o => !mergedGroups.some(g => g.officer_ids.includes(o.id)))
                        .map((officer) => (
                            <OfficerReviewCard
                                key={officer.id}
                                officer={officer}
                                approved={decisions[officer.id]}
                                selected={selectedForMerge.includes(officer.id)}
                                onToggleApprove={() => toggleApproval(officer.id)}
                                onToggleSelect={() => toggleMergeSelect(officer.id)}
                                showMergeCheckbox={selectedForMerge.length > 0}
                            />
                        ))}
                </div>

                {/* Footer */}
                <div className="mt-8 p-6 bg-slate-900 rounded-xl">
                    <div className="flex flex-col md:flex-row justify-between items-center gap-4">
                        <div className="text-slate-400 text-center md:text-left">
                            <div className="text-2xl font-bold text-white">
                                {approvedCount} officers approved
                            </div>
                            <div className="text-sm">
                                {mergedGroups.length} merge groups • {officers.length - mergedCount} individual
                            </div>
                        </div>
                        <Button
                            onClick={() => onComplete({
                                decisions,
                                mergedGroups,
                                officers: getProcessedOfficers()
                            })}
                            className="bg-green-600 hover:bg-green-500 px-8"
                            disabled={approvedCount === 0}
                            size="lg"
                        >
                            Continue to Detail Editing
                            <ArrowRight className="h-5 w-5 ml-2" />
                        </Button>
                    </div>
                </div>
            </div>
        </div>
    );
}
```

---

### 4. Officer Detail Editor (with Name Field)

```jsx
// src/components/OfficerDetailEditor.jsx

export default function OfficerDetailEditor({ officers, onComplete, onBack }) {
    const [currentIndex, setCurrentIndex] = useState(0);
    const [edits, setEdits] = useState({});

    const currentOfficer = officers[currentIndex];
    const officerEdits = edits[currentOfficer.id] || {};

    const updateField = (field, value) => {
        setEdits(prev => ({
            ...prev,
            [currentOfficer.id]: {
                ...prev[currentOfficer.id],
                [field]: value
            }
        }));
    };

    const goNext = () => {
        if (currentIndex < officers.length - 1) {
            setCurrentIndex(prev => prev + 1);
        }
    };

    const goPrev = () => {
        if (currentIndex > 0) {
            setCurrentIndex(prev => prev - 1);
        }
    };

    return (
        <div className="min-h-screen bg-slate-950 p-6">
            <div className="max-w-4xl mx-auto">
                {/* Progress Bar */}
                <div className="mb-6">
                    <div className="flex justify-between text-sm text-slate-400 mb-2">
                        <span>Officer {currentIndex + 1} of {officers.length}</span>
                        <span>{Math.round(((currentIndex + 1) / officers.length) * 100)}% complete</span>
                    </div>
                    <div className="h-2 bg-slate-800 rounded-full overflow-hidden">
                        <div
                            className="h-full bg-green-500 transition-all duration-300"
                            style={{ width: `${((currentIndex + 1) / officers.length) * 100}%` }}
                        />
                    </div>
                </div>

                {/* Main Editor Card */}
                <Card className="bg-slate-900 border-slate-800 overflow-hidden">
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-0">
                        {/* Left: Photo Section */}
                        <div className="bg-slate-950 p-6">
                            {/* Primary Image */}
                            <div className="aspect-square bg-slate-800 rounded-xl overflow-hidden mb-4 relative">
                                <img
                                    src={getCropUrl(currentOfficer.best_crop_path)}
                                    className="w-full h-full object-cover"
                                    alt={`Officer ${currentIndex + 1}`}
                                />
                                <div className="absolute top-3 left-3 bg-black/75 px-3 py-1 rounded-full text-white text-sm font-bold">
                                    #{currentIndex + 1}
                                </div>
                                {currentOfficer.isMerged && (
                                    <div className="absolute top-3 right-3 bg-blue-600 px-2 py-1 rounded-full text-white text-xs flex items-center gap-1">
                                        <GitMerge className="h-3 w-3" />
                                        Merged
                                    </div>
                                )}
                            </div>

                            {/* Other Appearances (if merged) */}
                            {currentOfficer.all_crops?.length > 1 && (
                                <div>
                                    <p className="text-xs text-slate-500 uppercase font-bold mb-2">
                                        All Appearances ({currentOfficer.all_crops.length})
                                    </p>
                                    <div className="flex gap-2 overflow-x-auto pb-2">
                                        {currentOfficer.all_crops.map((crop, idx) => (
                                            <div
                                                key={idx}
                                                className="flex-shrink-0 w-16 h-16 rounded-lg overflow-hidden border border-slate-700"
                                            >
                                                <img
                                                    src={getCropUrl(crop.path)}
                                                    className="w-full h-full object-cover"
                                                    alt={`Appearance ${idx + 1}`}
                                                />
                                                <div className="absolute bottom-0 left-0 right-0 bg-black/75 text-[10px] text-white text-center py-0.5">
                                                    {crop.timestamp}
                                                </div>
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
                                            currentOfficer.confidence >= 0.8 ? 'text-green-400' :
                                            currentOfficer.confidence >= 0.6 ? 'text-yellow-400' :
                                            'text-red-400'
                                        }`}>
                                            {(currentOfficer.confidence * 100).toFixed(0)}%
                                        </span>
                                    </div>
                                    <div>
                                        <span className="text-slate-500">Appearances:</span>
                                        <span className="ml-2 text-white font-bold">
                                            {currentOfficer.total_appearances || 1}
                                        </span>
                                    </div>
                                </div>
                            </div>
                        </div>

                        {/* Right: Form Fields */}
                        <div className="p-6 space-y-5">
                            <h2 className="text-xl font-bold text-white mb-6">
                                Edit Officer Details
                            </h2>

                            {/* Officer Name (from uniform label) */}
                            <EditableNameField
                                officer={currentOfficer}
                                value={officerEdits.name_override}
                                onUpdate={(val) => updateField('name_override', val)}
                            />

                            {/* Badge Number */}
                            <div>
                                <label className="text-xs text-slate-500 uppercase font-bold mb-1 block">
                                    Shoulder Number / Badge
                                    {currentOfficer.ocr_badge_result && !officerEdits.badge_override && (
                                        <span className="ml-2 text-green-400 font-normal text-[10px]">
                                            OCR detected ({(currentOfficer.ocr_badge_confidence * 100).toFixed(0)}%)
                                        </span>
                                    )}
                                </label>
                                <input
                                    type="text"
                                    value={officerEdits.badge_override ?? currentOfficer.badge ?? ''}
                                    onChange={(e) => updateField('badge_override', e.target.value.toUpperCase())}
                                    placeholder="e.g. U1234, MPS456"
                                    className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-3
                                               text-white font-mono text-lg focus:border-blue-500 focus:ring-1
                                               focus:ring-blue-500/50 outline-none transition"
                                />
                                {currentOfficer.ocr_badge_result && (
                                    <p className="text-xs text-slate-500 mt-1">
                                        AI suggestion: <span className="text-green-400 font-mono">{currentOfficer.ocr_badge_result}</span>
                                    </p>
                                )}
                            </div>

                            {/* Police Force */}
                            <div>
                                <label className="text-xs text-slate-500 uppercase font-bold mb-1 block">
                                    Police Force
                                    {currentOfficer.ai_force && !officerEdits.force_override && (
                                        <span className="ml-2 text-green-400 font-normal text-[10px]">
                                            AI detected
                                        </span>
                                    )}
                                </label>
                                <select
                                    value={officerEdits.force_override ?? currentOfficer.force ?? ''}
                                    onChange={(e) => updateField('force_override', e.target.value)}
                                    className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-3
                                               text-white focus:border-blue-500 outline-none transition"
                                >
                                    <option value="">Select Force...</option>
                                    {UK_POLICE_FORCES.map(force => (
                                        <option key={force.value} value={force.value}>
                                            {force.label}
                                        </option>
                                    ))}
                                </select>
                            </div>

                            {/* Rank */}
                            <div>
                                <label className="text-xs text-slate-500 uppercase font-bold mb-1 block">
                                    Rank
                                    {currentOfficer.ai_rank && !officerEdits.rank_override && (
                                        <span className="ml-2 text-green-400 font-normal text-[10px]">
                                            AI detected
                                        </span>
                                    )}
                                </label>
                                <select
                                    value={officerEdits.rank_override ?? currentOfficer.rank ?? ''}
                                    onChange={(e) => updateField('rank_override', e.target.value)}
                                    className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-3
                                               text-white focus:border-blue-500 outline-none transition"
                                >
                                    <option value="">Select Rank...</option>
                                    {UK_POLICE_RANKS.map(rank => (
                                        <option key={rank.value} value={rank.value}>
                                            {rank.label}
                                        </option>
                                    ))}
                                </select>
                            </div>

                            {/* Role/Unit Tags */}
                            <div>
                                <label className="text-xs text-slate-500 uppercase font-bold mb-1 block">
                                    Role / Unit
                                </label>
                                <div className="flex flex-wrap gap-2 mb-2">
                                    {ROLE_OPTIONS.map(role => {
                                        const selected = (officerEdits.roles || currentOfficer.roles || []).includes(role.value);
                                        return (
                                            <button
                                                key={role.value}
                                                type="button"
                                                onClick={() => toggleRole(role.value)}
                                                className={`px-3 py-1.5 rounded-full text-sm font-medium transition ${
                                                    selected
                                                        ? 'bg-green-600 text-white'
                                                        : 'bg-slate-800 text-slate-400 hover:bg-slate-700'
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
                                <label className="text-xs text-slate-500 uppercase font-bold mb-1 block">
                                    Observer Notes
                                </label>
                                <textarea
                                    value={officerEdits.notes ?? currentOfficer.notes ?? ''}
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
                            className="text-slate-400"
                        >
                            <ChevronLeft className="h-5 w-5 mr-1" />
                            Previous
                        </Button>

                        <div className="flex gap-2">
                            {officers.map((_, idx) => (
                                <button
                                    key={idx}
                                    onClick={() => setCurrentIndex(idx)}
                                    className={`w-2 h-2 rounded-full transition ${
                                        idx === currentIndex
                                            ? 'bg-green-500 w-6'
                                            : edits[officers[idx].id]
                                                ? 'bg-blue-500'
                                                : 'bg-slate-700'
                                    }`}
                                />
                            ))}
                        </div>

                        {currentIndex < officers.length - 1 ? (
                            <Button
                                onClick={goNext}
                                className="bg-green-600 hover:bg-green-500"
                            >
                                Save & Next
                                <ChevronRight className="h-5 w-5 ml-1" />
                            </Button>
                        ) : (
                            <Button
                                onClick={() => onComplete(edits)}
                                className="bg-green-600 hover:bg-green-500"
                            >
                                Finish Editing
                                <Check className="h-5 w-5 ml-1" />
                            </Button>
                        )}
                    </div>
                </Card>

                {/* Back Button */}
                <div className="mt-4 text-center">
                    <Button variant="ghost" onClick={onBack} className="text-slate-500">
                        <ArrowLeft className="h-4 w-4 mr-2" />
                        Back to Review Panel
                    </Button>
                </div>
            </div>
        </div>
    );
}
```

---

### 5. Database Schema Updates

```python
# backend/models.py - Updated with merge support and name field

class Officer(Base):
    __tablename__ = 'officers'

    id = Column(Integer, primary_key=True)

    # Primary identification
    badge_number = Column(String, nullable=True, index=True)
    name = Column(String, nullable=True)  # NEW: Officer name from uniform label

    # AI-detected fields
    ai_name = Column(String, nullable=True)
    ai_name_confidence = Column(Float, nullable=True)

    # Manual overrides
    name_override = Column(String, nullable=True)
    badge_override = Column(String, nullable=True)

    # Force and rank
    force = Column(String, nullable=True)
    force_override = Column(String, nullable=True)

    # Face embedding for re-identification
    face_embedding = Column(LargeBinary, nullable=True)

    # Best photo
    primary_crop_path = Column(String, nullable=True)

    # Merge tracking
    merged_into_id = Column(Integer, ForeignKey('officers.id'), nullable=True)
    merge_confidence = Column(Float, nullable=True)
    merged_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    appearances = relationship("OfficerAppearance", back_populates="officer")
    merged_from = relationship("Officer", backref=backref('merged_into', remote_side=[id]))


class OfficerAppearance(Base):
    __tablename__ = 'officer_appearances'

    id = Column(Integer, primary_key=True)
    officer_id = Column(Integer, ForeignKey('officers.id'), index=True)
    media_id = Column(Integer, ForeignKey('media.id'), index=True)

    # Timestamps
    timestamp_in_video = Column(String, nullable=True)
    frame_number = Column(Integer, nullable=True)

    # Image crops
    image_crop_path = Column(String, nullable=True)
    face_crop_path = Column(String, nullable=True)
    body_crop_path = Column(String, nullable=True)

    # Detection data
    confidence = Column(Float, default=0.0)
    face_embedding = Column(LargeBinary, nullable=True)

    # OCR results
    ocr_badge_result = Column(String, nullable=True)
    ocr_badge_confidence = Column(Float, nullable=True)
    ocr_name_result = Column(String, nullable=True)  # NEW
    ocr_name_confidence = Column(Float, nullable=True)  # NEW

    # AI analysis results
    ai_force = Column(String, nullable=True)
    ai_force_confidence = Column(Float, nullable=True)
    ai_rank = Column(String, nullable=True)
    ai_rank_confidence = Column(Float, nullable=True)
    ai_name = Column(String, nullable=True)  # NEW: from Claude Vision
    ai_name_confidence = Column(Float, nullable=True)  # NEW

    # Verification
    verified = Column(Boolean, default=False)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    verified_by = Column(Integer, ForeignKey('users.id'), nullable=True)

    # Manual overrides
    badge_override = Column(String, nullable=True)
    force_override = Column(String, nullable=True)
    rank_override = Column(String, nullable=True)
    name_override = Column(String, nullable=True)  # NEW
    role_override = Column(String, nullable=True)
    notes = Column(Text, nullable=True)

    # Action context
    action = Column(String, nullable=True)
    role = Column(String, nullable=True)

    # Relationships
    officer = relationship("Officer", back_populates="appearances")
    media = relationship("Media", back_populates="appearances")


class OfficerMerge(Base):
    """Track merge history for audit trail"""
    __tablename__ = 'officer_merges'

    id = Column(Integer, primary_key=True)

    # Merge participants
    primary_officer_id = Column(Integer, ForeignKey('officers.id'))
    merged_officer_id = Column(Integer, ForeignKey('officers.id'))

    # Merge metadata
    merge_confidence = Column(Float, nullable=True)
    auto_merged = Column(Boolean, default=False)
    merged_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    merged_by = Column(Integer, ForeignKey('users.id'), nullable=True)

    # For unmerge capability
    unmerged = Column(Boolean, default=False)
    unmerged_at = Column(DateTime(timezone=True), nullable=True)
    unmerged_by = Column(Integer, ForeignKey('users.id'), nullable=True)
```

---

### 6. New API Endpoints

```python
# backend/main.py - New endpoints for merge system

@app.post("/media/{media_id}/officers/merge")
def merge_officers(
    media_id: int,
    merge_request: schemas.MergeRequest,
    db: Session = Depends(get_db)
):
    """
    Merge multiple officer detections into a single officer.
    The first officer_id in the list becomes the primary.
    """
    if len(merge_request.officer_ids) < 2:
        raise HTTPException(400, "Need at least 2 officers to merge")

    primary_id = merge_request.officer_ids[0]
    to_merge_ids = merge_request.officer_ids[1:]

    # Get all officers
    primary = db.query(models.Officer).filter(models.Officer.id == primary_id).first()
    if not primary:
        raise HTTPException(404, f"Primary officer {primary_id} not found")

    merged_count = 0
    for merge_id in to_merge_ids:
        officer = db.query(models.Officer).filter(models.Officer.id == merge_id).first()
        if officer:
            # Move all appearances to primary officer
            db.query(models.OfficerAppearance).filter(
                models.OfficerAppearance.officer_id == merge_id
            ).update({"officer_id": primary_id})

            # Mark as merged
            officer.merged_into_id = primary_id
            officer.merge_confidence = merge_request.confidence
            officer.merged_at = datetime.now(timezone.utc)

            # Record merge history
            merge_record = models.OfficerMerge(
                primary_officer_id=primary_id,
                merged_officer_id=merge_id,
                merge_confidence=merge_request.confidence,
                auto_merged=merge_request.auto_merged
            )
            db.add(merge_record)
            merged_count += 1

    # Update primary officer's best crop if needed
    update_best_crop(db, primary)

    db.commit()

    return {
        "primary_officer_id": primary_id,
        "merged_count": merged_count,
        "total_appearances": db.query(models.OfficerAppearance).filter(
            models.OfficerAppearance.officer_id == primary_id
        ).count()
    }


@app.post("/officers/{officer_id}/unmerge")
def unmerge_officer(
    officer_id: int,
    unmerge_request: schemas.UnmergeRequest,
    db: Session = Depends(get_db)
):
    """
    Unmerge specific appearances back into a new separate officer.
    """
    # Get appearances to split
    appearances = db.query(models.OfficerAppearance).filter(
        models.OfficerAppearance.id.in_(unmerge_request.appearance_ids),
        models.OfficerAppearance.officer_id == officer_id
    ).all()

    if not appearances:
        raise HTTPException(404, "No matching appearances found")

    # Create new officer from split appearances
    new_officer = models.Officer(
        badge_number=appearances[0].ocr_badge_result,
        face_embedding=appearances[0].face_embedding,
        primary_crop_path=appearances[0].image_crop_path
    )
    db.add(new_officer)
    db.flush()

    # Move appearances to new officer
    for app in appearances:
        app.officer_id = new_officer.id

    # Mark unmerge in history
    merge_record = db.query(models.OfficerMerge).filter(
        models.OfficerMerge.primary_officer_id == officer_id,
        models.OfficerMerge.unmerged == False
    ).first()
    if merge_record:
        merge_record.unmerged = True
        merge_record.unmerged_at = datetime.now(timezone.utc)

    db.commit()

    return {
        "new_officer_id": new_officer.id,
        "appearances_moved": len(appearances),
        "original_officer_id": officer_id
    }


@app.get("/media/{media_id}/merge-suggestions")
def get_merge_suggestions(
    media_id: int,
    threshold: float = 0.85,
    db: Session = Depends(get_db)
):
    """
    Get suggested officer merges based on face embedding similarity.
    """
    appearances = db.query(models.OfficerAppearance).filter(
        models.OfficerAppearance.media_id == media_id,
        models.OfficerAppearance.face_embedding.isnot(None)
    ).all()

    suggestions = []
    processed_pairs = set()

    for i, app1 in enumerate(appearances):
        for app2 in appearances[i+1:]:
            if app1.officer_id == app2.officer_id:
                continue

            pair_key = tuple(sorted([app1.officer_id, app2.officer_id]))
            if pair_key in processed_pairs:
                continue

            # Calculate embedding similarity
            emb1 = np.frombuffer(app1.face_embedding, dtype=np.float32)
            emb2 = np.frombuffer(app2.face_embedding, dtype=np.float32)
            similarity = float(np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2)))

            if similarity >= threshold:
                suggestions.append({
                    "officer_a_id": app1.officer_id,
                    "officer_b_id": app2.officer_id,
                    "appearance_a_id": app1.id,
                    "appearance_b_id": app2.id,
                    "confidence": similarity,
                    "auto_merge": similarity >= 0.95,
                    "crop_a": app1.image_crop_path,
                    "crop_b": app2.image_crop_path
                })
                processed_pairs.add(pair_key)

    # Sort by confidence descending
    suggestions.sort(key=lambda x: x["confidence"], reverse=True)

    return {"suggestions": suggestions}


@app.post("/media/{media_id}/officers/batch-update")
def batch_update_officers(
    media_id: int,
    updates: List[schemas.OfficerUpdate],
    db: Session = Depends(get_db)
):
    """
    Batch update multiple officers with verification status and overrides.
    """
    updated = 0
    for update in updates:
        appearance = db.query(models.OfficerAppearance).filter(
            models.OfficerAppearance.id == update.appearance_id,
            models.OfficerAppearance.media_id == media_id
        ).first()

        if appearance:
            appearance.verified = update.verified
            appearance.verified_at = datetime.now(timezone.utc) if update.verified else None

            # Apply overrides
            if update.badge_override is not None:
                appearance.badge_override = update.badge_override
            if update.name_override is not None:
                appearance.name_override = update.name_override
            if update.force_override is not None:
                appearance.force_override = update.force_override
            if update.rank_override is not None:
                appearance.rank_override = update.rank_override
            if update.role_override is not None:
                appearance.role_override = update.role_override
            if update.notes is not None:
                appearance.notes = update.notes

            updated += 1

    db.commit()

    return {"updated": updated}
```

---

### 7. Schemas

```python
# backend/schemas.py - New schemas

class MergeRequest(BaseModel):
    officer_ids: List[int]
    confidence: float = 0.0
    auto_merged: bool = False

class UnmergeRequest(BaseModel):
    appearance_ids: List[int]

class OfficerUpdate(BaseModel):
    appearance_id: int
    verified: bool = False
    badge_override: Optional[str] = None
    name_override: Optional[str] = None
    force_override: Optional[str] = None
    rank_override: Optional[str] = None
    role_override: Optional[str] = None
    notes: Optional[str] = None

class MergeSuggestion(BaseModel):
    officer_a_id: int
    officer_b_id: int
    confidence: float
    auto_merge: bool
    crop_a: Optional[str]
    crop_b: Optional[str]
```

---

## Enhanced Report Visual Design

### Officer Card (Final Report)

```
┌─────────────────────────────────────────────────────────────────────┐
│  ┌──────────────────┐                                               │
│  │                  │   PC WILLIAMS                                 │
│  │    [OFFICER      │   Badge: U1234                                │
│  │     PHOTO]       │   Metropolitan Police Service                 │
│  │                  │   Rank: Police Constable                      │
│  │                  │   Role: PSU, Evidence Gatherer                │
│  └──────────────────┘                                               │
│                                                                     │
│  ┌─ SOURCE IMAGES ───────────────────────────────────────────────┐ │
│  │  ┌────┐  ┌────┐  ┌────┐                                       │ │
│  │  │0:12│  │1:45│  │2:33│  3 appearances verified               │ │
│  │  └────┘  └────┘  └────┘                                       │ │
│  └───────────────────────────────────────────────────────────────┘ │
│                                                                     │
│  Observer Notes:                                                    │
│  "Observed using baton during kettling at 1:45"                    │
│                                                                     │
│  ─────────────────────────────────────────────────────────────────  │
│  Detection: AI ✓  |  Verified: Human ✓  |  Confidence: 94%         │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Implementation Phases (Updated)

### Phase 1: Backend Foundation (3-4 days)
- [ ] Add name fields to models
- [ ] Add merge tracking tables
- [ ] Enable OCR for badge AND name detection
- [ ] Create merge/unmerge endpoints
- [ ] Create batch update endpoint
- [ ] Create merge suggestions endpoint
- [ ] Database migration

### Phase 2: Officer Review Panel (3-4 days)
- [ ] Build OfficerReviewPanel component
- [ ] Implement merge suggestion cards
- [ ] Implement manual merge selection
- [ ] Implement unmerge flow
- [ ] Quick approve/reject actions
- [ ] Connect to merge API

### Phase 3: Detail Editor (2-3 days)
- [ ] Build OfficerDetailEditor component
- [ ] Editable name field with AI suggestion
- [ ] All other editable fields
- [ ] Progress indicator
- [ ] Navigation between officers
- [ ] Persist to batch update API

### Phase 4: Report Redesign (2-3 days)
- [ ] Enhanced officer gallery cards
- [ ] Force breakdown chart
- [ ] Appearance timeline
- [ ] Equipment grid
- [ ] Source provenance section
- [ ] Export options

### Phase 5: Integration & Testing (2 days)
- [ ] Wire up full flow in UploadPage
- [ ] Test merge/unmerge workflows
- [ ] Test OCR accuracy
- [ ] Mobile responsiveness
- [ ] Print styles

---

## File Changes Summary

### New Files
```
src/components/OfficerReviewPanel.jsx
src/components/OfficerDetailEditor.jsx
src/components/EditableNameField.jsx
src/components/MergeSuggestionCard.jsx
src/components/MergedOfficerCard.jsx
src/components/UnmergeModal.jsx
src/components/ReportPreview.jsx
src/components/DataVisualization/
backend/ai/name_detector.py
alembic/versions/xxx_add_merge_and_name_fields.py
```

### Modified Files
```
src/pages/UploadPage.jsx
src/pages/ReportPage.jsx
src/components/LiveAnalysis.jsx
backend/main.py
backend/models.py
backend/schemas.py
backend/ai/analyzer.py
backend/ai/uniform_analyzer.py
backend/reports.py
```

---

## Success Metrics

1. **Merge Accuracy**: Auto-merge false positive rate < 2%
2. **OCR Name Detection**: > 60% accuracy on clear uniform labels
3. **User Completion**: > 80% of users complete full verification flow
4. **Time to Report**: Average 5-10 minutes for 10 officer review

---

*Document created: 14 December 2024*
*Last updated: 14 December 2024*
*Author: Claude Code Assistant*

import { useState, useRef, useCallback, useEffect } from 'react';
import ReactPlayer from 'react-player';
import { Play, Pause, Volume2, VolumeX, Maximize, SkipBack, SkipForward, Clock, User } from 'lucide-react';
import { sanitizeMediaPath } from '../utils/api';

/**
 * Parse timestamp string to seconds.
 * Supports formats: "HH:MM:SS", "MM:SS", "SS"
 */
const parseTimestamp = (timestamp) => {
  if (!timestamp) return 0;
  const parts = timestamp.split(':').map(Number);
  if (parts.length === 3) {
    return parts[0] * 3600 + parts[1] * 60 + parts[2];
  } else if (parts.length === 2) {
    return parts[0] * 60 + parts[1];
  }
  return parts[0] || 0;
};

/**
 * Format seconds to timestamp string.
 */
const formatTime = (seconds) => {
  if (!seconds || isNaN(seconds)) return '0:00';
  const hrs = Math.floor(seconds / 3600);
  const mins = Math.floor((seconds % 3600) / 60);
  const secs = Math.floor(seconds % 60);
  if (hrs > 0) {
    return `${hrs}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  }
  return `${mins}:${secs.toString().padStart(2, '0')}`;
};

/**
 * VideoPlayer component with timeline markers for officer appearances.
 *
 * Props:
 * - url: Video URL (YouTube, direct file, etc.)
 * - timeline: Array of timeline markers with officer appearances
 * - onMarkerClick: Callback when a marker is clicked
 * - apiBase: API base URL for serving local files
 */
export default function VideoPlayer({ url, timeline = [], onMarkerClick, apiBase }) {
  const playerRef = useRef(null);
  const progressBarRef = useRef(null);
  const [playing, setPlaying] = useState(false);
  const [muted, setMuted] = useState(false);
  const [volume, setVolume] = useState(0.8);
  const [played, setPlayed] = useState(0);
  const [duration, setDuration] = useState(0);
  const [seeking, setSeeking] = useState(false);
  const [hoveredMarker, setHoveredMarker] = useState(null);
  const [activeMarker, setActiveMarker] = useState(null);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const containerRef = useRef(null);

  // Determine if URL is local file (needs API base prepended)
  const getVideoUrl = () => {
    if (!url) return '';
    if (url.startsWith('http://') || url.startsWith('https://')) {
      return url;
    }
    // Local file - use secure path sanitization
    const cleanPath = sanitizeMediaPath(url);
    if (!cleanPath) return '';
    return `${apiBase}/data/${cleanPath}`;
  };

  const videoUrl = getVideoUrl();

  // Handle play/pause
  const handlePlayPause = useCallback(() => {
    setPlaying(prev => !prev);
  }, []);

  // Handle seeking
  const handleSeekMouseDown = () => setSeeking(true);

  const handleSeekChange = (e) => {
    const rect = progressBarRef.current.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const newPlayed = Math.max(0, Math.min(1, clickX / rect.width));
    setPlayed(newPlayed);
  };

  const handleSeekMouseUp = (e) => {
    setSeeking(false);
    const rect = progressBarRef.current.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const newPlayed = Math.max(0, Math.min(1, clickX / rect.width));
    playerRef.current?.seekTo(newPlayed);
  };

  // Handle progress bar click
  const handleProgressClick = (e) => {
    const rect = progressBarRef.current.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const newPlayed = Math.max(0, Math.min(1, clickX / rect.width));
    setPlayed(newPlayed);
    playerRef.current?.seekTo(newPlayed);
  };

  // Handle progress update from player
  const handleProgress = (state) => {
    if (!seeking) {
      setPlayed(state.played);

      // Check if current time matches any marker (within 1 second)
      const currentTime = state.playedSeconds;
      const matchingMarker = timeline.find(marker => {
        const markerTime = parseTimestamp(marker.timestamp);
        return Math.abs(currentTime - markerTime) < 1;
      });

      if (matchingMarker && activeMarker?.timestamp !== matchingMarker.timestamp) {
        setActiveMarker(matchingMarker);
      } else if (!matchingMarker && activeMarker) {
        // Keep marker visible for a bit longer
        setTimeout(() => setActiveMarker(null), 2000);
      }
    }
  };

  // Seek to specific timestamp
  const seekToTimestamp = useCallback((timestamp) => {
    const seconds = parseTimestamp(timestamp);
    if (duration > 0 && playerRef.current) {
      playerRef.current.seekTo(seconds / duration, 'fraction');
      setPlaying(true);
    }
  }, [duration]);

  // Handle marker click
  const handleMarkerClick = (marker) => {
    seekToTimestamp(marker.timestamp);
    setActiveMarker(marker);
    onMarkerClick?.(marker);
  };

  // Skip forward/backward
  const handleSkip = (seconds) => {
    const currentTime = played * duration;
    const newTime = Math.max(0, Math.min(duration, currentTime + seconds));
    playerRef.current?.seekTo(newTime / duration, 'fraction');
  };

  // Fullscreen toggle
  const handleFullscreen = () => {
    if (!document.fullscreenElement) {
      containerRef.current?.requestFullscreen();
      setIsFullscreen(true);
    } else {
      document.exitFullscreen();
      setIsFullscreen(false);
    }
  };

  // Listen for fullscreen changes
  useEffect(() => {
    const handleFullscreenChange = () => {
      setIsFullscreen(!!document.fullscreenElement);
    };
    document.addEventListener('fullscreenchange', handleFullscreenChange);
    return () => document.removeEventListener('fullscreenchange', handleFullscreenChange);
  }, []);

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyPress = (e) => {
      if (e.target.tagName === 'INPUT') return;
      switch (e.key) {
        case ' ':
          e.preventDefault();
          handlePlayPause();
          break;
        case 'ArrowLeft':
          e.preventDefault();
          handleSkip(-10);
          break;
        case 'ArrowRight':
          e.preventDefault();
          handleSkip(10);
          break;
        case 'm':
          setMuted(prev => !prev);
          break;
        case 'f':
          handleFullscreen();
          break;
      }
    };
    window.addEventListener('keydown', handleKeyPress);
    return () => window.removeEventListener('keydown', handleKeyPress);
  }, [handlePlayPause, handleSkip]);

  // Calculate marker positions
  const getMarkerPosition = (timestamp) => {
    if (!duration) return 0;
    const seconds = parseTimestamp(timestamp);
    return (seconds / duration) * 100;
  };

  // Group nearby markers to prevent overlap
  const groupedMarkers = timeline.reduce((acc, marker) => {
    const pos = getMarkerPosition(marker.timestamp);
    const existing = acc.find(m => Math.abs(getMarkerPosition(m[0].timestamp) - pos) < 2);
    if (existing) {
      existing.push(marker);
    } else {
      acc.push([marker]);
    }
    return acc;
  }, []);

  return (
    <div ref={containerRef} className="video-player-container bg-black rounded-lg overflow-hidden">
      {/* Video Player */}
      <div className="relative aspect-video bg-black">
        <ReactPlayer
          ref={playerRef}
          url={videoUrl}
          playing={playing}
          muted={muted}
          volume={volume}
          width="100%"
          height="100%"
          onProgress={handleProgress}
          onDuration={setDuration}
          progressInterval={250}
          config={{
            file: {
              attributes: {
                crossOrigin: 'anonymous'
              }
            }
          }}
        />

        {/* Active Marker Overlay */}
        {activeMarker && (
          <div className="absolute top-4 right-4 bg-black/80 text-white p-3 rounded-lg max-w-xs animate-in fade-in slide-in-from-right duration-300">
            <div className="flex items-center gap-2 mb-2">
              <User className="h-4 w-4 text-green-400" />
              <span className="font-bold text-green-400">
                Officer #{activeMarker.officer_id}
              </span>
              {activeMarker.badge && (
                <span className="text-xs bg-gray-700 px-2 py-0.5 rounded">
                  Badge: {activeMarker.badge}
                </span>
              )}
            </div>
            <div className="flex items-center gap-2 text-sm text-gray-300">
              <Clock className="h-3 w-3" />
              <span>{activeMarker.timestamp}</span>
            </div>
            {activeMarker.action && (
              <p className="text-xs text-gray-400 mt-1 line-clamp-2">
                {activeMarker.action}
              </p>
            )}
          </div>
        )}

        {/* Play/Pause overlay on click */}
        <div
          className="absolute inset-0 cursor-pointer"
          onClick={handlePlayPause}
        />
      </div>

      {/* Controls */}
      <div className="bg-slate-900 p-3">
        {/* Progress Bar with Markers */}
        <div className="relative mb-3">
          {/* Clickable progress bar */}
          <div
            ref={progressBarRef}
            className="h-2 bg-gray-700 rounded-full cursor-pointer relative group"
            onClick={handleProgressClick}
            onMouseDown={handleSeekMouseDown}
            onMouseUp={handleSeekMouseUp}
          >
            {/* Played progress */}
            <div
              className="absolute top-0 left-0 h-full bg-green-500 rounded-full transition-all"
              style={{ width: `${played * 100}%` }}
            />

            {/* Seek handle */}
            <div
              className="absolute top-1/2 -translate-y-1/2 w-4 h-4 bg-white rounded-full shadow-lg opacity-0 group-hover:opacity-100 transition-opacity"
              style={{ left: `calc(${played * 100}% - 8px)` }}
            />
          </div>

          {/* Timeline Markers */}
          <div className="absolute top-0 left-0 w-full h-2 pointer-events-none">
            {groupedMarkers.map((group, idx) => {
              const position = getMarkerPosition(group[0].timestamp);
              const isHovered = hoveredMarker === idx;
              const markerCount = group.length;

              return (
                <div
                  key={idx}
                  className="absolute top-1/2 -translate-y-1/2 pointer-events-auto"
                  style={{ left: `${position}%` }}
                  onMouseEnter={() => setHoveredMarker(idx)}
                  onMouseLeave={() => setHoveredMarker(null)}
                  onClick={(e) => {
                    e.stopPropagation();
                    handleMarkerClick(group[0]);
                  }}
                >
                  {/* Marker dot */}
                  <div
                    className={`w-3 h-3 -ml-1.5 rounded-full cursor-pointer transition-all ${
                      markerCount > 1
                        ? 'bg-red-500 ring-2 ring-red-300'
                        : 'bg-yellow-400'
                    } ${isHovered ? 'scale-150' : ''}`}
                  />

                  {/* Marker tooltip */}
                  {isHovered && (
                    <div className="absolute bottom-full mb-2 left-1/2 -translate-x-1/2 bg-black/90 text-white text-xs p-2 rounded whitespace-nowrap z-10">
                      <div className="font-bold text-green-400">
                        {markerCount > 1
                          ? `${markerCount} officers detected`
                          : `Officer #${group[0].officer_id}`
                        }
                      </div>
                      <div className="text-gray-300">{group[0].timestamp}</div>
                      {markerCount === 1 && group[0].action && (
                        <div className="text-gray-400 max-w-[200px] truncate">
                          {group[0].action}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* Control buttons */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            {/* Skip back */}
            <button
              onClick={() => handleSkip(-10)}
              className="p-2 text-white hover:bg-white/10 rounded-full transition"
              title="Skip back 10s"
            >
              <SkipBack className="h-4 w-4" />
            </button>

            {/* Play/Pause */}
            <button
              onClick={handlePlayPause}
              className="p-2 bg-green-600 hover:bg-green-700 text-white rounded-full transition"
            >
              {playing ? <Pause className="h-5 w-5" /> : <Play className="h-5 w-5 ml-0.5" />}
            </button>

            {/* Skip forward */}
            <button
              onClick={() => handleSkip(10)}
              className="p-2 text-white hover:bg-white/10 rounded-full transition"
              title="Skip forward 10s"
            >
              <SkipForward className="h-4 w-4" />
            </button>

            {/* Time display */}
            <span className="text-white text-sm ml-2 font-mono">
              {formatTime(played * duration)} / {formatTime(duration)}
            </span>
          </div>

          <div className="flex items-center gap-2">
            {/* Marker count */}
            {timeline.length > 0 && (
              <span className="text-yellow-400 text-xs font-medium mr-2">
                {timeline.length} detection{timeline.length !== 1 ? 's' : ''}
              </span>
            )}

            {/* Volume */}
            <div className="flex items-center gap-1 group">
              <button
                onClick={() => setMuted(prev => !prev)}
                className="p-2 text-white hover:bg-white/10 rounded-full transition"
              >
                {muted ? <VolumeX className="h-4 w-4" /> : <Volume2 className="h-4 w-4" />}
              </button>
              <input
                type="range"
                min={0}
                max={1}
                step={0.1}
                value={muted ? 0 : volume}
                onChange={(e) => {
                  setVolume(parseFloat(e.target.value));
                  setMuted(false);
                }}
                className="w-16 h-1 opacity-0 group-hover:opacity-100 transition-opacity cursor-pointer"
              />
            </div>

            {/* Fullscreen */}
            <button
              onClick={handleFullscreen}
              className="p-2 text-white hover:bg-white/10 rounded-full transition"
              title="Fullscreen"
            >
              <Maximize className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Timeline List (below player) */}
      {timeline.length > 0 && (
        <div className="bg-slate-800 border-t border-slate-700 max-h-48 overflow-y-auto">
          <div className="p-2">
            <h4 className="text-xs text-gray-400 font-bold uppercase px-2 mb-2">
              Officer Detections Timeline
            </h4>
            <div className="space-y-1">
              {timeline.map((marker, idx) => (
                <button
                  key={idx}
                  onClick={() => handleMarkerClick(marker)}
                  className={`w-full flex items-center gap-3 p-2 rounded-lg text-left transition ${
                    activeMarker?.timestamp === marker.timestamp
                      ? 'bg-green-600/30 text-white'
                      : 'hover:bg-white/5 text-gray-300'
                  }`}
                >
                  <span className="font-mono text-sm text-yellow-400 min-w-[60px]">
                    {marker.timestamp}
                  </span>
                  <span className="text-sm">
                    Officer #{marker.officer_id}
                    {marker.badge && ` (${marker.badge})`}
                  </span>
                  {marker.action && (
                    <span className="text-xs text-gray-500 truncate flex-1">
                      {marker.action}
                    </span>
                  )}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

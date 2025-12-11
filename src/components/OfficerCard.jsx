import { useState } from 'react';
import { Card } from '@/components/ui/card';
import { User } from 'lucide-react';

// Get country flag for police force
const getCountryFlag = () => {
  // All UK police forces use the Union Jack
  return '🇬🇧';
};

// Format shoulder/warrant number - replace unknown characters with X
const formatBadgeNumber = (badgeNumber) => {
  if (!badgeNumber) return 'XXXXXX';

  // If it's marked as unknown or partial, format appropriately
  const badge = badgeNumber.toString().toUpperCase();

  // If badge contains question marks or is marked unknown, replace with X
  if (badge.includes('?') || badge.toLowerCase().includes('unknown')) {
    return badge.replace(/\?/g, 'X').replace(/unknown/gi, 'XXXXXX');
  }

  return badge;
};

// Format force name for display (uppercase, abbreviated if needed)
const formatForceName = (force) => {
  if (!force) return 'UNKNOWN FORCE';

  const forceUpper = force.toUpperCase();

  // Common abbreviations for long names
  const abbreviations = {
    'METROPOLITAN POLICE SERVICE': 'METROPOLITAN POLICE',
    'POLICE SERVICE OF NORTHERN IRELAND': 'PSNI',
    'BRITISH TRANSPORT POLICE': 'BTP',
  };

  return abbreviations[forceUpper] || forceUpper;
};

const OfficerCard = ({ officer, onClick }) => {
  const [imageLoaded, setImageLoaded] = useState(false);
  const [imageError, setImageError] = useState(false);

  const handleImageLoad = () => {
    setImageLoaded(true);
  };

  const handleImageError = () => {
    setImageError(true);
    setImageLoaded(true);
  };

  const countryFlag = getCountryFlag(officer.force);
  const badgeNumber = formatBadgeNumber(officer.badgeNumber);
  const forceName = formatForceName(officer.force);

  return (
    <Card
      className="group cursor-pointer overflow-hidden rounded-lg border-2 border-slate-300 bg-slate-900 shadow-md transition-all duration-200 hover:shadow-xl hover:border-slate-400"
      onClick={() => onClick(officer)}
    >
      {/* Image container with overlays */}
      <div className="relative aspect-square overflow-hidden bg-slate-800">
        {/* Loading state */}
        {!imageLoaded && !imageError && (
          <div className="absolute inset-0 bg-slate-800 animate-pulse" />
        )}

        {/* Error/No image state */}
        {imageError ? (
          <div className="absolute inset-0 bg-slate-800 flex items-center justify-center">
            <div className="text-slate-500 text-center">
              <User className="h-16 w-16 mx-auto mb-2" />
              <div className="text-xs font-mono">NO IMAGE</div>
            </div>
          </div>
        ) : (
          <img
            src={officer.photo}
            alt={`Officer ${officer.badgeNumber}`}
            className={`h-full w-full object-cover object-center transition-transform duration-300 group-hover:scale-105 ${
              imageLoaded ? 'opacity-100' : 'opacity-0'
            }`}
            onLoad={handleImageLoad}
            onError={handleImageError}
          />
        )}

        {/* Top overlay with badge number and force */}
        <div className="absolute top-0 left-0 right-0 p-2 flex justify-between items-start">
          {/* Top Left - Shoulder/Warrant Number */}
          <div className="bg-black/80 backdrop-blur-sm border border-slate-600 px-2 py-1 rounded">
            <span className="text-white font-bold font-mono text-sm tracking-wider">
              {badgeNumber}
            </span>
          </div>

          {/* Top Right - Police Force */}
          <div className="bg-black/80 backdrop-blur-sm border border-slate-600 px-2 py-1 rounded max-w-[60%]">
            <span className="text-white font-bold font-mono text-xs tracking-wide truncate block">
              {forceName}
            </span>
          </div>
        </div>

        {/* Bottom overlay with STATE AGENT */}
        <div className="absolute bottom-0 left-0 right-0 p-2">
          <div className="bg-red-700/90 backdrop-blur-sm border border-red-500 px-2 py-1 rounded inline-flex items-center gap-1.5">
            <span className="text-base">{countryFlag}</span>
            <span className="text-white font-bold font-mono text-xs tracking-widest">
              STATE AGENT
            </span>
          </div>
        </div>
      </div>

      {/* Card footer with metadata */}
      <div className="p-2 bg-slate-900 border-t border-slate-700">
        <div className="flex items-center justify-between">
          {officer.role && (
            <span className="text-xs font-mono text-slate-400 uppercase tracking-wide truncate">
              {officer.role}
            </span>
          )}
          {officer.sources && officer.sources.length > 0 && (
            <span className="text-xs font-mono text-slate-500">
              {officer.sources.length} source{officer.sources.length !== 1 ? 's' : ''}
            </span>
          )}
        </div>
      </div>
    </Card>
  );
};

export default OfficerCard;

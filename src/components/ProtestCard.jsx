import PropTypes from 'prop-types';
import { Calendar, MapPin, Users, Camera, Shield, ChevronRight } from 'lucide-react';
import { Card } from '@/components/ui/card';

// Event type configuration for visual styling
const EVENT_TYPE_CONFIG = {
  march: {
    color: 'bg-blue-500',
    lightBg: 'bg-blue-50',
    textColor: 'text-blue-700',
    borderColor: 'border-blue-200',
    label: 'March',
  },
  rally: {
    color: 'bg-green-500',
    lightBg: 'bg-green-50',
    textColor: 'text-green-700',
    borderColor: 'border-green-200',
    label: 'Rally',
  },
  vigil: {
    color: 'bg-purple-500',
    lightBg: 'bg-purple-50',
    textColor: 'text-purple-700',
    borderColor: 'border-purple-200',
    label: 'Vigil',
  },
  encampment: {
    color: 'bg-orange-500',
    lightBg: 'bg-orange-50',
    textColor: 'text-orange-700',
    borderColor: 'border-orange-200',
    label: 'Encampment',
  },
  demonstration: {
    color: 'bg-red-500',
    lightBg: 'bg-red-50',
    textColor: 'text-red-700',
    borderColor: 'border-red-200',
    label: 'Demonstration',
  },
  default: {
    color: 'bg-slate-500',
    lightBg: 'bg-slate-50',
    textColor: 'text-slate-700',
    borderColor: 'border-slate-200',
    label: 'Event',
  },
};

/**
 * Format date for display.
 * @param {string} dateString - ISO date string
 * @returns {string} Formatted date
 */
const formatDate = (dateString) => {
  if (!dateString) return 'Date unknown';
  try {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-GB', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
    });
  } catch {
    return 'Date unknown';
  }
};

/**
 * Format attendance number for display.
 * @param {number|null} attendance - Estimated attendance
 * @returns {string} Formatted attendance
 */
const formatAttendance = (attendance) => {
  if (!attendance) return null;
  if (attendance >= 1000000) {
    return `${(attendance / 1000000).toFixed(1)}M`;
  }
  if (attendance >= 1000) {
    return `${(attendance / 1000).toFixed(0)}K`;
  }
  return attendance.toString();
};

const ProtestCard = ({ protest, onClick }) => {
  const eventType = protest.event_type?.toLowerCase() || 'default';
  const config = EVENT_TYPE_CONFIG[eventType] || EVENT_TYPE_CONFIG.default;
  const formattedAttendance = formatAttendance(protest.estimated_attendance);

  return (
    <Card
      className={`group cursor-pointer overflow-hidden rounded-lg border ${config.borderColor} bg-white shadow-sm transition-all duration-200 hover:shadow-lg hover:border-slate-300`}
      onClick={() => onClick(protest)}
    >
      {/* Cover Image or Placeholder */}
      <div className="relative h-40 bg-gradient-to-br from-slate-100 to-slate-200 overflow-hidden">
        {protest.cover_image_url ? (
          <img
            src={protest.cover_image_url}
            alt={protest.name}
            loading="lazy"
            className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-105"
          />
        ) : (
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="text-slate-300">
              <Shield className="h-16 w-16" />
            </div>
          </div>
        )}

        {/* Event Type Badge */}
        <div className="absolute top-3 left-3">
          <span className={`${config.color} text-white text-xs font-semibold px-2.5 py-1 rounded-full`}>
            {config.label}
          </span>
        </div>

        {/* Status Badge */}
        {protest.status === 'verified' && (
          <div className="absolute top-3 right-3">
            <span className="bg-green-500 text-white text-xs font-semibold px-2 py-1 rounded-full">
              Verified
            </span>
          </div>
        )}

        {/* Date Overlay */}
        <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/70 to-transparent p-3">
          <div className="flex items-center gap-1.5 text-white text-sm">
            <Calendar className="h-4 w-4" />
            <span>{formatDate(protest.date)}</span>
          </div>
        </div>
      </div>

      {/* Card Content */}
      <div className="p-4">
        {/* Title */}
        <h3 className="font-semibold text-slate-900 text-lg line-clamp-2 mb-2 group-hover:text-slate-700">
          {protest.name}
        </h3>

        {/* Location */}
        <div className="flex items-center gap-1.5 text-slate-600 text-sm mb-3">
          <MapPin className="h-4 w-4 flex-shrink-0" />
          <span className="truncate">
            {protest.city || protest.location}
            {protest.country && protest.country !== 'United Kingdom' && `, ${protest.country}`}
          </span>
        </div>

        {/* Stats Row */}
        <div className="flex items-center gap-4 text-sm">
          {formattedAttendance && (
            <div className="flex items-center gap-1 text-slate-500">
              <Users className="h-4 w-4" />
              <span>{formattedAttendance}</span>
            </div>
          )}
          {protest.media_count > 0 && (
            <div className="flex items-center gap-1 text-slate-500">
              <Camera className="h-4 w-4" />
              <span>{protest.media_count}</span>
            </div>
          )}
          {protest.officer_count > 0 && (
            <div className="flex items-center gap-1 text-slate-500">
              <Shield className="h-4 w-4" />
              <span>{protest.officer_count}</span>
            </div>
          )}
        </div>

        {/* Police Force */}
        {protest.police_force && (
          <div className="mt-3 pt-3 border-t border-slate-100">
            <span className="text-xs text-slate-500">
              Policed by: <span className="font-medium text-slate-700">{protest.police_force}</span>
            </span>
          </div>
        )}
      </div>

      {/* View Details Footer */}
      <div className="px-4 py-3 bg-slate-50 border-t border-slate-100 flex items-center justify-between">
        <span className="text-sm font-medium text-slate-600">View Details</span>
        <ChevronRight className="h-4 w-4 text-slate-400 group-hover:translate-x-1 transition-transform" />
      </div>
    </Card>
  );
};

ProtestCard.propTypes = {
  protest: PropTypes.shape({
    id: PropTypes.number.isRequired,
    name: PropTypes.string.isRequired,
    date: PropTypes.string,
    location: PropTypes.string,
    city: PropTypes.string,
    country: PropTypes.string,
    event_type: PropTypes.string,
    status: PropTypes.string,
    cover_image_url: PropTypes.string,
    estimated_attendance: PropTypes.number,
    police_force: PropTypes.string,
    media_count: PropTypes.number,
    officer_count: PropTypes.number,
  }).isRequired,
  onClick: PropTypes.func.isRequired,
};

export default ProtestCard;

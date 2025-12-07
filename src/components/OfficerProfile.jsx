import { X, ExternalLink, Calendar, MapPin, Shield, FileText } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';

const OfficerProfile = ({ officer, onClose }) => {
  if (!officer) return null;

  const getSourceIcon = (type) => {
    switch (type) {
      case 'video':
        return '🎥';
      case 'photo':
        return '📷';
      case 'tweet':
        return '🐦';
      case 'article':
        return '📰';
      default:
        return '🔗';
    }
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
      <div className="relative w-full max-w-4xl max-h-[90vh] overflow-y-auto bg-white rounded-xl shadow-2xl">
        {/* Close button */}
        <Button
          variant="ghost"
          size="icon"
          className="absolute top-4 right-4 z-10 bg-white/80 hover:bg-white"
          onClick={onClose}
        >
          <X className="h-5 w-5" />
        </Button>

        {/* Header with image and basic info */}
        <div className="relative">
          <div className="h-64 md:h-80 overflow-hidden rounded-t-xl">
            <img
              src={officer.photo}
              alt={`Officer ${officer.badgeNumber}`}
              className="w-full h-full object-cover"
            />
            <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent" />
          </div>

          <div className="absolute bottom-6 left-6 text-white">
            <div className="flex items-center gap-2 mb-2">
              <Shield className="h-5 w-5" />
              <span className="text-sm font-medium opacity-90">BADGE NUMBER</span>
            </div>
            <div className="text-4xl font-bold mb-2">{officer.badgeNumber}</div>
            <div className="text-lg opacity-90">{officer.role}</div>
          </div>
        </div>

        {/* Content */}
        <div className="p-6 md:p-8">
          {/* Event details */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
            <Card className="p-4">
              <div className="flex items-center gap-3 mb-2">
                <Calendar className="h-5 w-5 text-blue-600" />
                <span className="font-medium text-gray-900">Date</span>
              </div>
              <p className="text-gray-600">{formatDate(officer.protestDate)}</p>
            </Card>

            <Card className="p-4">
              <div className="flex items-center gap-3 mb-2">
                <MapPin className="h-5 w-5 text-blue-600" />
                <span className="font-medium text-gray-900">Location</span>
              </div>
              <p className="text-gray-600">{officer.location}</p>
            </Card>
          </div>

          {/* Notes section */}
          <div className="mb-8">
            <div className="flex items-center gap-3 mb-4">
              <FileText className="h-5 w-5 text-blue-600" />
              <h3 className="text-xl font-semibold text-gray-900">Documented Actions</h3>
            </div>
            <Card className="p-6">
              <p className="text-gray-700 leading-relaxed">{officer.notes}</p>
            </Card>
          </div>

          {/* Sources section */}
          <div>
            <div className="flex items-center gap-3 mb-4">
              <ExternalLink className="h-5 w-5 text-blue-600" />
              <h3 className="text-xl font-semibold text-gray-900">
                Source Materials ({officer.sources.length})
              </h3>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {officer.sources.map((source, index) => (
                <Card key={index} className="p-4 hover:shadow-md transition-shadow">
                  <div className="flex items-start gap-3">
                    <span className="text-2xl">{getSourceIcon(source.type)}</span>
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-2">
                        <span className="text-sm font-medium text-blue-600 uppercase tracking-wide">
                          {source.type}
                        </span>
                      </div>
                      <p className="text-sm text-gray-700 mb-3">{source.description}</p>
                      <a
                        href={source.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 text-sm text-blue-600 hover:text-blue-800 font-medium"
                      >
                        View Source
                        <ExternalLink className="h-3 w-3" />
                      </a>
                    </div>
                  </div>
                </Card>
              ))}
            </div>
          </div>

        </div>

        {/* Coordinates if available */}
        {(officer.latitude && officer.longitude) && (
          <div className="mt-2 text-xs text-gray-400 font-mono">
            {officer.latitude}, {officer.longitude}
          </div>
        )}

        {/* Appeal for Information */}
        <div className="mt-8 bg-red-50 border-2 border-red-200 rounded-lg p-6">
          <div className="flex items-center gap-3 mb-4">
            <Megaphone className="h-6 w-6 text-red-600" />
            <h3 className="text-xl font-bold text-red-900">Appeal for Information</h3>
          </div>
          <p className="text-gray-700 mb-4">
            We are building a case against this officer for their actions. If you have any additional footage,
            photos, or information about this individual or this event, please contact us securely.
          </p>
          <div className="flex gap-4">
            <Button className="bg-red-600 hover:bg-red-700 text-white">
              Submit Evidence
            </Button>
            <Button variant="outline" className="text-red-600 border-red-600 hover:bg-red-50">
              Contact Legal Team
            </Button>
          </div>
        </div>

        {/* Footer note */}
        <div className="mt-8 p-4 bg-gray-50 rounded-lg">
          <p className="text-sm text-gray-600 text-center">
            This documentation is part of our commitment to transparency and accountability.
            All information is sourced from publicly available materials.
          </p>
        </div>
      </div>
    </div>
    </div >
  );
};

export default OfficerProfile;


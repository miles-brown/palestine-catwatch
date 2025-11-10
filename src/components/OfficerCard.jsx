import { useState } from 'react';
import { Card } from '@/components/ui/card';

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

  return (
    <Card 
      className="group cursor-pointer overflow-hidden rounded-lg border-2 border-green-200 bg-white shadow-md transition-all duration-300 hover:border-red-400 hover:shadow-xl hover:scale-105"
      onClick={() => onClick(officer)}
    >
      <div className="relative aspect-square overflow-hidden">
        {!imageLoaded && !imageError && (
          <div className="absolute inset-0 bg-gray-200 animate-pulse" />
        )}
        
        {imageError ? (
          <div className="absolute inset-0 bg-gray-300 flex items-center justify-center">
            <div className="text-gray-500 text-center">
              <div className="text-4xl mb-2">👤</div>
              <div className="text-sm">Image unavailable</div>
            </div>
          </div>
        ) : (
          <img
            src={officer.photo}
            alt={`Officer ${officer.badgeNumber}`}
            className={`h-full w-full object-cover transition-transform duration-300 group-hover:scale-110 ${
              imageLoaded ? 'opacity-100' : 'opacity-0'
            }`}
            onLoad={handleImageLoad}
            onError={handleImageError}
          />
        )}
        
        {/* Palestine flag stripe overlay */}
        <div className="absolute top-0 left-0 right-0 palestine-flag-stripe"></div>
        
        {/* Badge number overlay */}
        <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/90 to-transparent p-4">
          <div className="text-white">
            <div className="text-xs font-medium opacity-90 text-red-300">STATE AGENT</div>
            <div className="text-2xl font-bold">{officer.badgeNumber}</div>
            <div className="text-xs text-green-300 mt-1">🇵🇸 DOCUMENTED</div>
          </div>
        </div>
        
        {/* Hover overlay */}
        <div className="absolute inset-0 bg-red-900/0 group-hover:bg-red-900/20 transition-colors duration-300" />
      </div>
      
      {/* Card footer with basic info */}
      <div className="p-4 bg-gradient-to-r from-green-50 to-red-50">
        <div className="text-sm text-gray-600 mb-1 font-medium">{officer.protestDate}</div>
        <div className="text-sm font-medium text-gray-900 mb-2 line-clamp-2">{officer.location}</div>
        <div className="flex items-center justify-between">
          <div className="text-xs text-red-700 font-bold uppercase tracking-wide bg-red-100 px-2 py-1 rounded">
            {officer.role}
          </div>
          <div className="text-xs text-green-700 font-bold">
            🇵🇸 SOLIDARITY
          </div>
        </div>
      </div>
    </Card>
  );
};

export default OfficerCard;


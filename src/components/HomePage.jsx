import { useState, useEffect } from 'react';
import OfficerCard from './OfficerCard';
import OfficerProfile from './OfficerProfile';
// import { officers } from '../data/officers'; // Deprecated
import { Heart, Camera, Megaphone, AlertTriangle, Users, Eye } from 'lucide-react';
import { Card } from '@/components/ui/card';

const API_BASE = "http://localhost:8000";

const HomePage = () => {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedOfficer, setSelectedOfficer] = useState(null);
  const [officers, setOfficers] = useState([]);

  useEffect(() => {
    const fetchOfficers = async () => {
      try {
        const response = await fetch(`${API_BASE}/officers`);
        const data = await response.json();

        const mappedOfficers = data.map(off => {
          const mainAppearance = off.appearances?.[0];
          const media = mainAppearance?.media;
          const cropPath = mainAppearance?.image_crop_path;

          // Format photo URL
          // Backend stores: ../data/frames/2/frame_0000.jpg using relative paths from backend dir
          // API serves /data -> mapped to ../data
          // So we need to strip ../data/ and append to API_BASE/data/
          let photoUrl = "https://via.placeholder.com/400?text=No+Image";
          if (cropPath) {
            const relativePath = cropPath.replace('../data/', '').replace(/^\/+/, '');
            photoUrl = `${API_BASE}/data/${relativePath}`;
          }

          return {
            id: off.id,
            badgeNumber: off.badge_number || 'Unknown',
            role: mainAppearance?.role || off.force || 'Officer',
            force: off.force || 'Unknown Force',
            location: 'London',
            protestDate: media?.timestamp || new Date().toISOString(),
            photo: photoUrl,
            status: 'Identified',
            notes: off.notes || 'No notes available.',
            sources: off.appearances.map(app => ({
              type: app.media?.type || 'photo',
              description: app.action || 'Evidence',
              url: app.media?.url ? `${API_BASE}/data/${app.media.url.replace('../data/', '').replace(/^\/+/, '')}` : '#'
            }))
          };
        });
        setOfficers(mappedOfficers);
      } catch (error) {
        console.error("Failed to fetch officers:", error);
      }
    };

    fetchOfficers();
  }, []);

  const handleOfficerClick = (officer) => {
    setSelectedOfficer(officer);
  };

  const handleCloseProfile = () => {
    setSelectedOfficer(null);
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Memorial Section */}
      <div className="journalist-memorial">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="text-center">
            <div className="flex items-center justify-center gap-2 mb-4">
              <Heart className="h-6 w-6 text-red-500" />
              <span className="memorial-text text-2xl font-bold">In Memory</span>
              <Heart className="h-6 w-6 text-red-500" />
            </div>
            <p className="text-white text-lg mb-4">
              Dedicated to the journalists, civilians, and freedom fighters who have died in Palestine
            </p>
            <div className="flex flex-wrap justify-center gap-4 text-sm">
              <span className="press-badge">PRESS</span>
              <span className="text-white">🇵🇸 Over 140 journalists killed since October 2023</span>
              <span className="press-badge">PRESS</span>
            </div>
            <p className="text-red-300 text-sm mt-4 italic">
              "The pen is mightier than the sword, but they kill us for both"
            </p>
          </div>
        </div>
      </div>

      {/* Hero Section */}
      <div className="bg-white border-b-2 border-green-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
          <div className="text-center">
            <h1 className="text-4xl md:text-6xl font-bold text-gray-900 mb-6">
              Palestine
              <span className="block memorial-text">Accountability</span>
            </h1>
            <p className="text-xl text-gray-600 max-w-3xl mx-auto mb-8">
              Documenting state oppression during Palestine solidarity demonstrations.
              Exposing the erosion of democratic rights and the rise of authoritarian policing
              in Britain's descent toward fascist control.
            </p>
            <div className="flex flex-wrap justify-center gap-4 text-sm text-gray-700">
              <span className="px-3 py-1 bg-red-100 border border-red-300 rounded-full font-semibold">🇵🇸 Free Palestine</span>
              <span className="px-3 py-1 bg-green-100 border border-green-300 rounded-full font-semibold">Press Freedom</span>
              <span className="px-3 py-1 bg-gray-100 border border-gray-300 rounded-full font-semibold">Anti-Fascist</span>
              <span className="px-3 py-1 bg-red-100 border border-red-300 rounded-full font-semibold">Democratic Rights</span>
            </div>
          </div>
        </div>
      </div>

      {/* Dystopian Warning Section */}
      <div className="orwell-quote mx-4 my-8 p-6 rounded-lg">
        <div className="max-w-4xl mx-auto text-center">
          <AlertTriangle className="h-8 w-8 mx-auto mb-4 text-red-500" />
          <blockquote className="text-lg mb-4">
            "Every record has been destroyed or falsified, every book rewritten, every picture repainted,
            every statue and street building renamed, every date altered. And the process is continuing
            day by day and minute by minute. History has stopped."
          </blockquote>
          <cite className="text-sm opacity-75">— George Orwell, 1984</cite>
          <p className="text-sm mt-4 text-yellow-400">
            ⚠️ Britain 2024: Peaceful protesters criminalized, journalists arrested, truth suppressed ⚠️
          </p>
        </div>
      </div>

      {/* Officers Grid Section */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <div className="text-center mb-12">
          <h2 className="text-3xl font-bold text-gray-900 mb-4">
            State Oppression Documentation
          </h2>
          <p className="text-lg text-gray-600 max-w-2xl mx-auto">
            Evidence of authoritarian policing tactics used against Palestine solidarity protesters.
            Each profile documents the systematic suppression of democratic rights and free speech.
          </p>
          <div className="mt-6 p-4 bg-yellow-50 border-l-4 border-yellow-400 rounded-r-lg max-w-2xl mx-auto">
            <div className="flex items-center gap-2 mb-2">
              <Eye className="h-5 w-5 text-yellow-600" />
              <span className="font-semibold text-yellow-800">Big Brother is Watching</span>
            </div>
            <p className="text-sm text-yellow-700">
              These officers participated in the suppression of peaceful Palestine solidarity demonstrations.
              Their actions represent the state's authoritarian response to legitimate protest.
            </p>
          </div>
        </div>

        {/* Grid of officer cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
          {officers.map((officer) => (
            <OfficerCard
              key={officer.id}
              officer={officer}
              onClick={handleOfficerClick}
            />
          ))}
        </div>

        {/* Stats section */}
        <div className="mt-16 grid grid-cols-1 md:grid-cols-3 gap-8 text-center">
          <Card className="p-6 border-2 border-green-200">
            <div className="text-3xl font-bold text-green-700 mb-2">
              {officers.length}
            </div>
            <div className="text-gray-600">State Agents Documented</div>
            <div className="text-xs text-gray-500 mt-1">Suppressing Palestine solidarity</div>
          </Card>
          <Card className="p-6 border-2 border-red-200">
            <div className="text-3xl font-bold text-red-700 mb-2">
              {officers.reduce((total, officer) => total + officer.sources.length, 0)}
            </div>
            <div className="text-gray-600">Evidence Sources</div>
            <div className="text-xs text-gray-500 mt-1">Proof of authoritarian tactics</div>
          </Card>
          <Card className="p-6 border-2 border-gray-200">
            <div className="text-3xl font-bold text-gray-700 mb-2">
              {new Set(officers.map(officer => officer.protestDate)).size}
            </div>
            <div className="text-gray-600">Suppressed Demonstrations</div>
            <div className="text-xs text-gray-500 mt-1">Democratic rights violated</div>
          </Card>
        </div>

        {/* Call to Action */}
        <div className="mt-16 bg-gradient-to-r from-red-50 to-green-50 border-2 border-red-200 rounded-lg p-8">
          <div className="text-center">
            <h3 className="text-2xl font-bold text-gray-900 mb-4">
              🇵🇸 Resist Fascism - Defend Democracy 🇵🇸
            </h3>
            <p className="text-lg text-gray-700 mb-6">
              The systematic suppression of Palestine solidarity demonstrates Britain's slide toward authoritarianism.
              When peaceful protest is criminalized, democracy dies. When journalists are silenced, truth perishes.
            </p>
            <div className="flex flex-wrap justify-center gap-4 text-sm">
              <span className="px-4 py-2 bg-red-600 text-white rounded-lg font-semibold">
                Never Again Means Never Again
              </span>
              <span className="px-4 py-2 bg-green-600 text-white rounded-lg font-semibold">
                From the River to the Sea
              </span>
              <span className="px-4 py-2 bg-black text-white rounded-lg font-semibold">
                Press Freedom Now
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Officer Profile Modal */}
      {selectedOfficer && (
        <OfficerProfile
          officer={selectedOfficer}
          onClose={handleCloseProfile}
        />
      )}
    </div>
  );
};

export default HomePage;


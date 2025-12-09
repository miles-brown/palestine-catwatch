import { useState, useEffect } from 'react';
import OfficerCard from './OfficerCard';
import OfficerProfile from './OfficerProfile';
import MapView from './MapView';
import { Heart, Camera, Megaphone, AlertTriangle, Users, Eye, Map, Grid, Filter, X, ChevronDown } from 'lucide-react';
import { Card } from '@/components/ui/card';
import { API_BASE, getMediaUrl, fetchWithErrorHandling } from '../utils/api';

const ITEMS_PER_PAGE = 20;

const HomePage = () => {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedOfficer, setSelectedOfficer] = useState(null);
  const [officers, setOfficers] = useState([]);
  const [viewMode, setViewMode] = useState('grid'); // 'grid' or 'map'
  const [currentPage, setCurrentPage] = useState(1);
  const [totalOfficers, setTotalOfficers] = useState(0);
  const [isLoading, setIsLoading] = useState(true);

  // Advanced filters
  const [showFilters, setShowFilters] = useState(false);
  const [forceFilter, setForceFilter] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [minAppearances, setMinAppearances] = useState(0);
  const [availableForces, setAvailableForces] = useState([]);

  useEffect(() => {
    const fetchOfficers = async () => {
      setIsLoading(true);
      try {
        // Build query params with filters
        const skip = (currentPage - 1) * ITEMS_PER_PAGE;
        const params = new URLSearchParams({
          skip: skip.toString(),
          limit: ITEMS_PER_PAGE.toString()
        });

        if (forceFilter) params.append('force', forceFilter);
        if (dateFrom) params.append('date_from', dateFrom);
        if (dateTo) params.append('date_to', dateTo);

        const response = await fetch(`${API_BASE}/officers?${params}`);
        const data = await response.json();

        const mappedOfficers = data.map(off => {
          const mainAppearance = off.appearances?.[0];
          const media = mainAppearance?.media;
          const cropPath = mainAppearance?.image_crop_path;

          // Format photo URL using secure path sanitization
          const photoUrl = getMediaUrl(cropPath) || "https://via.placeholder.com/400?text=No+Image";

          return {
            id: off.id,
            badgeNumber: off.badge_number || 'Unknown',
            role: mainAppearance?.role || off.force || 'Officer',
            force: off.force || 'Unknown Force',
            location: 'London',
            latitude: off.latitude,
            longitude: off.longitude,
            protestDate: media?.timestamp || new Date().toISOString(),
            photo: photoUrl,
            status: 'Identified',
            notes: off.notes || 'No notes available.',
            sources: off.appearances.map(app => ({
              type: app.media?.type || 'photo',
              description: app.action || 'Evidence',
              url: getMediaUrl(app.media?.url) || '#'
            }))
          };
        });
        setOfficers(mappedOfficers);

        // Extract unique forces for filter dropdown
        const forces = [...new Set(data.map(o => o.force).filter(Boolean))];
        if (forces.length > 0) {
          setAvailableForces(prev => {
            const combined = [...new Set([...prev, ...forces])];
            return combined.sort();
          });
        }
      } catch (error) {
        console.error("Failed to fetch officers:", error);
      } finally {
        setIsLoading(false);
      }
    };

    fetchOfficers();
  }, [currentPage, forceFilter, dateFrom, dateTo]);

  // Fetch total count using dedicated count endpoint
  useEffect(() => {
    const fetchTotalCount = async () => {
      try {
        const response = await fetch(`${API_BASE}/officers/count`);
        const data = await response.json();
        setTotalOfficers(data.count || 0);
      } catch (error) {
        console.error("Failed to fetch total count:", error);
      }
    };
    fetchTotalCount();
  }, []);

  const totalPages = Math.ceil(totalOfficers / ITEMS_PER_PAGE);

  const handlePageChange = (newPage) => {
    if (newPage >= 1 && newPage <= totalPages) {
      setCurrentPage(newPage);
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
  };

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

        {/* Search and Filters */}
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 mb-8">
          <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
            <div className="flex flex-wrap gap-4 items-end">
              {/* Text Search */}
              <div className="flex-1 min-w-[200px]">
                <label className="block text-sm font-medium text-gray-700 mb-1">Search Officials</label>
                <input
                  type="text"
                  placeholder="Search by badge number, notes, or role..."
                  className="w-full p-2 border border-gray-300 rounded-md focus:ring-green-500 focus:border-green-500"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                />
              </div>

              {/* Advanced Filters Toggle */}
              <div>
                <button
                  onClick={() => setShowFilters(!showFilters)}
                  className={`flex items-center gap-2 px-4 py-2 rounded-md border ${
                    showFilters || forceFilter || dateFrom || dateTo
                      ? 'bg-green-50 border-green-300 text-green-700'
                      : 'bg-white border-gray-300 text-gray-700 hover:bg-gray-50'
                  }`}
                >
                  <Filter className="h-4 w-4" />
                  Filters
                  {(forceFilter || dateFrom || dateTo) && (
                    <span className="ml-1 px-1.5 py-0.5 text-xs bg-green-100 text-green-800 rounded-full">
                      {[forceFilter, dateFrom, dateTo].filter(Boolean).length}
                    </span>
                  )}
                  <ChevronDown className={`h-4 w-4 transition-transform ${showFilters ? 'rotate-180' : ''}`} />
                </button>
              </div>

              {/* View Toggle */}
              <div>
                <div className="flex bg-gray-100 p-1 rounded-md border border-gray-200">
                  <button
                    onClick={() => setViewMode('grid')}
                    className={`p-2 rounded flex items-center gap-2 text-sm font-medium ${viewMode === 'grid' ? 'bg-white shadow-sm text-gray-900' : 'text-gray-500 hover:text-gray-900'}`}
                  >
                    <Grid className="h-4 w-4" />
                    Grid
                  </button>
                  <button
                    onClick={() => setViewMode('map')}
                    className={`p-2 rounded flex items-center gap-2 text-sm font-medium ${viewMode === 'map' ? 'bg-white shadow-sm text-gray-900' : 'text-gray-500 hover:text-gray-900'}`}
                  >
                    <Map className="h-4 w-4" />
                    Map
                  </button>
                </div>
              </div>
            </div>

            {/* Advanced Filters Panel */}
            {showFilters && (
              <div className="mt-4 pt-4 border-t border-gray-200">
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                  {/* Force Filter */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Force</label>
                    <select
                      value={forceFilter}
                      onChange={(e) => { setForceFilter(e.target.value); setCurrentPage(1); }}
                      className="w-full p-2 border border-gray-300 rounded-md focus:ring-green-500 focus:border-green-500"
                    >
                      <option value="">All Forces</option>
                      {availableForces.map(force => (
                        <option key={force} value={force}>{force}</option>
                      ))}
                    </select>
                  </div>

                  {/* Date From */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Date From</label>
                    <input
                      type="date"
                      value={dateFrom}
                      onChange={(e) => { setDateFrom(e.target.value); setCurrentPage(1); }}
                      className="w-full p-2 border border-gray-300 rounded-md focus:ring-green-500 focus:border-green-500"
                    />
                  </div>

                  {/* Date To */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Date To</label>
                    <input
                      type="date"
                      value={dateTo}
                      onChange={(e) => { setDateTo(e.target.value); setCurrentPage(1); }}
                      className="w-full p-2 border border-gray-300 rounded-md focus:ring-green-500 focus:border-green-500"
                    />
                  </div>

                  {/* Min Appearances */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Min Appearances</label>
                    <select
                      value={minAppearances}
                      onChange={(e) => { setMinAppearances(parseInt(e.target.value)); setCurrentPage(1); }}
                      className="w-full p-2 border border-gray-300 rounded-md focus:ring-green-500 focus:border-green-500"
                    >
                      <option value={0}>Any</option>
                      <option value={2}>2+</option>
                      <option value={3}>3+</option>
                      <option value={5}>5+</option>
                      <option value={10}>10+</option>
                    </select>
                  </div>
                </div>

                {/* Clear Filters */}
                {(forceFilter || dateFrom || dateTo || minAppearances > 0) && (
                  <div className="mt-4 flex justify-end">
                    <button
                      onClick={() => {
                        setForceFilter('');
                        setDateFrom('');
                        setDateTo('');
                        setMinAppearances(0);
                        setCurrentPage(1);
                      }}
                      className="flex items-center gap-2 px-3 py-1.5 text-sm text-red-600 hover:bg-red-50 rounded-md"
                    >
                      <X className="h-4 w-4" />
                      Clear All Filters
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Content Area */}
        {viewMode === 'map' ? (
          <div className="mb-16">
            <MapView
              officers={officers.filter(o => {
                if (!searchQuery) return true;
                const query = searchQuery.toLowerCase();
                return (
                  (o.badgeNumber && o.badgeNumber.toLowerCase().includes(query)) ||
                  (o.notes && o.notes.toLowerCase().includes(query)) ||
                  (o.role && o.role.toLowerCase().includes(query))
                );
              })}
              onOfficerClick={handleOfficerClick}
            />
          </div>
        ) : (
          <>
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-green-600"></div>
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
              {officers
                .filter(officer => {
                  // Text search filter
                  if (searchQuery) {
                    const query = searchQuery.toLowerCase();
                    const matchesSearch = (
                      (officer.badgeNumber && officer.badgeNumber.toLowerCase().includes(query)) ||
                      (officer.notes && officer.notes.toLowerCase().includes(query)) ||
                      (officer.role && officer.role.toLowerCase().includes(query)) ||
                      (officer.force && officer.force.toLowerCase().includes(query))
                    );
                    if (!matchesSearch) return false;
                  }

                  // Min appearances filter (client-side)
                  if (minAppearances > 0 && officer.sources.length < minAppearances) {
                    return false;
                  }

                  return true;
                })
                .map((officer) => (
                  <OfficerCard
                    key={officer.id}
                    officer={officer}
                    onClick={handleOfficerClick}
                  />
                ))}
            </div>
          )}

          {/* Pagination Controls */}
          {totalPages > 1 && !searchQuery && (
            <div className="flex items-center justify-center gap-2 mt-8">
              <button
                onClick={() => handlePageChange(1)}
                disabled={currentPage === 1}
                className="px-3 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                First
              </button>
              <button
                onClick={() => handlePageChange(currentPage - 1)}
                disabled={currentPage === 1}
                className="px-3 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Previous
              </button>

              <span className="px-4 py-2 text-sm font-medium text-gray-700">
                Page {currentPage} of {totalPages}
              </span>

              <button
                onClick={() => handlePageChange(currentPage + 1)}
                disabled={currentPage === totalPages}
                className="px-3 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Next
              </button>
              <button
                onClick={() => handlePageChange(totalPages)}
                disabled={currentPage === totalPages}
                className="px-3 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Last
              </button>
            </div>
          )}
          </>
        )}

        {/* Stats section */}
        <div className="mt-16 grid grid-cols-1 md:grid-cols-3 gap-8 text-center">
          <Card className="p-6 border-2 border-green-200">
            <div className="text-3xl font-bold text-green-700 mb-2">
              {totalOfficers || officers.length}
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


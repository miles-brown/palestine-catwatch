import { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import OfficerCard from './OfficerCard';
import OfficerProfile from './OfficerProfile';
import MapView from './MapView';
import LazyOfficerGrid, { useInfiniteOfficers } from './LazyOfficerGrid';
import { Shield, Users, FileText, Map, Grid, Filter, X, ChevronDown, LayoutList, Scale, Database, ArrowRight } from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { OfficerGridSkeleton } from '@/components/ui/skeleton';
import { API_BASE, getMediaUrl, fetchWithErrorHandling } from '../utils/api';
import { Link } from 'react-router-dom';

// Configuration constants
const ITEMS_PER_PAGE = 20;
const MAX_SEARCH_LENGTH = 200;
const COUNT_DEBOUNCE_MS = 300;

/**
 * Sanitize search query to prevent XSS and ensure safe string operations
 * - Trims whitespace
 * - Removes HTML tags
 * - Limits length to prevent DoS
 */
const sanitizeSearchQuery = (query) => {
  if (!query || typeof query !== 'string') return '';
  return query
    .trim()
    .replace(/<[^>]*>/g, '') // Remove HTML tags
    .slice(0, MAX_SEARCH_LENGTH);
};

/**
 * Filter officers by search query and minimum appearances
 * @param {Array} officers - List of officers to filter
 * @param {string} query - Sanitized, lowercase search query
 * @param {number} minAppearances - Minimum number of appearances required
 * @returns {Array} Filtered officers
 */
const filterOfficers = (officers, query, minAppearances = 0) => {
  return officers.filter(officer => {
    // Text search filter
    if (query) {
      const matchesSearch = (
        (officer.badgeNumber && officer.badgeNumber.toLowerCase().includes(query)) ||
        (officer.notes && officer.notes.toLowerCase().includes(query)) ||
        (officer.role && officer.role.toLowerCase().includes(query)) ||
        (officer.force && officer.force.toLowerCase().includes(query))
      );
      if (!matchesSearch) return false;
    }

    // Min appearances filter
    if (minAppearances > 0 && officer.sources.length < minAppearances) {
      return false;
    }

    return true;
  });
};

const HomePage = () => {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedOfficer, setSelectedOfficer] = useState(null);
  const [officers, setOfficers] = useState([]);
  const [viewMode, setViewMode] = useState('grid'); // 'grid', 'map', or 'infinite'
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

  // Memoized sanitized search query for filtering
  const sanitizedQuery = useMemo(() => sanitizeSearchQuery(searchQuery).toLowerCase(), [searchQuery]);

  // Handler for search input that sanitizes on change
  const handleSearchChange = useCallback((e) => {
    setSearchQuery(sanitizeSearchQuery(e.target.value));
  }, []);

  // Infinite scroll hook
  const infiniteFilters = { force: forceFilter, dateFrom, dateTo };
  const {
    officers: infiniteOfficers,
    isLoading: infiniteLoading,
    loadingMore,
    hasMore,
    totalCount: infiniteTotalCount,
    loadMore
  } = useInfiniteOfficers(API_BASE, viewMode === 'infinite' ? infiniteFilters : {});

  // AbortController ref for officers fetch to prevent race conditions
  const officersAbortRef = useRef(null);

  useEffect(() => {
    // Abort any in-flight request to prevent race conditions
    if (officersAbortRef.current) {
      officersAbortRef.current.abort();
    }

    const abortController = new AbortController();
    officersAbortRef.current = abortController;

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

        const response = await fetch(`${API_BASE}/officers?${params}`, {
          signal: abortController.signal
        });
        const data = await response.json();

        // Only update state if request wasn't aborted
        if (abortController.signal.aborted) return;

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
        // Ignore abort errors, log others
        if (error.name !== 'AbortError') {
          console.error("Failed to fetch officers:", error);
        }
      } finally {
        if (!abortController.signal.aborted) {
          setIsLoading(false);
        }
      }
    };

    fetchOfficers();

    return () => {
      // Use the ref to abort, not the captured abortController
      // This prevents aborting the wrong request if a new render has already started
      if (officersAbortRef.current) {
        officersAbortRef.current.abort();
      }
    };
  }, [currentPage, forceFilter, dateFrom, dateTo]);

  // Debounce timer ref for count fetch
  const countDebounceRef = useRef(null);
  // AbortController ref to cancel stale requests
  const countAbortRef = useRef(null);

  // Fetch total count using dedicated count endpoint (debounced with race condition handling)
  useEffect(() => {
    // Clear previous debounce timer
    if (countDebounceRef.current) {
      clearTimeout(countDebounceRef.current);
    }
    // Abort any in-flight request to prevent race conditions
    if (countAbortRef.current) {
      countAbortRef.current.abort();
    }

    // Debounce the count fetch to reduce API calls during rapid filter changes
    countDebounceRef.current = setTimeout(async () => {
      // Create new AbortController for this request
      const abortController = new AbortController();
      countAbortRef.current = abortController;

      try {
        // Build query params to match officers fetch filters
        const params = new URLSearchParams();
        if (forceFilter) params.append('force', forceFilter);
        if (dateFrom) params.append('date_from', dateFrom);
        if (dateTo) params.append('date_to', dateTo);

        const queryString = params.toString();
        const url = `${API_BASE}/officers/count${queryString ? '?' + queryString : ''}`;
        const response = await fetch(url, { signal: abortController.signal });
        const data = await response.json();
        // Only update state if this request wasn't aborted
        if (!abortController.signal.aborted) {
          setTotalOfficers(data.count || 0);
        }
      } catch (error) {
        // Ignore abort errors, log others
        if (error.name !== 'AbortError') {
          console.error("Failed to fetch total count:", error);
        }
      }
    }, COUNT_DEBOUNCE_MS);

    return () => {
      if (countDebounceRef.current) {
        clearTimeout(countDebounceRef.current);
      }
      if (countAbortRef.current) {
        countAbortRef.current.abort();
      }
    };
  }, [forceFilter, dateFrom, dateTo]);

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

  // Memoize filtered officers to prevent expensive filtering on every render
  const filteredOfficersForMap = useMemo(
    () => filterOfficers(officers, sanitizedQuery),
    [officers, sanitizedQuery]
  );

  const filteredInfiniteOfficers = useMemo(
    () => filterOfficers(infiniteOfficers, sanitizedQuery, minAppearances),
    [infiniteOfficers, sanitizedQuery, minAppearances]
  );

  const filteredOfficersForGrid = useMemo(
    () => filterOfficers(officers, sanitizedQuery, minAppearances),
    [officers, sanitizedQuery, minAppearances]
  );

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Hero Section */}
      <div className="bg-white border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16 md:py-24">
          <div className="max-w-3xl mx-auto text-center">
            <div className="inline-flex items-center gap-2 px-3 py-1 bg-slate-100 text-slate-600 text-sm font-medium rounded-full mb-6">
              <Scale className="h-4 w-4" />
              Police Accountability Initiative
            </div>
            <h1 className="text-4xl md:text-5xl font-bold text-slate-900 mb-6 tracking-tight">
              Documenting Police Conduct at Public Demonstrations
            </h1>
            <p className="text-lg text-slate-600 mb-8 leading-relaxed">
              An independent research project maintaining a comprehensive database of police officers
              observed at Palestine solidarity protests in the UK. We promote transparency and
              accountability in public order policing.
            </p>
            <div className="flex flex-wrap justify-center gap-3">
              <Link to="/our-story">
                <Button variant="outline" className="text-sm">
                  Learn More
                  <ArrowRight className="h-4 w-4 ml-2" />
                </Button>
              </Link>
              <Link to="/register">
                <Button className="bg-slate-900 hover:bg-slate-800 text-white text-sm">
                  Contribute Evidence
                </Button>
              </Link>
            </div>
          </div>
        </div>
      </div>

      {/* Mission Cards */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <Card className="p-6 bg-white border border-slate-200">
            <div className="w-10 h-10 bg-slate-100 rounded-lg flex items-center justify-center mb-4">
              <Database className="h-5 w-5 text-slate-600" />
            </div>
            <h3 className="font-semibold text-slate-900 mb-2">Evidence Database</h3>
            <p className="text-sm text-slate-600">
              Systematic collection and cataloguing of photographic and video evidence from public demonstrations.
            </p>
          </Card>
          <Card className="p-6 bg-white border border-slate-200">
            <div className="w-10 h-10 bg-slate-100 rounded-lg flex items-center justify-center mb-4">
              <Shield className="h-5 w-5 text-slate-600" />
            </div>
            <h3 className="font-semibold text-slate-900 mb-2">Officer Identification</h3>
            <p className="text-sm text-slate-600">
              AI-assisted identification and tracking of police personnel to ensure accountability for conduct.
            </p>
          </Card>
          <Card className="p-6 bg-white border border-slate-200">
            <div className="w-10 h-10 bg-slate-100 rounded-lg flex items-center justify-center mb-4">
              <FileText className="h-5 w-5 text-slate-600" />
            </div>
            <h3 className="font-semibold text-slate-900 mb-2">Public Record</h3>
            <p className="text-sm text-slate-600">
              Creating a permanent, searchable archive of policing practices at demonstrations for researchers and journalists.
            </p>
          </Card>
        </div>
      </div>

      {/* Officers Database Section */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-8">
          <h2 className="text-2xl font-bold text-slate-900 mb-2">
            Officer Database
          </h2>
          <p className="text-slate-600">
            Browse documented police officers observed at public demonstrations. Use filters to refine your search.
          </p>
        </div>

        {/* Search and Filters */}
        <div className="mb-8">
          <div className="bg-white p-6 rounded-lg border border-slate-200">
            <div className="flex flex-wrap gap-4 items-end">
              {/* Text Search */}
              <div className="flex-1 min-w-[200px]">
                <label className="block text-sm font-medium text-gray-700 mb-1">Search Officials</label>
                <input
                  type="text"
                  placeholder="Search by badge number, notes, or role..."
                  className="w-full p-2 border border-gray-300 rounded-md focus:ring-green-500 focus:border-green-500"
                  value={searchQuery}
                  onChange={handleSearchChange}
                  maxLength={MAX_SEARCH_LENGTH}
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
                    title="Paginated Grid"
                  >
                    <Grid className="h-4 w-4" />
                    <span className="hidden sm:inline">Grid</span>
                  </button>
                  <button
                    onClick={() => setViewMode('infinite')}
                    className={`p-2 rounded flex items-center gap-2 text-sm font-medium ${viewMode === 'infinite' ? 'bg-white shadow-sm text-gray-900' : 'text-gray-500 hover:text-gray-900'}`}
                    title="Infinite Scroll"
                  >
                    <LayoutList className="h-4 w-4" />
                    <span className="hidden sm:inline">Scroll</span>
                  </button>
                  <button
                    onClick={() => setViewMode('map')}
                    className={`p-2 rounded flex items-center gap-2 text-sm font-medium ${viewMode === 'map' ? 'bg-white shadow-sm text-gray-900' : 'text-gray-500 hover:text-gray-900'}`}
                    title="Map View"
                  >
                    <Map className="h-4 w-4" />
                    <span className="hidden sm:inline">Map</span>
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
              officers={filteredOfficersForMap}
              onOfficerClick={handleOfficerClick}
            />
          </div>
        ) : viewMode === 'infinite' ? (
          /* Infinite Scroll View with Intersection Observer */
          <LazyOfficerGrid
            officers={filteredInfiniteOfficers}
            onOfficerClick={handleOfficerClick}
            isLoading={infiniteLoading}
            hasMore={hasMore && !sanitizedQuery}
            onLoadMore={loadMore}
            loadingMore={loadingMore}
          />
        ) : (
          /* Paginated Grid View */
          <>
          {isLoading ? (
            <OfficerGridSkeleton count={8} />
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
              {filteredOfficersForGrid.map((officer) => (
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
        <div className="mt-12 grid grid-cols-1 md:grid-cols-3 gap-6">
          <Card className="p-6 bg-white border border-slate-200">
            <div className="text-3xl font-bold text-slate-900 mb-1">
              {viewMode === 'infinite' ? infiniteTotalCount : (totalOfficers || officers.length)}
            </div>
            <div className="text-sm font-medium text-slate-600">Officers Documented</div>
            <div className="text-xs text-slate-400 mt-1">In our database</div>
          </Card>
          <Card className="p-6 bg-white border border-slate-200">
            <div className="text-3xl font-bold text-slate-900 mb-1">
              {(viewMode === 'infinite' ? infiniteOfficers : officers).reduce((total, officer) => total + officer.sources.length, 0)}
            </div>
            <div className="text-sm font-medium text-slate-600">Evidence Items</div>
            <div className="text-xs text-slate-400 mt-1">Photos and videos collected</div>
          </Card>
          <Card className="p-6 bg-white border border-slate-200">
            <div className="text-3xl font-bold text-slate-900 mb-1">
              {new Set((viewMode === 'infinite' ? infiniteOfficers : officers).map(officer => officer.protestDate)).size}
            </div>
            <div className="text-sm font-medium text-slate-600">Events Covered</div>
            <div className="text-xs text-slate-400 mt-1">Public demonstrations documented</div>
          </Card>
        </div>

        {/* Call to Action */}
        <div className="mt-12 bg-white border border-slate-200 rounded-lg p-8">
          <div className="max-w-2xl mx-auto text-center">
            <h3 className="text-xl font-semibold text-slate-900 mb-3">
              Help Build the Record
            </h3>
            <p className="text-slate-600 mb-6">
              This database relies on contributions from witnesses and attendees at public demonstrations.
              If you have photographic or video evidence, consider contributing to our archive.
            </p>
            <div className="flex flex-wrap justify-center gap-3">
              <Link to="/register">
                <Button className="bg-slate-900 hover:bg-slate-800 text-white">
                  Create Account
                </Button>
              </Link>
              <Link to="/about">
                <Button variant="outline">
                  Learn About Our Methods
                </Button>
              </Link>
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


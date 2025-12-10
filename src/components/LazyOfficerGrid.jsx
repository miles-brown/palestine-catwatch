import { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import OfficerCard from './OfficerCard';
import { OfficerGridSkeleton } from '@/components/ui/skeleton';
import { Loader2 } from 'lucide-react';

/**
 * LazyOfficerGrid - An officer grid with intersection observer for lazy loading
 *
 * Features:
 * - Infinite scroll with intersection observer
 * - Only renders visible cards + buffer
 * - Smooth loading states
 * - Memory efficient for large datasets
 */

// Maximum number of items to keep in the visible set to prevent memory leaks
const MAX_VISIBLE_ITEMS = 100;
// Time in ms to wait before removing an item from visible set after it leaves viewport
const VISIBILITY_CLEANUP_DELAY = 5000;
// Maximum length for filter string values
const MAX_FILTER_LENGTH = 100;

/**
 * Validate and sanitize a date string for API requests
 * @param {string} dateStr - Date string to validate
 * @returns {string|null} - Validated date string or null if invalid
 */
const validateDateFilter = (dateStr) => {
  if (!dateStr || typeof dateStr !== 'string') return null;
  // Basic ISO date format validation (YYYY-MM-DD)
  const dateRegex = /^\d{4}-\d{2}-\d{2}$/;
  if (!dateRegex.test(dateStr)) return null;
  // Verify it's a valid date
  const date = new Date(dateStr);
  if (isNaN(date.getTime())) return null;
  return dateStr;
};

/**
 * Validate and sanitize a string filter value
 * @param {string} str - String to validate
 * @returns {string|null} - Sanitized string or null if invalid
 */
const validateStringFilter = (str) => {
  if (!str || typeof str !== 'string') return null;
  // Trim and limit length
  const sanitized = str.trim().slice(0, MAX_FILTER_LENGTH);
  // Remove any potentially dangerous characters
  return sanitized.replace(/[<>]/g, '') || null;
};

export default function LazyOfficerGrid({
  officers,
  onOfficerClick,
  isLoading = false,
  hasMore = false,
  onLoadMore = null,
  loadingMore = false
}) {
  const [visibleItems, setVisibleItems] = useState(new Set());
  const observerRef = useRef(null);
  const loadMoreRef = useRef(null);
  const itemRefs = useRef({});
  const cleanupTimersRef = useRef({});

  // Set up intersection observer for individual cards
  useEffect(() => {
    // Disconnect existing observer before creating a new one to prevent duplicate observations
    if (observerRef.current) {
      observerRef.current.disconnect();
    }

    const options = {
      root: null, // viewport
      rootMargin: '100px', // pre-load 100px before visible
      threshold: 0
    };

    observerRef.current = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        const id = entry.target.dataset.officerId;
        if (id) {
          if (entry.isIntersecting) {
            // Clear any pending cleanup timer for this item
            if (cleanupTimersRef.current[id]) {
              clearTimeout(cleanupTimersRef.current[id]);
              delete cleanupTimersRef.current[id];
            }

            setVisibleItems(prev => {
              const next = new Set(prev);
              next.add(id);

              // If we exceed the max, remove oldest items (FIFO behavior via Set iteration order)
              if (next.size > MAX_VISIBLE_ITEMS) {
                const iterator = next.values();
                // Remove the oldest items until we're under the limit
                while (next.size > MAX_VISIBLE_ITEMS) {
                  const oldest = iterator.next().value;
                  // Don't remove items that are currently intersecting
                  if (oldest !== id) {
                    next.delete(oldest);
                  }
                }
              }

              return next;
            });
          } else {
            // Item left viewport - schedule cleanup after delay for smoother scrolling
            cleanupTimersRef.current[id] = setTimeout(() => {
              setVisibleItems(prev => {
                const next = new Set(prev);
                next.delete(id);
                return next;
              });
              delete cleanupTimersRef.current[id];
            }, VISIBILITY_CLEANUP_DELAY);
          }
        }
      });
    }, options);

    // Observe all officer items
    Object.values(itemRefs.current).forEach(ref => {
      if (ref) {
        observerRef.current.observe(ref);
      }
    });

    return () => {
      if (observerRef.current) {
        observerRef.current.disconnect();
      }
      // Clean up all pending timers
      Object.values(cleanupTimersRef.current).forEach(timer => clearTimeout(timer));
      cleanupTimersRef.current = {};
    };
  }, [officers.length]);

  // Set up intersection observer for infinite scroll
  useEffect(() => {
    if (!onLoadMore || !hasMore) return;

    const loadMoreOptions = {
      root: null,
      rootMargin: '200px', // trigger load 200px before reaching bottom
      threshold: 0
    };

    const loadMoreObserver = new IntersectionObserver((entries) => {
      const [entry] = entries;
      if (entry.isIntersecting && hasMore && !loadingMore) {
        onLoadMore();
      }
    }, loadMoreOptions);

    if (loadMoreRef.current) {
      loadMoreObserver.observe(loadMoreRef.current);
    }

    return () => {
      loadMoreObserver.disconnect();
    };
  }, [hasMore, loadingMore, onLoadMore]);

  // Register refs for new items
  const setItemRef = useCallback((id, el) => {
    if (el) {
      itemRefs.current[id] = el;
      if (observerRef.current) {
        observerRef.current.observe(el);
      }
    }
  }, []);

  if (isLoading && officers.length === 0) {
    return <OfficerGridSkeleton count={8} />;
  }

  if (officers.length === 0) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-500">No officers found matching your criteria.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
        {officers.map((officer) => (
          <div
            key={officer.id}
            ref={(el) => setItemRef(officer.id.toString(), el)}
            data-officer-id={officer.id}
            className="min-h-[300px]" // Placeholder height for layout stability
          >
            <LazyOfficerCard
              officer={officer}
              onClick={onOfficerClick}
              isVisible={visibleItems.has(officer.id.toString())}
            />
          </div>
        ))}
      </div>

      {/* Infinite scroll trigger */}
      {hasMore && (
        <div
          ref={loadMoreRef}
          className="flex justify-center py-8"
        >
          {loadingMore ? (
            <div className="flex items-center gap-2 text-gray-500">
              <Loader2 className="h-5 w-5 animate-spin" />
              <span>Loading more officers...</span>
            </div>
          ) : (
            <div className="h-10" /> // Invisible trigger area
          )}
        </div>
      )}
    </div>
  );
}

/**
 * LazyOfficerCard - Only renders full content when visible
 */
function LazyOfficerCard({ officer, onClick, isVisible }) {
  const [hasBeenVisible, setHasBeenVisible] = useState(false);

  useEffect(() => {
    if (isVisible && !hasBeenVisible) {
      setHasBeenVisible(true);
    }
  }, [isVisible, hasBeenVisible]);

  // Once visible, always render (for scroll back up)
  if (!hasBeenVisible) {
    return (
      <div className="bg-gray-100 rounded-lg animate-pulse aspect-square">
        <div className="h-full w-full flex items-center justify-center">
          <div className="text-gray-400 text-4xl">👤</div>
        </div>
      </div>
    );
  }

  return <OfficerCard officer={officer} onClick={onClick} />;
}

/**
 * useInfiniteOfficers - Hook for managing infinite scroll state
 */
export function useInfiniteOfficers(apiBase, filters = {}) {
  const [officers, setOfficers] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [hasMore, setHasMore] = useState(true);
  const [page, setPage] = useState(1);
  const [totalCount, setTotalCount] = useState(0);
  const [error, setError] = useState(null);
  const [retryCount, setRetryCount] = useState(0);
  const ITEMS_PER_PAGE = 20;

  // Extract filter values for stable dependencies
  const { force, dateFrom, dateTo } = filters;

  // Reset when filters change
  useEffect(() => {
    setOfficers([]);
    setPage(1);
    setHasMore(true);
    setIsLoading(true);
    setError(null);
  }, [force, dateFrom, dateTo]);

  // Fetch officers
  useEffect(() => {
    const fetchOfficers = async () => {
      const isFirstPage = page === 1;
      if (isFirstPage) {
        setIsLoading(true);
      } else {
        setLoadingMore(true);
      }

      try {
        const skip = (page - 1) * ITEMS_PER_PAGE;
        const params = new URLSearchParams({
          skip: skip.toString(),
          limit: ITEMS_PER_PAGE.toString()
        });

        // Validate and sanitize filter values before sending to API
        const validatedForce = validateStringFilter(force);
        const validatedDateFrom = validateDateFilter(dateFrom);
        const validatedDateTo = validateDateFilter(dateTo);

        if (validatedForce) params.append('force', validatedForce);
        if (validatedDateFrom) params.append('date_from', validatedDateFrom);
        if (validatedDateTo) params.append('date_to', validatedDateTo);

        const response = await fetch(`${apiBase}/officers?${params}`);
        const data = await response.json();

        const mappedOfficers = data.map(off => {
          const mainAppearance = off.appearances?.[0];
          const media = mainAppearance?.media;
          const cropPath = mainAppearance?.image_crop_path;

          let photoUrl = "https://via.placeholder.com/400?text=No+Image";
          if (cropPath) {
            const relativePath = cropPath.replace('../data/', '').replace(/^\/+/, '');
            photoUrl = `${apiBase}/data/${relativePath}`;
          }

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
              url: app.media?.url ? `${apiBase}/data/${app.media.url.replace('../data/', '').replace(/^\/+/, '')}` : '#'
            }))
          };
        });

        if (isFirstPage) {
          setOfficers(mappedOfficers);
        } else {
          setOfficers(prev => [...prev, ...mappedOfficers]);
        }

        setHasMore(data.length === ITEMS_PER_PAGE);
        setError(null);
      } catch (err) {
        console.error("Failed to fetch officers:", err);
        setError(err.message || 'Failed to load officers. Please try again.');
      } finally {
        setIsLoading(false);
        setLoadingMore(false);
      }
    };

    fetchOfficers();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, apiBase, force, dateFrom, dateTo, retryCount]);

  // Fetch total count
  useEffect(() => {
    const fetchCount = async () => {
      try {
        const params = new URLSearchParams();
        // Use same validation as officers fetch
        const validatedForce = validateStringFilter(force);
        const validatedDateFrom = validateDateFilter(dateFrom);
        const validatedDateTo = validateDateFilter(dateTo);

        if (validatedForce) params.append('force', validatedForce);
        if (validatedDateFrom) params.append('date_from', validatedDateFrom);
        if (validatedDateTo) params.append('date_to', validatedDateTo);

        const queryString = params.toString();
        const url = `${apiBase}/officers/count${queryString ? '?' + queryString : ''}`;
        const response = await fetch(url);
        const data = await response.json();
        setTotalCount(data.count || 0);
      } catch (error) {
        console.error("Failed to fetch count:", error);
      }
    };
    fetchCount();
  }, [apiBase, force, dateFrom, dateTo]);

  const loadMore = useCallback(() => {
    if (!loadingMore && hasMore) {
      setPage(p => p + 1);
    }
  }, [loadingMore, hasMore]);

  // Retry function to attempt fetching again after an error
  const retry = useCallback(() => {
    setError(null);
    setRetryCount(c => c + 1);
  }, []);

  return {
    officers,
    isLoading,
    loadingMore,
    hasMore,
    totalCount,
    error,
    loadMore,
    retry
  };
}

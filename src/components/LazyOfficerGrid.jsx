import { useState, useEffect, useRef, useCallback } from 'react';
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

  // Set up intersection observer for individual cards
  useEffect(() => {
    const options = {
      root: null, // viewport
      rootMargin: '100px', // pre-load 100px before visible
      threshold: 0
    };

    observerRef.current = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        const id = entry.target.dataset.officerId;
        if (id) {
          setVisibleItems(prev => {
            const next = new Set(prev);
            if (entry.isIntersecting) {
              next.add(id);
            }
            // Keep items visible for smoother scrolling (don't remove immediately)
            return next;
          });
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
  const ITEMS_PER_PAGE = 20;

  // Reset when filters change
  useEffect(() => {
    setOfficers([]);
    setPage(1);
    setHasMore(true);
    setIsLoading(true);
  }, [JSON.stringify(filters)]);

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

        if (filters.force) params.append('force', filters.force);
        if (filters.dateFrom) params.append('date_from', filters.dateFrom);
        if (filters.dateTo) params.append('date_to', filters.dateTo);

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
      } catch (error) {
        console.error("Failed to fetch officers:", error);
      } finally {
        setIsLoading(false);
        setLoadingMore(false);
      }
    };

    fetchOfficers();
  }, [page, apiBase, JSON.stringify(filters)]);

  // Fetch total count
  useEffect(() => {
    const fetchCount = async () => {
      try {
        const params = new URLSearchParams();
        if (filters.force) params.append('force', filters.force);
        if (filters.dateFrom) params.append('date_from', filters.dateFrom);
        if (filters.dateTo) params.append('date_to', filters.dateTo);

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
  }, [apiBase, JSON.stringify(filters)]);

  const loadMore = useCallback(() => {
    if (!loadingMore && hasMore) {
      setPage(p => p + 1);
    }
  }, [loadingMore, hasMore]);

  return {
    officers,
    isLoading,
    loadingMore,
    hasMore,
    totalCount,
    loadMore
  };
}

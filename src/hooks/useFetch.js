/**
 * Custom hooks for data fetching with proper cleanup
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { fetchWithErrorHandling } from '../utils/api';

/**
 * Hook for fetching data with automatic abort on unmount.
 * Prevents memory leaks from pending requests.
 *
 * @param {string} url - The URL to fetch
 * @param {object} options - Fetch options
 * @param {boolean} options.immediate - Whether to fetch immediately (default: true)
 * @returns {object} - { data, loading, error, refetch }
 *
 * @example
 * // Basic usage - fetches immediately when url changes
 * const { data, loading, error } = useFetch('/api/data');
 *
 * @example
 * // Manual fetching - use refetch() to trigger
 * const { data, refetch } = useFetch('/api/data', { immediate: false });
 * // Later: refetch();
 *
 * @note For dependent fetches (e.g., when other state changes), call refetch()
 * manually instead of passing deps. This avoids potential infinite loops
 * from object/array dependencies.
 */
export function useFetch(url, { immediate = true } = {}) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(immediate);
  const [error, setError] = useState(null);
  const abortControllerRef = useRef(null);

  const fetchData = useCallback(async () => {
    // Abort any existing request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    // Create new abort controller
    abortControllerRef.current = new AbortController();

    setLoading(true);
    setError(null);

    try {
      const response = await fetch(url, {
        signal: abortControllerRef.current.signal,
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const result = await response.json();
      setData(result);
      return result;
    } catch (err) {
      // Ignore abort errors
      if (err.name === 'AbortError') {
        return;
      }
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [url]);

  useEffect(() => {
    if (immediate && url) {
      fetchData();
    }

    // Cleanup: abort on unmount
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, [url, immediate, fetchData]);

  return { data, loading, error, refetch: fetchData };
}

/**
 * Hook for managing multiple API calls with abort controllers.
 * Use this when a component makes several fetch calls on mount.
 *
 * @returns {object} - { createAbortController, abortAll }
 */
export function useAbortController() {
  const controllersRef = useRef(new Set());

  const createAbortController = useCallback(() => {
    const controller = new AbortController();
    controllersRef.current.add(controller);
    return controller;
  }, []);

  const abortAll = useCallback(() => {
    controllersRef.current.forEach(controller => {
      controller.abort();
    });
    controllersRef.current.clear();
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      abortAll();
    };
  }, [abortAll]);

  return { createAbortController, abortAll };
}

/**
 * Safe fetch wrapper that handles abort and returns data or null.
 * Use inside useEffect with an AbortController.
 *
 * @param {string} url - URL to fetch
 * @param {AbortSignal} signal - AbortController signal
 * @returns {Promise<any|null>} - Data or null if aborted/failed
 */
export async function safeFetch(url, signal) {
  try {
    const response = await fetch(url, { signal });
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    return await response.json();
  } catch (err) {
    if (err.name === 'AbortError') {
      return null;
    }
    throw err;
  }
}

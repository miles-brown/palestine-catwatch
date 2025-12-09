/**
 * API Utilities for Palestine Catwatch
 *
 * Provides secure path sanitization and standardized fetch handling
 * to prevent path traversal vulnerabilities and ensure consistent error handling.
 */

// API Base URL configuration
let API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";
if (!API_BASE.startsWith("http")) {
  API_BASE = `https://${API_BASE}`;
}

export { API_BASE };

/**
 * Sanitize a file path to prevent path traversal attacks.
 *
 * This function:
 * 1. Removes ALL occurrences of ../ (not just the first)
 * 2. Removes leading slashes
 * 3. Normalizes multiple slashes to single slashes
 * 4. Handles various bypass attempts like ..././, encoded paths, etc.
 *
 * @param {string} path - The path to sanitize
 * @returns {string|null} - Sanitized path or null if invalid
 */
export function sanitizePath(path) {
  if (!path || typeof path !== 'string') {
    return null;
  }

  let sanitized = path;

  // Decode any URL-encoded characters first
  try {
    sanitized = decodeURIComponent(sanitized);
  } catch {
    // If decoding fails, continue with original
  }

  // Remove all ../ patterns (including nested ones like ..././)
  // Keep looping until no more ../ patterns exist
  let previousLength;
  do {
    previousLength = sanitized.length;
    sanitized = sanitized.replace(/\.\.\//g, '');
    sanitized = sanitized.replace(/\.\./g, '');
  } while (sanitized.length !== previousLength);

  // Remove the ../data/ prefix that's commonly in the database
  sanitized = sanitized.replace(/^\.\.\/data\//g, '');
  sanitized = sanitized.replace(/data\//g, '');

  // Handle paths that start with data/
  if (sanitized.startsWith('data/')) {
    sanitized = sanitized.substring(5);
  }

  // Split on data/ and take the last part
  if (sanitized.includes('data/')) {
    const parts = sanitized.split('data/');
    sanitized = parts[parts.length - 1];
  }

  // Remove leading slashes (handles multiple slashes)
  sanitized = sanitized.replace(/^\/+/, '');

  // Normalize multiple consecutive slashes to single slash
  sanitized = sanitized.replace(/\/+/g, '/');

  // Remove any remaining dangerous characters
  // Only allow alphanumeric, /, -, _, ., and space
  sanitized = sanitized.replace(/[^a-zA-Z0-9/\-_.]/g, '');

  // Final check: ensure we have a valid path
  if (!sanitized || sanitized === '/' || sanitized.includes('..')) {
    return null;
  }

  return sanitized;
}

/**
 * Construct a secure crop URL from a crop_path.
 *
 * @param {string} cropPath - The crop path from the API
 * @param {string} apiBase - Optional API base URL override
 * @returns {string|null} - Full URL or null if path is invalid
 */
export function getCropUrl(cropPath, apiBase = API_BASE) {
  const sanitized = sanitizePath(cropPath);
  if (!sanitized) {
    return null;
  }
  return `${apiBase}/data/${sanitized}`;
}

/**
 * Construct a secure media URL.
 *
 * @param {string} url - The media URL or path
 * @param {string} apiBase - Optional API base URL override
 * @returns {string} - Full URL
 */
export function getMediaUrl(url, apiBase = API_BASE) {
  if (!url) return '';

  // If it's already a full URL, return as-is
  if (url.startsWith('http://') || url.startsWith('https://')) {
    return url;
  }

  const sanitized = sanitizePath(url);
  if (!sanitized) {
    return '';
  }

  return `${apiBase}/data/${sanitized}`;
}

/**
 * Enhanced fetch wrapper with standardized error handling.
 *
 * @param {string} url - The URL to fetch
 * @param {RequestInit} options - Fetch options
 * @returns {Promise<{data: any, error: string|null}>} - Response data or error
 */
export async function safeFetch(url, options = {}) {
  try {
    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });

    // Try to parse response body
    let data;
    const contentType = response.headers.get('content-type');
    if (contentType && contentType.includes('application/json')) {
      data = await response.json();
    } else {
      data = await response.text();
    }

    // Check for HTTP errors
    if (!response.ok) {
      const errorMessage = data?.detail || data?.message || data ||
        `HTTP ${response.status}: ${response.statusText}`;
      return { data: null, error: errorMessage };
    }

    return { data, error: null };
  } catch (err) {
    // Network errors, JSON parse errors, etc.
    console.error('Fetch error:', err);
    return {
      data: null,
      error: err.message || 'Network error occurred'
    };
  }
}

/**
 * Fetch with automatic retry for transient failures.
 *
 * @param {string} url - The URL to fetch
 * @param {RequestInit} options - Fetch options
 * @param {number} maxRetries - Maximum number of retries
 * @returns {Promise<{data: any, error: string|null}>}
 */
export async function fetchWithRetry(url, options = {}, maxRetries = 3) {
  let lastError = null;

  for (let attempt = 0; attempt < maxRetries; attempt++) {
    const result = await safeFetch(url, options);

    if (!result.error) {
      return result;
    }

    // Don't retry client errors (4xx)
    if (result.error.includes('HTTP 4')) {
      return result;
    }

    lastError = result.error;

    // Wait before retrying (exponential backoff)
    if (attempt < maxRetries - 1) {
      await new Promise(resolve => setTimeout(resolve, Math.pow(2, attempt) * 1000));
    }
  }

  return { data: null, error: lastError };
}

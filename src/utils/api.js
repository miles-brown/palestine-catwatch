/**
 * API utility functions for secure data handling
 */

// Configure API base URL
let API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";
if (!API_BASE.startsWith("http")) {
  API_BASE = `https://${API_BASE}`;
}

/**
 * Sanitize a media path to prevent path traversal attacks.
 *
 * Security: This function removes all path traversal patterns including:
 * - ../ sequences (encoded or not)
 * - Leading slashes
 * - Repeated slashes
 *
 * @param {string} path - The raw path from the API
 * @returns {string|null} - Sanitized path or null if invalid
 */
export const sanitizeMediaPath = (path) => {
  if (!path || typeof path !== 'string') return null;

  // Remove all ../ patterns (handles multiple occurrences)
  // Also handles URL-encoded versions: %2e%2e%2f
  let sanitized = path
    .replace(/(\.\.\/)|(\.\.\\)|(%2e%2e%2f)|(%2e%2e%5c)/gi, '')
    // Remove data/ prefix if present
    .replace(/^(\.\.\/)*data\//i, '')
    // Remove leading slashes
    .replace(/^\/+/, '')
    // Collapse multiple slashes to single
    .replace(/\/+/g, '/');

  // Final safety check - reject if any .. remains
  if (sanitized.includes('..')) {
    console.warn('Path traversal attempt detected:', path);
    return null;
  }

  return sanitized;
};

/**
 * Get a full media URL from a path.
 *
 * @param {string} path - The raw path from the API
 * @returns {string|null} - Full URL or null if invalid
 */
export const getMediaUrl = (path) => {
  const sanitized = sanitizeMediaPath(path);
  if (!sanitized) return null;
  return `${API_BASE}/data/${sanitized}`;
};

/**
 * Fetch wrapper with proper error handling.
 *
 * @param {string} url - The URL to fetch
 * @param {object} options - Fetch options
 * @returns {Promise<any>} - Parsed JSON response
 * @throws {Error} - On HTTP errors or network failures
 */
export const fetchWithErrorHandling = async (url, options = {}) => {
  const response = await fetch(url, options);

  if (!response.ok) {
    const errorText = await response.text().catch(() => 'Unknown error');
    let errorMessage;
    try {
      const errorJson = JSON.parse(errorText);
      errorMessage = errorJson.detail || errorJson.message || errorText;
    } catch {
      errorMessage = errorText;
    }
    throw new Error(`HTTP ${response.status}: ${errorMessage}`);
  }

  return response.json();
};

/**
 * Polling interval constant (ms)
 */
export const POLL_INTERVAL_MS = 2000;

export { API_BASE };

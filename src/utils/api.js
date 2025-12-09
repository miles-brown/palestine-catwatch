/**
 * API utility functions for secure data handling
 */

import { IS_PRODUCTION, logger } from './constants';

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
 * Generic user-friendly error messages by HTTP status code.
 * Used in production to avoid exposing internal details.
 */
const GENERIC_ERROR_MESSAGES = {
  400: 'Invalid request. Please check your input.',
  401: 'Authentication required. Please log in.',
  403: 'Access denied. You do not have permission.',
  404: 'The requested resource was not found.',
  409: 'Conflict. The resource may have been modified.',
  422: 'Invalid data provided.',
  429: 'Too many requests. Please try again later.',
  500: 'Server error. Please try again later.',
  502: 'Service temporarily unavailable.',
  503: 'Service temporarily unavailable.',
  504: 'Request timed out. Please try again.',
};

/**
 * Sanitize error message for user display.
 * In production, returns generic messages to avoid leaking internal details.
 * In development, returns the actual error for debugging.
 *
 * @param {number} status - HTTP status code
 * @param {string} rawMessage - Raw error message from server
 * @returns {string} - Sanitized error message
 */
const sanitizeErrorMessage = (status, rawMessage) => {
  if (!IS_PRODUCTION) {
    // In development, show full error for debugging
    return rawMessage;
  }

  // In production, use generic messages
  return GENERIC_ERROR_MESSAGES[status] || 'An unexpected error occurred.';
};

/**
 * Fetch wrapper with proper error handling.
 * Sanitizes error messages in production to prevent information leakage.
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
    let rawMessage;
    try {
      const errorJson = JSON.parse(errorText);
      rawMessage = errorJson.detail || errorJson.message || errorText;
    } catch {
      rawMessage = errorText;
    }

    // Log full error in development for debugging
    logger.debug(`API Error [${response.status}]:`, rawMessage);

    // Sanitize message for user display
    const userMessage = sanitizeErrorMessage(response.status, rawMessage);
    throw new Error(`HTTP ${response.status}: ${userMessage}`);
  }

  return response.json();
};

/**
 * Polling interval constant (ms)
 */
export const POLL_INTERVAL_MS = 2000;

export { API_BASE };

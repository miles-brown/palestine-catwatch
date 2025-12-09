/**
 * Shared constants used across the application
 */

/**
 * UK Police rank colors for consistent styling
 * Based on UK police hierarchy from Constable to Commissioner
 */
export const RANK_COLORS = {
  'Constable': 'bg-blue-100 text-blue-800 border-blue-300',
  'Sergeant': 'bg-green-100 text-green-800 border-green-300',
  'Inspector': 'bg-yellow-100 text-yellow-800 border-yellow-300',
  'Chief Inspector': 'bg-orange-100 text-orange-800 border-orange-300',
  'Superintendent': 'bg-red-100 text-red-800 border-red-300',
  'Chief Superintendent': 'bg-purple-100 text-purple-800 border-purple-300',
  'Commander': 'bg-pink-100 text-pink-800 border-pink-300',
  'Assistant Commissioner': 'bg-indigo-100 text-indigo-800 border-indigo-300',
  'Deputy Commissioner': 'bg-gray-800 text-white border-gray-900',
  'Commissioner': 'bg-black text-white border-gray-900'
};

/**
 * Get rank color classes for a given rank string.
 * Performs case-insensitive partial matching.
 *
 * @param {string} rank - The rank string to match
 * @returns {string} - Tailwind CSS classes for the rank
 */
export const getRankColor = (rank) => {
  if (!rank) return 'bg-gray-100 text-gray-800 border-gray-300';
  const rankLower = rank.toLowerCase();
  for (const [key, value] of Object.entries(RANK_COLORS)) {
    if (rankLower.includes(key.toLowerCase())) return value;
  }
  return 'bg-gray-100 text-gray-800 border-gray-300';
};

/**
 * Equipment category colors
 */
export const CATEGORY_COLORS = {
  defensive: { bg: 'bg-blue-100', text: 'text-blue-800', border: 'border-blue-300' },
  offensive: { bg: 'bg-red-100', text: 'text-red-800', border: 'border-red-300' },
  restraint: { bg: 'bg-orange-100', text: 'text-orange-800', border: 'border-orange-300' },
  identification: { bg: 'bg-green-100', text: 'text-green-800', border: 'border-green-300' },
  communication: { bg: 'bg-purple-100', text: 'text-purple-800', border: 'border-purple-300' },
  specialist: { bg: 'bg-gray-100', text: 'text-gray-800', border: 'border-gray-300' }
};

/**
 * UI Constants
 */
export const UI = {
  // Max heights for scrollable lists (in Tailwind units)
  MAX_LIST_HEIGHT: 'max-h-64',  // 16rem / 256px

  // Polling intervals (in ms)
  POLL_INTERVAL_MS: 2000,

  // Pagination
  DEFAULT_PAGE_SIZE: 20,
  MAX_PAGE_SIZE: 100,

  // Debounce delays (in ms)
  SEARCH_DEBOUNCE_MS: 300,
};

/**
 * Batch Analysis Constants
 */
export const BATCH_ANALYSIS = {
  PENDING_LIMIT: 50,
  MAX_RESULTS_SHOWN: 5,
};

/**
 * Environment detection
 */
export const IS_PRODUCTION = import.meta.env.PROD;

/**
 * Production-aware logger that suppresses debug/warn messages in production.
 * Errors are always logged.
 */
export const logger = {
  error: (...args) => console.error(...args),
  warn: (...args) => {
    if (!IS_PRODUCTION) console.warn(...args);
  },
  info: (...args) => {
    if (!IS_PRODUCTION) console.info(...args);
  },
  debug: (...args) => {
    if (!IS_PRODUCTION) console.log(...args);
  },
};

/**
 * Escalation equipment that indicates potential use of force
 */
export const ESCALATION_EQUIPMENT = [
  'Shield',
  'Long Shield',
  'Baton',
  'Taser',
  'Ballistic Helmet'
];

/**
 * Movement path colors for geographic visualization
 */
export const MOVEMENT_COLORS = [
  '#ef4444', '#f97316', '#eab308', '#22c55e', '#06b6d4',
  '#3b82f6', '#8b5cf6', '#ec4899', '#f43f5e', '#14b8a6'
];

/** Default fallback color when MOVEMENT_COLORS is empty or index invalid */
const DEFAULT_MOVEMENT_COLOR = '#6b7280'; // gray-500

/**
 * Safely get a movement color by index with modulo wrap-around.
 * Returns fallback if array is empty or index is invalid.
 *
 * @param {number} index - The index to look up
 * @returns {string} - Hex color string
 */
export const getMovementColor = (index) => {
  if (!MOVEMENT_COLORS.length || typeof index !== 'number' || !Number.isFinite(index)) {
    return DEFAULT_MOVEMENT_COLOR;
  }
  return MOVEMENT_COLORS[Math.abs(index) % MOVEMENT_COLORS.length];
};

/**
 * Safely parse and format a date string.
 * Returns fallback text if date is invalid.
 *
 * @param {string|Date} dateInput - Date string or Date object
 * @param {object} options - Intl.DateTimeFormat options
 * @param {string} fallback - Text to show for invalid dates
 * @returns {string} - Formatted date or fallback
 */
export const formatDate = (dateInput, options = {}, fallback = 'Unknown date') => {
  if (!dateInput) return fallback;
  try {
    const date = dateInput instanceof Date ? dateInput : new Date(dateInput);
    if (isNaN(date.getTime())) return fallback;
    return date.toLocaleDateString('en-GB', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
      ...options
    });
  } catch {
    return fallback;
  }
};

/**
 * Safely parse and format a date-time string.
 *
 * @param {string|Date} dateInput - Date string or Date object
 * @param {string} fallback - Text to show for invalid dates
 * @returns {string} - Formatted date-time or fallback
 */
export const formatDateTime = (dateInput, fallback = 'Unknown') => {
  if (!dateInput) return fallback;
  try {
    const date = dateInput instanceof Date ? dateInput : new Date(dateInput);
    if (isNaN(date.getTime())) return fallback;
    return date.toLocaleString('en-GB', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  } catch {
    return fallback;
  }
};

/**
 * Escalation score thresholds for equipment analysis
 * Determines risk level based on aggregate equipment scores
 */
export const ESCALATION_THRESHOLDS = {
  CRITICAL: 12,  // Red - highest risk
  HIGH: 8,       // Red - high risk
  ELEVATED: 5,   // Orange - elevated risk
  MODERATE: 3,   // Yellow - moderate risk
  LOW: 0         // Green - low risk
};

/**
 * Escalation level styles with colors and labels
 */
export const ESCALATION_STYLES = {
  CRITICAL: { bg: 'bg-red-600', text: 'text-white', label: 'Critical' },
  HIGH: { bg: 'bg-red-500', text: 'text-white', label: 'High' },
  ELEVATED: { bg: 'bg-orange-500', text: 'text-white', label: 'Elevated' },
  MODERATE: { bg: 'bg-yellow-500', text: 'text-black', label: 'Moderate' },
  LOW: { bg: 'bg-green-500', text: 'text-white', label: 'Low' }
};

/**
 * Get escalation style based on score
 *
 * @param {number} score - The escalation score
 * @returns {object} - { bg, text, label } style object
 */
export const getEscalationStyle = (score) => {
  if (typeof score !== 'number' || !Number.isFinite(score)) {
    return ESCALATION_STYLES.LOW;
  }
  if (score >= ESCALATION_THRESHOLDS.CRITICAL) return ESCALATION_STYLES.CRITICAL;
  if (score >= ESCALATION_THRESHOLDS.HIGH) return ESCALATION_STYLES.HIGH;
  if (score >= ESCALATION_THRESHOLDS.ELEVATED) return ESCALATION_STYLES.ELEVATED;
  if (score >= ESCALATION_THRESHOLDS.MODERATE) return ESCALATION_STYLES.MODERATE;
  return ESCALATION_STYLES.LOW;
};

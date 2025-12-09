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

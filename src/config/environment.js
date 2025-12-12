/**
 * Environment configuration with validation.
 *
 * Validates required environment variables at startup and provides
 * type-safe access to configuration values.
 */

// Required environment variables
const REQUIRED_VARS = [];

// Optional variables with defaults
const OPTIONAL_VARS = {
    VITE_API_URL: 'http://localhost:8000',
};

/**
 * Validate and get an environment variable
 */
function getEnvVar(name, defaultValue = undefined) {
    const value = import.meta.env[name];

    if (value === undefined || value === '') {
        if (defaultValue !== undefined) {
            return defaultValue;
        }
        throw new Error(`Missing required environment variable: ${name}`);
    }

    return value;
}

/**
 * Validate a URL format
 */
function isValidUrl(string) {
    try {
        const url = new URL(string);
        return url.protocol === 'http:' || url.protocol === 'https:';
    } catch {
        return false;
    }
}

/**
 * Environment configuration object
 */
export const config = {
    // API URL with validation
    get apiUrl() {
        const url = getEnvVar('VITE_API_URL', OPTIONAL_VARS.VITE_API_URL);

        if (!isValidUrl(url)) {
            console.error(`Invalid API URL: ${url}. Expected format: http(s)://hostname:port`);
            // Return default instead of crashing - API calls will fail gracefully
            return OPTIONAL_VARS.VITE_API_URL;
        }

        // Remove trailing slash for consistency
        return url.replace(/\/+$/, '');
    },

    // Environment mode
    get isDevelopment() {
        return import.meta.env.DEV;
    },

    get isProduction() {
        return import.meta.env.PROD;
    },

    get mode() {
        return import.meta.env.MODE;
    },
};

/**
 * Validate all required environment variables at startup
 */
export function validateEnvironment() {
    const errors = [];

    // Check required variables
    for (const varName of REQUIRED_VARS) {
        if (!import.meta.env[varName]) {
            errors.push(`Missing required environment variable: ${varName}`);
        }
    }

    // Validate API URL format
    const apiUrl = import.meta.env.VITE_API_URL || OPTIONAL_VARS.VITE_API_URL;
    if (!isValidUrl(apiUrl)) {
        errors.push(`Invalid VITE_API_URL format: ${apiUrl}`);
    }

    // Log warnings/errors but don't crash the app
    if (errors.length > 0) {
        console.error('Environment validation errors:', errors);
        // Don't throw - let the app try to load with defaults
        // API calls will fail gracefully with user-friendly error messages
    }

    return errors.length === 0;
}

/**
 * Log current configuration (safe values only)
 */
export function logConfig() {
    if (import.meta.env.DEV) {
        console.log('Environment Configuration:', {
            apiUrl: config.apiUrl,
            mode: config.mode,
            isDevelopment: config.isDevelopment,
            isProduction: config.isProduction,
        });
    }
}

export default config;

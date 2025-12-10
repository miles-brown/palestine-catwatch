import { useEffect, useRef } from 'react';

const TURNSTILE_SITE_KEY = '0x4AAAAAACFzIwdLZcVWtQ9T';

/**
 * Cloudflare Turnstile CAPTCHA component
 *
 * @param {Object} props
 * @param {function} props.onVerify - Callback when verification succeeds, receives token
 * @param {function} props.onError - Callback when verification fails
 * @param {function} props.onExpire - Callback when token expires
 * @param {string} props.theme - 'light', 'dark', or 'auto' (default: 'dark')
 * @param {string} props.size - 'normal' or 'compact' (default: 'normal')
 */
export default function Turnstile({
  onVerify,
  onError,
  onExpire,
  theme = 'dark',
  size = 'normal'
}) {
  const containerRef = useRef(null);
  const widgetIdRef = useRef(null);

  useEffect(() => {
    // Load Turnstile script if not already loaded
    if (!window.turnstile) {
      const script = document.createElement('script');
      script.src = 'https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit';
      script.async = true;
      script.defer = true;
      document.head.appendChild(script);

      script.onload = () => {
        renderWidget();
      };
    } else {
      renderWidget();
    }

    return () => {
      // Cleanup widget on unmount
      if (widgetIdRef.current !== null && window.turnstile) {
        try {
          window.turnstile.remove(widgetIdRef.current);
        } catch (e) {
          // Widget may already be removed
        }
      }
    };
  }, []);

  const renderWidget = () => {
    if (!containerRef.current || !window.turnstile) return;

    // Remove existing widget if any
    if (widgetIdRef.current !== null) {
      try {
        window.turnstile.remove(widgetIdRef.current);
      } catch (e) {
        // Ignore
      }
    }

    widgetIdRef.current = window.turnstile.render(containerRef.current, {
      sitekey: TURNSTILE_SITE_KEY,
      theme: theme,
      size: size,
      callback: (token) => {
        if (onVerify) onVerify(token);
      },
      'error-callback': () => {
        if (onError) onError();
      },
      'expired-callback': () => {
        if (onExpire) onExpire();
      },
    });
  };

  // Method to reset the widget (can be called via ref)
  const reset = () => {
    if (widgetIdRef.current !== null && window.turnstile) {
      window.turnstile.reset(widgetIdRef.current);
    }
  };

  return (
    <div
      ref={containerRef}
      className="cf-turnstile flex justify-center"
      data-sitekey={TURNSTILE_SITE_KEY}
      data-theme={theme}
      data-size={size}
    />
  );
}

// Export reset function for external use
export const resetTurnstile = (widgetId) => {
  if (window.turnstile && widgetId !== null) {
    window.turnstile.reset(widgetId);
  }
};

/**
 * Tests for API utility functions
 * Run with: npm test
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { sanitizeMediaPath, getMediaUrl, fetchWithErrorHandling, getBestCropUrl, getAllCropUrls } from './api';

describe('sanitizeMediaPath', () => {
  describe('path traversal prevention', () => {
    it('should remove ../ patterns', () => {
      expect(sanitizeMediaPath('../data/image.jpg')).toBe('image.jpg');
      expect(sanitizeMediaPath('../../etc/passwd')).toBe('etc/passwd');
      expect(sanitizeMediaPath('../../../root/.ssh/id_rsa')).toBe('root/.ssh/id_rsa');
    });

    it('should remove multiple consecutive ../ patterns', () => {
      expect(sanitizeMediaPath('../../../data/test.jpg')).toBe('test.jpg');
    });

    it('should remove URL-encoded path traversal attempts', () => {
      // %2e = . and %2f = /
      // After removing encoded ../, the result should not contain path traversal
      const result1 = sanitizeMediaPath('%2e%2e%2fdata/image.jpg');
      expect(result1).not.toContain('..');
      expect(result1).toBe('image.jpg'); // data/ prefix also removed

      const result2 = sanitizeMediaPath('%2e%2e%2f%2e%2e%2fetc/passwd');
      expect(result2).not.toContain('..');
    });

    it('should remove backslash path traversal (Windows-style)', () => {
      // Backslash traversal patterns are removed
      const result1 = sanitizeMediaPath('..\\data\\image.jpg');
      expect(result1).not.toContain('..');

      const result2 = sanitizeMediaPath('%2e%2e%5cdata');
      expect(result2).not.toContain('..');
    });

    it('should return null if path still contains .. after sanitization', () => {
      // This shouldn't happen with proper sanitization, but test the safety check
      const result = sanitizeMediaPath('safe/path/file.jpg');
      expect(result).not.toContain('..');
    });

    it('should handle mixed traversal attempts', () => {
      expect(sanitizeMediaPath('../data/../config/secret.json')).not.toContain('..');
    });
  });

  describe('path normalization', () => {
    it('should remove data/ prefix', () => {
      expect(sanitizeMediaPath('data/images/photo.jpg')).toBe('images/photo.jpg');
      expect(sanitizeMediaPath('../data/frames/1/frame.jpg')).toBe('frames/1/frame.jpg');
    });

    it('should remove leading slashes', () => {
      expect(sanitizeMediaPath('/images/photo.jpg')).toBe('images/photo.jpg');
      expect(sanitizeMediaPath('///multiple/slashes.jpg')).toBe('multiple/slashes.jpg');
    });

    it('should collapse multiple slashes to single', () => {
      expect(sanitizeMediaPath('path//to///file.jpg')).toBe('path/to/file.jpg');
    });
  });

  describe('edge cases', () => {
    it('should return null for null input', () => {
      expect(sanitizeMediaPath(null)).toBeNull();
    });

    it('should return null for undefined input', () => {
      expect(sanitizeMediaPath(undefined)).toBeNull();
    });

    it('should return null for empty string', () => {
      expect(sanitizeMediaPath('')).toBeNull();
    });

    it('should return null for non-string input', () => {
      expect(sanitizeMediaPath(123)).toBeNull();
      expect(sanitizeMediaPath({})).toBeNull();
      expect(sanitizeMediaPath([])).toBeNull();
    });

    it('should handle paths with special characters', () => {
      expect(sanitizeMediaPath('path/file with spaces.jpg')).toBe('path/file with spaces.jpg');
      expect(sanitizeMediaPath('path/file-name_123.jpg')).toBe('path/file-name_123.jpg');
    });

    it('should preserve valid relative paths', () => {
      expect(sanitizeMediaPath('crops/officer_1/face.jpg')).toBe('crops/officer_1/face.jpg');
      expect(sanitizeMediaPath('frames/media_5/frame_0001.jpg')).toBe('frames/media_5/frame_0001.jpg');
    });
  });
});

describe('getMediaUrl', () => {
  it('should return full URL for valid paths', () => {
    const result = getMediaUrl('crops/image.jpg');
    expect(result).toContain('/data/crops/image.jpg');
  });

  it('should return null for invalid paths', () => {
    expect(getMediaUrl(null)).toBeNull();
    expect(getMediaUrl(undefined)).toBeNull();
    expect(getMediaUrl('')).toBeNull();
  });

  it('should sanitize paths before constructing URL', () => {
    const result = getMediaUrl('../../../etc/passwd');
    expect(result).not.toContain('..');
    expect(result).toContain('/data/etc/passwd');
  });
});

describe('fetchWithErrorHandling', () => {
  beforeEach(() => {
    global.fetch = vi.fn();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('should return JSON data on successful response', async () => {
    const mockData = { id: 1, name: 'test' };
    global.fetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockData),
    });

    const result = await fetchWithErrorHandling('http://api.test/data');
    expect(result).toEqual(mockData);
  });

  it('should throw error on non-ok response', async () => {
    global.fetch.mockResolvedValueOnce({
      ok: false,
      status: 404,
      text: () => Promise.resolve('Not Found'),
    });

    await expect(fetchWithErrorHandling('http://api.test/data'))
      .rejects
      .toThrow('HTTP 404: Not Found');
  });

  it('should parse JSON error responses', async () => {
    global.fetch.mockResolvedValueOnce({
      ok: false,
      status: 400,
      text: () => Promise.resolve(JSON.stringify({ detail: 'Invalid request' })),
    });

    await expect(fetchWithErrorHandling('http://api.test/data'))
      .rejects
      .toThrow('HTTP 400: Invalid request');
  });

  it('should pass through fetch options', async () => {
    global.fetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({}),
    });

    await fetchWithErrorHandling('http://api.test/data', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    });

    expect(global.fetch).toHaveBeenCalledWith('http://api.test/data', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    });
  });

  it('should handle network errors', async () => {
    global.fetch.mockRejectedValueOnce(new Error('Network error'));

    await expect(fetchWithErrorHandling('http://api.test/data'))
      .rejects
      .toThrow('Network error');
  });
});

describe('getBestCropUrl', () => {
  describe('priority fallback', () => {
    it('should prioritize face_crop_path when available', () => {
      const appearance = {
        face_crop_path: 'frames/1/face_0.jpg',
        body_crop_path: 'frames/1/body_0.jpg',
        image_crop_path: 'frames/1/crop_0.jpg'
      };

      const result = getBestCropUrl(appearance);

      expect(result).toContain('/data/frames/1/face_0.jpg');
    });

    it('should fall back to body_crop_path when face_crop_path is null', () => {
      const appearance = {
        face_crop_path: null,
        body_crop_path: 'frames/1/body_0.jpg',
        image_crop_path: 'frames/1/crop_0.jpg'
      };

      const result = getBestCropUrl(appearance);

      expect(result).toContain('/data/frames/1/body_0.jpg');
    });

    it('should fall back to image_crop_path when face and body are null', () => {
      const appearance = {
        face_crop_path: null,
        body_crop_path: null,
        image_crop_path: 'frames/1/crop_0.jpg'
      };

      const result = getBestCropUrl(appearance);

      expect(result).toContain('/data/frames/1/crop_0.jpg');
    });

    it('should fall back to body_crop_path when face_crop_path is undefined', () => {
      const appearance = {
        body_crop_path: 'frames/1/body_0.jpg',
        image_crop_path: 'frames/1/crop_0.jpg'
      };

      const result = getBestCropUrl(appearance);

      expect(result).toContain('/data/frames/1/body_0.jpg');
    });
  });

  describe('edge cases', () => {
    it('should return null for null appearance', () => {
      expect(getBestCropUrl(null)).toBeNull();
    });

    it('should return null for undefined appearance', () => {
      expect(getBestCropUrl(undefined)).toBeNull();
    });

    it('should return null when all crop paths are null', () => {
      const appearance = {
        face_crop_path: null,
        body_crop_path: null,
        image_crop_path: null
      };

      expect(getBestCropUrl(appearance)).toBeNull();
    });

    it('should return null when all crop paths are undefined', () => {
      const appearance = {};

      expect(getBestCropUrl(appearance)).toBeNull();
    });

    it('should return null when all crop paths are empty strings', () => {
      const appearance = {
        face_crop_path: '',
        body_crop_path: '',
        image_crop_path: ''
      };

      expect(getBestCropUrl(appearance)).toBeNull();
    });
  });

  describe('security', () => {
    it('should sanitize path traversal attempts in face_crop_path', () => {
      const appearance = {
        face_crop_path: '../../../etc/passwd'
      };

      const result = getBestCropUrl(appearance);

      expect(result).not.toContain('..');
      expect(result).toContain('/data/etc/passwd');
    });

    it('should sanitize path traversal attempts in body_crop_path', () => {
      const appearance = {
        face_crop_path: null,
        body_crop_path: '../../../etc/passwd'
      };

      const result = getBestCropUrl(appearance);

      expect(result).not.toContain('..');
      expect(result).toContain('/data/etc/passwd');
    });
  });

  describe('URL handling', () => {
    it('should handle absolute HTTP URLs directly', () => {
      const appearance = {
        face_crop_path: 'http://cdn.example.com/image.jpg'
      };

      const result = getBestCropUrl(appearance);

      expect(result).toBe('http://cdn.example.com/image.jpg');
    });

    it('should handle absolute HTTPS URLs directly', () => {
      const appearance = {
        face_crop_path: 'https://cdn.example.com/image.jpg'
      };

      const result = getBestCropUrl(appearance);

      expect(result).toBe('https://cdn.example.com/image.jpg');
    });

    it('should handle R2 public URLs', () => {
      const appearance = {
        face_crop_path: 'https://pub-xxx.r2.dev/data/frames/1/face_0.jpg'
      };

      const result = getBestCropUrl(appearance);

      expect(result).toBe('https://pub-xxx.r2.dev/data/frames/1/face_0.jpg');
    });
  });
});

describe('getAllCropUrls', () => {
  describe('all crop types present', () => {
    it('should return all three crop URLs when all paths are present', () => {
      const appearance = {
        face_crop_path: 'frames/1/face_0.jpg',
        body_crop_path: 'frames/1/body_0.jpg',
        image_crop_path: 'frames/1/crop_0.jpg'
      };

      const result = getAllCropUrls(appearance);

      expect(result.face_crop_url).toContain('/data/frames/1/face_0.jpg');
      expect(result.body_crop_url).toContain('/data/frames/1/body_0.jpg');
      expect(result.best_crop_url).toContain('/data/frames/1/face_0.jpg');
    });

    it('should prioritize face in best_crop_url', () => {
      const appearance = {
        face_crop_path: 'frames/1/face_0.jpg',
        body_crop_path: 'frames/1/body_0.jpg',
        image_crop_path: 'frames/1/crop_0.jpg'
      };

      const result = getAllCropUrls(appearance);

      expect(result.best_crop_url).toContain('face_0.jpg');
    });
  });

  describe('partial crop paths', () => {
    it('should handle only body_crop_path present', () => {
      const appearance = {
        face_crop_path: null,
        body_crop_path: 'frames/1/body_0.jpg',
        image_crop_path: null
      };

      const result = getAllCropUrls(appearance);

      expect(result.face_crop_url).toBeNull();
      expect(result.body_crop_url).toContain('/data/frames/1/body_0.jpg');
      expect(result.best_crop_url).toContain('/data/frames/1/body_0.jpg');
    });

    it('should handle only legacy image_crop_path present', () => {
      const appearance = {
        face_crop_path: null,
        body_crop_path: null,
        image_crop_path: 'frames/1/crop_0.jpg'
      };

      const result = getAllCropUrls(appearance);

      expect(result.face_crop_url).toBeNull();
      expect(result.body_crop_url).toBeNull();
      expect(result.best_crop_url).toContain('/data/frames/1/crop_0.jpg');
    });

    it('should handle face and body present, legacy missing', () => {
      const appearance = {
        face_crop_path: 'frames/1/face_0.jpg',
        body_crop_path: 'frames/1/body_0.jpg',
        image_crop_path: null
      };

      const result = getAllCropUrls(appearance);

      expect(result.face_crop_url).toContain('/data/frames/1/face_0.jpg');
      expect(result.body_crop_url).toContain('/data/frames/1/body_0.jpg');
      expect(result.best_crop_url).toContain('/data/frames/1/face_0.jpg');
    });
  });

  describe('edge cases', () => {
    it('should handle null appearance', () => {
      const result = getAllCropUrls(null);

      expect(result).toEqual({
        face_crop_url: null,
        body_crop_url: null,
        best_crop_url: null
      });
    });

    it('should handle undefined appearance', () => {
      const result = getAllCropUrls(undefined);

      expect(result).toEqual({
        face_crop_url: null,
        body_crop_url: null,
        best_crop_url: null
      });
    });

    it('should handle appearance with no crop paths', () => {
      const appearance = {
        face_crop_path: null,
        body_crop_path: null,
        image_crop_path: null
      };

      const result = getAllCropUrls(appearance);

      expect(result.face_crop_url).toBeNull();
      expect(result.body_crop_url).toBeNull();
      expect(result.best_crop_url).toBeNull();
    });
  });

  describe('URL types', () => {
    it('should handle absolute URLs in all crop paths', () => {
      const appearance = {
        face_crop_path: 'https://r2.dev/face.jpg',
        body_crop_path: 'https://r2.dev/body.jpg',
        image_crop_path: 'https://r2.dev/crop.jpg'
      };

      const result = getAllCropUrls(appearance);

      expect(result.face_crop_url).toBe('https://r2.dev/face.jpg');
      expect(result.body_crop_url).toBe('https://r2.dev/body.jpg');
      expect(result.best_crop_url).toBe('https://r2.dev/face.jpg');
    });

    it('should handle mix of absolute and relative URLs', () => {
      const appearance = {
        face_crop_path: 'https://r2.dev/face.jpg',
        body_crop_path: 'frames/1/body_0.jpg',
        image_crop_path: null
      };

      const result = getAllCropUrls(appearance);

      expect(result.face_crop_url).toBe('https://r2.dev/face.jpg');
      expect(result.body_crop_url).toContain('/data/frames/1/body_0.jpg');
      expect(result.best_crop_url).toBe('https://r2.dev/face.jpg');
    });
  });

  describe('fallback priority', () => {
    it('should prioritize face > body > legacy in best_crop_url', () => {
      const testCases = [
        {
          input: { face_crop_path: 'face.jpg', body_crop_path: 'body.jpg', image_crop_path: 'crop.jpg' },
          expected: 'face.jpg'
        },
        {
          input: { face_crop_path: null, body_crop_path: 'body.jpg', image_crop_path: 'crop.jpg' },
          expected: 'body.jpg'
        },
        {
          input: { face_crop_path: null, body_crop_path: null, image_crop_path: 'crop.jpg' },
          expected: 'crop.jpg'
        }
      ];

      testCases.forEach(({ input, expected }) => {
        const result = getAllCropUrls(input);
        expect(result.best_crop_url).toContain(expected);
      });
    });
  });
});

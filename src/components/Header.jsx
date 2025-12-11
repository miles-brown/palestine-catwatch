import { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { Menu, X, LogIn, LogOut, User, Shield } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useAuth } from '../context/AuthContext';

// Constants
const MAX_DISPLAY_LENGTH = 50;

/**
 * Sanitize user display text to prevent XSS and ensure safe rendering.
 * Removes potentially dangerous characters and truncates to max length.
 * @param {string|null|undefined} text - The text to sanitize
 * @param {number} maxLength - Maximum length of output string
 * @returns {string} Sanitized text safe for rendering
 */
const sanitizeDisplayText = (text, maxLength = MAX_DISPLAY_LENGTH) => {
  if (!text || typeof text !== 'string') return '';
  return text
    .replace(/[<>&"']/g, '')
    .trim()
    .slice(0, maxLength);
};

// Navigation hover color classes for Palestine theme
const NAV_HOVER_COLORS = {
  '/our-story': 'hover:bg-red-50', // Red
  '/what-we-want': 'hover:bg-green-50', // Green
  '/about': 'hover:bg-slate-100', // Black (using slate as faint black)
};

const Header = () => {
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();
  const { isAuthenticated, isAdmin, user, logout } = useAuth();

  const publicNavigation = [
    { name: 'Home', href: '/' },
    { name: 'Our Mission', href: '/our-story' },
    { name: 'Our Goals', href: '/what-we-want' },
    { name: 'About', href: '/about' },
  ];

  const authNavigation = [
    { name: 'Home', href: '/' },
    { name: 'Dashboard', href: '/dashboard' },
    { name: 'Database', href: '/equipment' },
    { name: 'About', href: '/about' },
  ];

  const navigation = isAuthenticated ? authNavigation : publicNavigation;

  const isActive = (href) => {
    return location.pathname === href;
  };

  /**
   * Get hover color class for navigation item based on Palestine theme.
   * @param {string} href - The navigation item's href
   * @returns {string} Tailwind CSS class for hover background
   */
  const getNavHoverColor = (href) => {
    return NAV_HOVER_COLORS[href] || 'hover:bg-slate-50';
  };

  const handleLogout = () => {
    logout();
    setIsMenuOpen(false);
    navigate('/');
  };

  return (
    <header className="bg-white border-b border-slate-200 sticky top-0 z-40 shadow-sm">
      {/* Palestine Support Ribbon */}
      <div className="h-1 w-full bg-gradient-to-r from-black via-white to-green-600 relative">
        <div className="absolute left-0 top-0 h-full w-1/4 bg-gradient-to-r from-black to-transparent" />
        <div className="absolute left-0 top-0 h-full w-8 bg-red-600" style={{ clipPath: 'polygon(0 0, 100% 0, 70% 100%, 0 100%)' }} />
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          {/* Logo */}
          <Link to="/" className="flex items-center gap-3">
            <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-slate-900 text-white font-bold text-sm">
              PAC
            </div>
            <div>
              <div className="text-lg font-semibold text-slate-900">
                Palestine Accountability
              </div>
              <div className="hidden sm:block text-xs text-slate-500">
                Police Accountability Campaign
              </div>
            </div>
          </Link>

          {/* Desktop Navigation */}
          <nav className="hidden md:flex items-center space-x-1">
            {navigation.map((item) => (
              <Link
                key={item.name}
                to={item.href}
                className={`px-3 py-2 text-sm font-medium rounded-md transition-colors ${isActive(item.href)
                  ? 'text-slate-900 bg-slate-100'
                  : `text-slate-600 hover:text-slate-900 ${getNavHoverColor(item.href)}`
                  }`}
              >
                {item.name}
              </Link>
            ))}

            <div className="w-px h-6 bg-slate-200 mx-2" />

            {isAuthenticated ? (
              <>
                <Link to="/upload">
                  <Button className="bg-slate-900 hover:bg-slate-800 text-white text-sm">
                    Submit Evidence
                  </Button>
                </Link>

                {/* User Menu */}
                <div className="flex items-center gap-2 pl-2">
                  {isAdmin && (
                    <Link
                      to="/admin"
                      className="p-2 text-slate-500 hover:text-slate-900 hover:bg-slate-50 rounded-md"
                      title="Admin Panel"
                    >
                      <Shield className="h-4 w-4" />
                    </Link>
                  )}
                  <div className="flex items-center gap-2 px-2 py-1 bg-slate-50 rounded-md">
                    <User className="h-4 w-4 text-slate-400" />
                    <span className="text-sm text-slate-700">{sanitizeDisplayText(user?.username)}</span>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={handleLogout}
                    className="text-slate-500 hover:text-slate-900"
                  >
                    <LogOut className="h-4 w-4" />
                  </Button>
                </div>
              </>
            ) : (
              <div className="flex items-center gap-2">
                <Link to="/login">
                  <Button variant="ghost" size="sm" className="text-sm text-slate-600">
                    Sign In
                  </Button>
                </Link>
                <Link to="/register">
                  <Button className="palestine-flag-btn text-white text-sm font-medium px-4 py-2 rounded-md transition-all hover:opacity-90 hover:shadow-md">
                    Get Involved
                  </Button>
                </Link>
              </div>
            )}
          </nav>

          {/* Mobile menu button */}
          <Button
            variant="ghost"
            size="icon"
            className="md:hidden"
            onClick={() => setIsMenuOpen(!isMenuOpen)}
          >
            {isMenuOpen ? (
              <X className="h-5 w-5" />
            ) : (
              <Menu className="h-5 w-5" />
            )}
          </Button>
        </div>

        {/* Mobile Navigation */}
        {isMenuOpen && (
          <div className="md:hidden border-t border-slate-100 py-4">
            <nav className="flex flex-col space-y-1">
              {/* User Info (if logged in) */}
              {isAuthenticated && (
                <div className="px-3 py-3 mb-2 bg-slate-50 rounded-lg">
                  <div className="flex items-center gap-2">
                    <User className="h-5 w-5 text-slate-600" />
                    <div>
                      <p className="font-medium text-slate-900">{sanitizeDisplayText(user?.full_name) || sanitizeDisplayText(user?.username)}</p>
                      <p className="text-xs text-slate-500 capitalize">{sanitizeDisplayText(user?.role)}</p>
                    </div>
                  </div>
                </div>
              )}

              {navigation.map((item) => (
                <Link
                  key={item.name}
                  to={item.href}
                  className={`text-base font-medium px-3 py-3 rounded-lg ${isActive(item.href) ? 'text-slate-900 bg-slate-100' : 'text-slate-600'
                    }`}
                  onClick={() => setIsMenuOpen(false)}
                >
                  {item.name}
                </Link>
              ))}

              {isAuthenticated && (
                <>
                  {/* Tools Section */}
                  <div className="pt-3 mt-2 border-t border-slate-100">
                    <p className="px-3 py-1 text-xs font-semibold text-slate-400 uppercase tracking-wider">Research Tools</p>
                    <Link
                      to="/face-search"
                      className={`text-base font-medium px-3 py-3 rounded-lg block ${isActive('/face-search') ? 'text-slate-900 bg-slate-100' : 'text-slate-600'}`}
                      onClick={() => setIsMenuOpen(false)}
                    >
                      Face Search
                    </Link>
                    <Link
                      to="/equipment"
                      className={`text-base font-medium px-3 py-3 rounded-lg block ${isActive('/equipment') ? 'text-slate-900 bg-slate-100' : 'text-slate-600'}`}
                      onClick={() => setIsMenuOpen(false)}
                    >
                      Equipment Database
                    </Link>
                    <Link
                      to="/chain-of-command"
                      className={`text-base font-medium px-3 py-3 rounded-lg block ${isActive('/chain-of-command') ? 'text-slate-900 bg-slate-100' : 'text-slate-600'}`}
                      onClick={() => setIsMenuOpen(false)}
                    >
                      Chain of Command
                    </Link>
                    <Link
                      to="/geographic"
                      className={`text-base font-medium px-3 py-3 rounded-lg block ${isActive('/geographic') ? 'text-slate-900 bg-slate-100' : 'text-slate-600'}`}
                      onClick={() => setIsMenuOpen(false)}
                    >
                      Geographic Analysis
                    </Link>
                    <Link
                      to="/equipment-correlation"
                      className={`text-base font-medium px-3 py-3 rounded-lg block ${isActive('/equipment-correlation') ? 'text-slate-900 bg-slate-100' : 'text-slate-600'}`}
                      onClick={() => setIsMenuOpen(false)}
                    >
                      Equipment Correlation
                    </Link>
                    <Link
                      to="/timeline"
                      className={`text-base font-medium px-3 py-3 rounded-lg block ${isActive('/timeline') ? 'text-slate-900 bg-slate-100' : 'text-slate-600'}`}
                      onClick={() => setIsMenuOpen(false)}
                    >
                      Event Timeline
                    </Link>
                    {isAdmin && (
                      <Link
                        to="/admin"
                        className={`text-base font-medium px-3 py-3 rounded-lg block ${isActive('/admin') ? 'text-slate-900 bg-slate-100' : 'text-slate-600'}`}
                        onClick={() => setIsMenuOpen(false)}
                      >
                        Admin Panel
                      </Link>
                    )}
                  </div>
                </>
              )}

              {/* Info Section */}
              <div className="pt-3 mt-2 border-t border-slate-100">
                <p className="px-3 py-1 text-xs font-semibold text-slate-400 uppercase tracking-wider">Information</p>
                <Link
                  to="/manifesto"
                  className="text-base font-medium text-slate-600 px-3 py-3 rounded-lg block"
                  onClick={() => setIsMenuOpen(false)}
                >
                  Our Approach
                </Link>
                <Link
                  to="/terms"
                  className="text-base font-medium text-slate-600 px-3 py-3 rounded-lg block"
                  onClick={() => setIsMenuOpen(false)}
                >
                  Terms of Use
                </Link>
                <Link
                  to="/privacy"
                  className="text-base font-medium text-slate-600 px-3 py-3 rounded-lg block"
                  onClick={() => setIsMenuOpen(false)}
                >
                  Privacy Policy
                </Link>
              </div>

              {/* Action Buttons */}
              <div className="pt-3 mt-2 border-t border-slate-100 space-y-2">
                {isAuthenticated ? (
                  <>
                    <Link to="/upload" onClick={() => setIsMenuOpen(false)}>
                      <Button className="w-full bg-slate-900 hover:bg-slate-800 text-white py-3 text-base">
                        Submit Evidence
                      </Button>
                    </Link>
                    <Button
                      variant="outline"
                      className="w-full py-3 text-base"
                      onClick={handleLogout}
                    >
                      <LogOut className="h-4 w-4 mr-2" />
                      Sign Out
                    </Button>
                  </>
                ) : (
                  <>
                    <Link to="/login" onClick={() => setIsMenuOpen(false)}>
                      <Button variant="outline" className="w-full py-3 text-base">
                        Sign In
                      </Button>
                    </Link>
                    <Link to="/register" onClick={() => setIsMenuOpen(false)}>
                      <Button className="w-full palestine-flag-btn text-white py-3 text-base font-medium">
                        Get Involved
                      </Button>
                    </Link>
                  </>
                )}
              </div>
            </nav>
          </div>
        )}
      </div>
    </header>
  );
};

export default Header;

import { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { Menu, X, AlertTriangle, Eye, LogIn, LogOut, User, Shield } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useAuth } from '../context/AuthContext';

// Maximum length for displayed user text
const MAX_DISPLAY_LENGTH = 50;

/**
 * Sanitize user display text to prevent XSS and ensure safe rendering.
 * @param {string} text - The text to sanitize
 * @param {number} maxLength - Maximum allowed length (default: MAX_DISPLAY_LENGTH)
 * @returns {string} - Sanitized text safe for display
 */
const sanitizeDisplayText = (text, maxLength = MAX_DISPLAY_LENGTH) => {
  if (!text || typeof text !== 'string') return '';
  // Remove potentially dangerous characters and limit length
  return text
    .replace(/[<>&"']/g, '')
    .trim()
    .slice(0, maxLength);
};

const Header = () => {
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();
  const { isAuthenticated, isAdmin, user, logout } = useAuth();

  const publicNavigation = [
    { name: 'Home', href: '/' },
    { name: 'Our Story', href: '/our-story' },
    { name: 'What We Want', href: '/what-we-want' },
    { name: 'About', href: '/about' },
  ];

  const authNavigation = [
    { name: 'Home', href: '/' },
    { name: 'Dashboard', href: '/dashboard' },
    { name: 'Our Story', href: '/our-story' },
    { name: 'About', href: '/about' },
  ];

  const navigation = isAuthenticated ? authNavigation : publicNavigation;

  const isActive = (href) => {
    return location.pathname === href;
  };

  const handleLogout = () => {
    logout();
    setIsMenuOpen(false);
    navigate('/');
  };

  return (
    <>
      {/* Palestine flag stripe */}
      <div className="palestine-flag-stripe"></div>

      {/* Dystopian warning banner */}
      <div className="warning-banner px-4 py-2 text-center text-sm">
        <div className="max-w-7xl mx-auto flex items-center justify-center gap-2">
          <AlertTriangle className="h-4 w-4" />
          <span className="font-mono">
            "In times of universal deceit, telling the truth becomes a revolutionary act" - Orwell
          </span>
          <Eye className="h-4 w-4" />
        </div>
      </div>

      <header className="bg-white border-b-2 border-green-700 sticky top-0 z-40 shadow-md">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            {/* Logo with PA emblem */}
            <Link to="/" className="flex items-center gap-2 sm:gap-3">
              <div className="pa-emblem text-sm sm:text-base">PA</div>
              <div>
                <div className="text-base sm:text-xl font-bold text-gray-900">
                  Palestine Accountability
                </div>
                <div className="hidden sm:flex text-xs text-gray-600 font-medium items-center gap-2">
                  <span className="hidden md:inline">For Press Freedom & Democratic Rights</span>
                </div>
              </div>
            </Link>

            {/* Desktop Navigation */}
            <nav className="hidden md:flex items-center space-x-6">
              {navigation.map((item) => (
                <Link
                  key={item.name}
                  to={item.href}
                  className={`text-sm font-medium transition-colors hover:text-green-700 ${isActive(item.href)
                    ? 'text-green-700 border-b-2 border-green-700 pb-1'
                    : 'text-gray-700'
                    }`}
                >
                  {item.name}
                </Link>
              ))}

              {isAuthenticated ? (
                <>
                  <Link to="/upload">
                    <Button className="bg-red-600 hover:bg-red-700 text-white text-sm">
                      Submit Evidence
                    </Button>
                  </Link>

                  {/* User Menu */}
                  <div className="flex items-center gap-3 pl-3 border-l border-gray-300">
                    {isAdmin && (
                      <Link
                        to="/admin"
                        className="text-gray-600 hover:text-green-700"
                        title="Admin Panel"
                      >
                        <Shield className="h-5 w-5" />
                      </Link>
                    )}
                    <div className="flex items-center gap-2">
                      <User className="h-4 w-4 text-gray-500" />
                      <span className="text-sm text-gray-700">{sanitizeDisplayText(user?.username)}</span>
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={handleLogout}
                      className="text-gray-600 hover:text-red-600"
                    >
                      <LogOut className="h-4 w-4" />
                    </Button>
                  </div>
                </>
              ) : (
                <div className="flex items-center gap-2">
                  <Link to="/login">
                    <Button variant="outline" size="sm" className="text-sm">
                      <LogIn className="h-4 w-4 mr-1" />
                      Sign In
                    </Button>
                  </Link>
                  <Link to="/register">
                    <Button className="bg-green-600 hover:bg-green-700 text-white text-sm">
                      Join Us
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
            <div className="md:hidden border-t border-gray-200 py-4 animate-in slide-in-from-top duration-200">
              <nav className="flex flex-col space-y-1">
                {/* User Info (if logged in) */}
                {isAuthenticated && (
                  <div className="px-3 py-3 mb-2 bg-green-50 rounded-lg">
                    <div className="flex items-center gap-2">
                      <User className="h-5 w-5 text-green-700" />
                      <div>
                        <p className="font-medium text-gray-900">{sanitizeDisplayText(user?.full_name) || sanitizeDisplayText(user?.username)}</p>
                        <p className="text-xs text-gray-500">{sanitizeDisplayText(user?.role)}</p>
                      </div>
                    </div>
                  </div>
                )}

                {navigation.map((item) => (
                  <Link
                    key={item.name}
                    to={item.href}
                    className={`text-base font-medium transition-colors hover:text-green-700 px-3 py-3 rounded-lg ${isActive(item.href) ? 'text-green-700 bg-green-50' : 'text-gray-700'
                      }`}
                    onClick={() => setIsMenuOpen(false)}
                  >
                    {item.name}
                  </Link>
                ))}

                {isAuthenticated && (
                  <>
                    {/* Tools Section */}
                    <div className="pt-3 mt-2 border-t border-gray-200">
                      <p className="px-3 py-1 text-xs font-semibold text-gray-400 uppercase tracking-wider">Tools</p>
                      <Link
                        to="/face-search"
                        className={`text-base font-medium px-3 py-3 rounded-lg block ${isActive('/face-search') ? 'text-green-700 bg-green-50' : 'text-gray-700'}`}
                        onClick={() => setIsMenuOpen(false)}
                      >
                        Face Search
                      </Link>
                      <Link
                        to="/equipment"
                        className={`text-base font-medium px-3 py-3 rounded-lg block ${isActive('/equipment') ? 'text-green-700 bg-green-50' : 'text-gray-700'}`}
                        onClick={() => setIsMenuOpen(false)}
                      >
                        Equipment Database
                      </Link>
                      <Link
                        to="/chain-of-command"
                        className={`text-base font-medium px-3 py-3 rounded-lg block ${isActive('/chain-of-command') ? 'text-green-700 bg-green-50' : 'text-gray-700'}`}
                        onClick={() => setIsMenuOpen(false)}
                      >
                        Chain of Command
                      </Link>
                      <Link
                        to="/geographic"
                        className={`text-base font-medium px-3 py-3 rounded-lg block ${isActive('/geographic') ? 'text-green-700 bg-green-50' : 'text-gray-700'}`}
                        onClick={() => setIsMenuOpen(false)}
                      >
                        Geographic Map
                      </Link>
                      <Link
                        to="/equipment-correlation"
                        className={`text-base font-medium px-3 py-3 rounded-lg block ${isActive('/equipment-correlation') ? 'text-green-700 bg-green-50' : 'text-gray-700'}`}
                        onClick={() => setIsMenuOpen(false)}
                      >
                        Escalation Analysis
                      </Link>
                      <Link
                        to="/timeline"
                        className={`text-base font-medium px-3 py-3 rounded-lg block ${isActive('/timeline') ? 'text-green-700 bg-green-50' : 'text-gray-700'}`}
                        onClick={() => setIsMenuOpen(false)}
                      >
                        Event Timeline
                      </Link>
                      {isAdmin && (
                        <Link
                          to="/admin"
                          className={`text-base font-medium px-3 py-3 rounded-lg block ${isActive('/admin') ? 'text-green-700 bg-green-50' : 'text-gray-700'}`}
                          onClick={() => setIsMenuOpen(false)}
                        >
                          Admin Panel
                        </Link>
                      )}
                    </div>
                  </>
                )}

                {/* Info Section */}
                <div className="pt-3 mt-2 border-t border-gray-200">
                  <p className="px-3 py-1 text-xs font-semibold text-gray-400 uppercase tracking-wider">Info</p>
                  <Link
                    to="/manifesto"
                    className="text-base font-medium text-gray-700 hover:text-red-600 px-3 py-3 rounded-lg block"
                    onClick={() => setIsMenuOpen(false)}
                  >
                    Manifesto
                  </Link>
                  <Link
                    to="/terms"
                    className="text-base font-medium text-gray-700 px-3 py-3 rounded-lg block"
                    onClick={() => setIsMenuOpen(false)}
                  >
                    Terms
                  </Link>
                  <Link
                    to="/privacy"
                    className="text-base font-medium text-gray-700 px-3 py-3 rounded-lg block"
                    onClick={() => setIsMenuOpen(false)}
                  >
                    Privacy
                  </Link>
                </div>

                {/* Action Buttons */}
                <div className="pt-3 mt-2 border-t border-gray-200 space-y-2">
                  {isAuthenticated ? (
                    <>
                      <Link to="/upload" onClick={() => setIsMenuOpen(false)}>
                        <Button className="w-full bg-red-600 hover:bg-red-700 text-white py-3 text-base">
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
                          <LogIn className="h-4 w-4 mr-2" />
                          Sign In
                        </Button>
                      </Link>
                      <Link to="/register" onClick={() => setIsMenuOpen(false)}>
                        <Button className="w-full bg-green-600 hover:bg-green-700 text-white py-3 text-base">
                          Create Account
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
    </>
  );
};

export default Header;

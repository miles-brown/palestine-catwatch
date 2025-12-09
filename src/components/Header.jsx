import { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Menu, X, AlertTriangle, Eye } from 'lucide-react';
import { Button } from '@/components/ui/button';

const Header = () => {
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const location = useLocation();

  const navigation = [
    { name: 'Home', href: '/' },
    { name: 'Dashboard', href: '/dashboard' },
    { name: 'Our Story', href: '/our-story' },
    { name: 'What We Want', href: '/what-we-want' },
    { name: 'About', href: '/about' },
  ];

  const isActive = (href) => {
    return location.pathname === href;
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
            <nav className="hidden md:flex items-center space-x-8">
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
              <Link to="/upload">
                <Button className="bg-red-600 hover:bg-red-700 text-white text-sm">
                  Submit Evidence
                </Button>
              </Link>
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
                    to="/admin"
                    className={`text-base font-medium px-3 py-3 rounded-lg block ${isActive('/admin') ? 'text-green-700 bg-green-50' : 'text-gray-700'}`}
                    onClick={() => setIsMenuOpen(false)}
                  >
                    Admin Panel
                  </Link>
                </div>

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

                <div className="pt-3 mt-2 border-t border-gray-200">
                  <Link to="/upload" onClick={() => setIsMenuOpen(false)}>
                    <Button className="w-full bg-red-600 hover:bg-red-700 text-white py-3 text-base">
                      Submit Evidence
                    </Button>
                  </Link>
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


import { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Menu, X, AlertTriangle, Eye } from 'lucide-react';
import { Button } from '@/components/ui/button';

const Header = () => {
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const location = useLocation();

  const navigation = [
    { name: 'Home', href: '/' },
    { name: 'Our Story', href: '/our-story' },
    { name: 'What We Want', href: '/what-we-want' },
    { name: 'About', href: '/about' },
    { name: 'Terms', href: '/terms' },
    { name: 'Privacy', href: '/privacy' },
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
            <Link to="/" className="flex items-center gap-3">
              <div className="pa-emblem">PA</div>
              <div>
                <div className="text-xl font-bold text-gray-900">
                  Palestine Accountability
                </div>
                <div className="text-xs text-gray-600 font-medium">
                  For Press Freedom & Democratic Rights
                </div>
              </div>
            </Link>

            {/* Desktop Navigation */}
            <nav className="hidden md:flex items-center space-x-8">
              {navigation.map((item) => (
                <Link
                  key={item.name}
                  to={item.href}
                  className={`text-sm font-medium transition-colors hover:text-green-700 ${
                    isActive(item.href)
                      ? 'text-green-700 border-b-2 border-green-700 pb-1'
                      : 'text-gray-700'
                  }`}
                >
                  {item.name}
                </Link>
              ))}
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
            <div className="md:hidden border-t border-gray-200 py-4">
              <nav className="flex flex-col space-y-4">
                {navigation.map((item) => (
                  <Link
                    key={item.name}
                    to={item.href}
                    className={`text-sm font-medium transition-colors hover:text-green-700 ${
                      isActive(item.href) ? 'text-green-700' : 'text-gray-700'
                    }`}
                    onClick={() => setIsMenuOpen(false)}
                  >
                    {item.name}
                  </Link>
                ))}
              </nav>
            </div>
          )}
        </div>
      </header>
    </>
  );
};

export default Header;


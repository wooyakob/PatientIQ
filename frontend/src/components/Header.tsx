import { Plus, Moon, Sun } from 'lucide-react';
import { Link, useLocation } from 'react-router-dom';
import { cn } from '@/lib/utils';
import { useTheme } from '@/contexts/ThemeContext';
import { Button } from '@/components/ui/button';

export function Header() {
  const location = useLocation();
  const { theme, toggleTheme } = useTheme();
  
  const navLinks = [
    { to: '/', label: 'Patient Dashboard' },
    { to: '/calendar', label: 'Calendar' },
    { to: '/messages', label: 'Messages' },
  ];

  return (
    <header className="sticky top-0 z-50 glass-card border-b border-border/50 px-6 py-4">
      <div className="max-w-7xl mx-auto flex items-center justify-between">
        <Link to="/" className="flex items-center gap-3">
          <div className="gradient-primary p-2 rounded-xl">
            <Plus className="h-5 w-5 text-primary-foreground" strokeWidth={3} />
          </div>
          <span className="text-xl font-semibold text-foreground">PatientIQ</span>
        </Link>
        <nav className="flex items-center gap-6">
          {navLinks.map((link) => (
            <Link
              key={link.to}
              to={link.to}
              className={cn(
                "text-sm font-medium transition-colors hover:text-primary",
                location.pathname === link.to
                  ? "text-primary"
                  : "text-muted-foreground"
              )}
            >
              {link.label}
            </Link>
          ))}
          <Button
            variant="ghost"
            size="icon"
            onClick={toggleTheme}
            className="ml-2 h-9 w-9"
            aria-label={theme === 'light' ? 'Switch to dark mode' : 'Switch to light mode'}
          >
            {theme === 'light' ? (
              <Moon className="h-5 w-5 text-muted-foreground hover:text-foreground transition-colors" />
            ) : (
              <Sun className="h-5 w-5 text-muted-foreground hover:text-foreground transition-colors" />
            )}
          </Button>
        </nav>
      </div>
    </header>
  );
}

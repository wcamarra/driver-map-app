import { Link, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export function Layout() {
  const { user, logout } = useAuth();
  const location = useLocation();

  return (
    <div className="app-shell">
      <header className="app-header">
        <Link to="/" className="brand">
          Driver Map
        </Link>
        <nav className="nav-links">
          <Link to="/" className={location.pathname === '/' ? 'active' : ''}>
            Discover
          </Link>
          {user && (
            <>
              <Link to="/generate" className={location.pathname === '/generate' ? 'active' : ''}>
                Generate
              </Link>
              <Link to="/editor" className={location.pathname.startsWith('/editor') ? 'active' : ''}>
                Create
              </Link>
              <Link to="/mine" className={location.pathname === '/mine' ? 'active' : ''}>
                My routes
              </Link>
            </>
          )}
        </nav>
        <div className="header-actions">
          {user ? (
            <>
              <span className="user-label">@{user.username}</span>
              <button type="button" className="btn btn-ghost" onClick={logout}>
                Log out
              </button>
            </>
          ) : (
            <Link to="/login" className="btn btn-primary">
              Sign in
            </Link>
          )}
        </div>
      </header>
      <main className="app-main">
        <Outlet />
      </main>
    </div>
  );
}

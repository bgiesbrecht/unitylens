import { useEffect, useState } from 'react';
import {
  LayoutDashboard,
  Database,
  FolderTree,
  Search,
  Settings,
  ScanSearch,
  TableProperties,
  LogOut,
} from 'lucide-react';
import { Link } from '../router';
import { getVersion } from '../api/client';
import { useAuth } from '../auth/AuthContext';

interface SidebarProps {
  open: boolean;
  onClose: () => void;
}

type Role = 'admin' | 'viewer';

interface NavItem {
  to: string;
  icon: typeof LayoutDashboard;
  label: string;
  roles: Role[];
}

const NAV_ITEMS: NavItem[] = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard', roles: ['admin'] },
  { to: '/sources', icon: Database, label: 'Sources', roles: ['admin'] },
  { to: '/dictionary', icon: TableProperties, label: 'Data Dictionary', roles: ['admin', 'viewer'] },
  { to: '/browse', icon: FolderTree, label: 'Browse Catalog', roles: ['admin', 'viewer'] },
  { to: '/search', icon: Search, label: 'Search', roles: ['admin', 'viewer'] },
];

const ADMIN_ITEMS: NavItem[] = [
  { to: '/admin', icon: Settings, label: 'Admin', roles: ['admin'] },
];

export function Sidebar({ open, onClose }: SidebarProps) {
  const { user, logout } = useAuth();
  const [version, setVersion] = useState<string>('');

  useEffect(() => {
    getVersion()
      .then((v) => setVersion(v))
      .catch(() => setVersion(''));
  }, []);

  const role: Role | null = (user?.role as Role | undefined) || null;
  const navItems = role ? NAV_ITEMS.filter((i) => i.roles.includes(role)) : [];
  const adminItems = role ? ADMIN_ITEMS.filter((i) => i.roles.includes(role)) : [];

  return (
    <>
      {open && <div className="sidebar-overlay" onClick={onClose} />}
      <aside className={`sidebar${open ? ' open' : ''}`}>
        <div className="sidebar-brand">
          <div className="sidebar-brand-icon">
            <ScanSearch size={18} />
          </div>
          <div>
            <div className="sidebar-brand-text">UnityLens</div>
            <div className="sidebar-brand-sub">Data Catalog</div>
          </div>
        </div>

        <nav className="sidebar-nav">
          <div className="sidebar-nav-section">Navigation</div>
          {navItems.map((item) => (
            <Link
              key={item.to}
              to={item.to}
              className="sidebar-link"
              activeClassName="active"
              onClick={onClose}
            >
              <item.icon size={18} />
              {item.label}
            </Link>
          ))}

          {adminItems.length > 0 && (
            <>
              <div className="sidebar-nav-section" style={{ marginTop: 12 }}>
                Administration
              </div>
              {adminItems.map((item) => (
                <Link
                  key={item.to}
                  to={item.to}
                  className="sidebar-link"
                  activeClassName="active"
                  onClick={onClose}
                >
                  <item.icon size={18} />
                  {item.label}
                </Link>
              ))}
            </>
          )}
        </nav>

        <div className="sidebar-footer">
          {user && (
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                marginBottom: 6,
                gap: 8,
              }}
            >
              <span
                style={{
                  fontSize: '0.78rem',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                }}
                title={`${user.username} (${user.role})`}
              >
                {user.username} · {user.role}
              </span>
              <button
                onClick={() => logout()}
                title="Sign out"
                style={{
                  background: 'transparent',
                  border: 'none',
                  color: 'inherit',
                  cursor: 'pointer',
                  padding: 4,
                  display: 'flex',
                  alignItems: 'center',
                }}
              >
                <LogOut size={14} />
              </button>
            </div>
          )}
          <div>UnityLens{version ? ` v${version}` : ''}</div>
        </div>
      </aside>
    </>
  );
}

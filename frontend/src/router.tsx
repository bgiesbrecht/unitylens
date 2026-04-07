import { useState, useEffect, useCallback, createContext, useContext } from 'react';

interface RouterContext {
  path: string;
  navigate: (path: string) => void;
  params: Record<string, string>;
}

const RouterCtx = createContext<RouterContext>({
  path: '/',
  navigate: () => {},
  params: {},
});

export function useRouter() {
  return useContext(RouterCtx);
}

function getHashPath(): string {
  const hash = window.location.hash.slice(1);
  return hash || '/';
}

export function RouterProvider({ children }: { children: React.ReactNode }) {
  const [path, setPath] = useState(getHashPath);

  useEffect(() => {
    const handler = () => setPath(getHashPath());
    window.addEventListener('hashchange', handler);
    return () => window.removeEventListener('hashchange', handler);
  }, []);

  const navigate = useCallback((newPath: string) => {
    window.location.hash = newPath;
  }, []);

  return (
    <RouterCtx.Provider value={{ path, navigate, params: {} }}>
      {children}
    </RouterCtx.Provider>
  );
}

interface Route {
  pattern: string;
  component: React.ComponentType<{ params: Record<string, string> }>;
}

export function Routes({ routes }: { routes: Route[] }) {
  const { path } = useRouter();

  const basePath = path.split('?')[0];

  for (const route of routes) {
    const params = matchRoute(route.pattern, basePath);
    if (params !== null) {
      const Component = route.component;
      return <Component params={params} />;
    }
  }

  return <div className="page-not-found">Page not found</div>;
}

function matchRoute(pattern: string, path: string): Record<string, string> | null {
  const patternParts = pattern.split('/').filter(Boolean);
  const pathParts = path.split('/').filter(Boolean);

  if (patternParts.length !== pathParts.length) return null;

  const params: Record<string, string> = {};
  for (let i = 0; i < patternParts.length; i++) {
    if (patternParts[i].startsWith(':')) {
      params[patternParts[i].slice(1)] = decodeURIComponent(pathParts[i]);
    } else if (patternParts[i] !== pathParts[i]) {
      return null;
    }
  }
  return params;
}

export function Link({
  to,
  children,
  className,
  activeClassName,
  onClick,
}: {
  to: string;
  children: React.ReactNode;
  className?: string;
  activeClassName?: string;
  onClick?: () => void;
}) {
  const { path } = useRouter();
  const basePath = path.split('?')[0];
  const isActive = basePath === to || (to !== '/' && basePath.startsWith(to));
  const cls = [className, isActive && activeClassName].filter(Boolean).join(' ');

  return (
    <a
      href={`#${to}`}
      className={cls}
      onClick={(e) => {
        if (onClick) onClick();
      }}
    >
      {children}
    </a>
  );
}

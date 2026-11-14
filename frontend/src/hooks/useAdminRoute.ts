import { useEffect, useState } from 'react';

const ADMIN_HASH = '#admin';

const isAdminHash = (): boolean => window.location.hash === ADMIN_HASH;

/**
 * True when the page is opened as `/#admin`. This only hides operator screens from the
 * citizen navigation; it is not access control (the API must enforce that itself).
 */
export function useAdminRoute(): boolean {
  const [isAdmin, setIsAdmin] = useState<boolean>(isAdminHash);

  useEffect(() => {
    const onHashChange = (): void => setIsAdmin(isAdminHash());
    window.addEventListener('hashchange', onHashChange);
    return () => window.removeEventListener('hashchange', onHashChange);
  }, []);

  return isAdmin;
}

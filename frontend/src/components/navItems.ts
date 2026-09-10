/**
 * The primary destinations, shared by the desktop header nav and the mobile
 * bottom nav so the two cannot drift apart.
 */
export interface NavItem {
  to: string;
  label: string;
  /** Path data for a 20x20 viewBox icon. */
  path: string;
}

export const NAV_ITEMS: NavItem[] = [
  {
    to: "/",
    label: "Home",
    path: "M3 9.5 10 3l7 6.5V17a1 1 0 0 1-1 1h-4v-5H8v5H4a1 1 0 0 1-1-1z",
  },
  {
    to: "/trip",
    label: "Trip",
    path: "M3 13h14M5 13V9l2-4h6l2 4v4M6.5 16.5h1M12.5 16.5h1",
  },
  {
    to: "/radar",
    label: "Radar",
    path: "M10 2a8 8 0 1 0 0 16 8 8 0 0 0 0-16zM10 6v4l3 2",
  },
  {
    to: "/learn",
    label: "Learn",
    path: "M3 4.5c2.3 0 4.3.6 7 2v10c-2.7-1.4-4.7-2-7-2V4.5Zm14 0c-2.3 0-4.3.6-7 2v10c2.7-1.4 4.7-2 7-2V4.5Z",
  },
  {
    to: "/me",
    label: "Me",
    path: "M10 3a3 3 0 1 1 0 6 3 3 0 0 1 0-6Zm-5 14c.4-3.2 2.1-5 5-5s4.6 1.8 5 5H5Z",
  },
];

/**
 * Whether a nav item is the active one for the current location.
 *
 * Home matches exactly; every other tab stays highlighted across its whole
 * section.
 *
 * @param item - The nav item.
 * @param pathname - The current location pathname.
 * @returns True when the item should render as active.
 */
export function isNavItemActive(item: NavItem, pathname: string): boolean {
  if (item.to === "/") return pathname === "/";
  return pathname === item.to || pathname.startsWith(`${item.to}/`);
}

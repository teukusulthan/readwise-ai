/** Optional `handle` on a RouteObject, read by AppLayout via `useMatches()`. */
export interface IRouteHandle {
  /**
   * The page fills the main column exactly and manages its own scrolling
   * (e.g. the chat: message list scrolls, composer stays pinned). No page padding.
   */
  fullHeight?: boolean
}

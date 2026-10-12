/**
 * Inertia (momentum) scrolling for a scroll container — used by PerfectScrollArea.
 *
 * Wheel and trackpad input move a *target* position; every animation frame the real
 * scrollTop eases towards it (exponential smoothing, frame-rate independent). Result:
 * a mouse wheel glides instead of jumping in 100 px steps, and fast flicks carry on
 * softly. Native scrolls we did not start (scrollbar drag, keyboard, find-in-page,
 * programmatic jumps) are adopted as the new position, so nothing ever fights the user.
 *
 * Nested areas: the innermost area that can still move in the wheel's direction takes
 * the event (and marks it handled); at its edge it lets the event reach its parent.
 * Ctrl+wheel (pinch zoom) and mostly-horizontal gestures are left to the browser.
 */

/** Share of the remaining distance covered per 60 Hz frame: higher = snappier, lower = floatier. */
const SMOOTHING = 0.16
const LINE_HEIGHT_PX = 16
/** Treat a scrollTop that differs from what we wrote by more than this as someone else scrolling. */
const EXTERNAL_TOLERANCE_PX = 2

const engines = new WeakMap<HTMLElement, InertiaScroll>()

class InertiaScroll {
  private target: number
  private current: number
  private frame = 0
  private lastTime = 0
  private written = -1
  /** True while we assign scrollTop ourselves (some engines fire "scroll" synchronously). */
  private writing = false

  constructor(
    private readonly element: HTMLElement,
    /** Never hand the wheel to a parent area, even at the edge (perfect-scrollbar's wheelPropagation: false). */
    private readonly contain: boolean,
  ) {
    this.target = this.current = element.scrollTop
    element.addEventListener('wheel', this.onWheel, { passive: false })
    element.addEventListener('scroll', this.onScroll, { passive: true })
  }

  destroy() {
    cancelAnimationFrame(this.frame)
    this.element.removeEventListener('wheel', this.onWheel)
    this.element.removeEventListener('scroll', this.onScroll)
  }

  private get max() {
    return Math.max(0, this.element.scrollHeight - this.element.clientHeight)
  }

  /** Glide to `top` (clamped). */
  scrollTo(top: number) {
    if (!this.frame) this.target = this.current = this.element.scrollTop
    this.target = clamp(top, 0, this.max)
    this.start()
  }

  private onWheel = (event: WheelEvent) => {
    if (event.defaultPrevented || event.ctrlKey) return
    if (Math.abs(event.deltaX) > Math.abs(event.deltaY)) return
    const max = this.max
    if (max <= 0) return

    const unit = event.deltaMode === 1 ? LINE_HEIGHT_PX : event.deltaMode === 2 ? this.element.clientHeight : 1
    if (!this.frame) this.target = this.current = this.element.scrollTop
    const next = clamp(this.target + event.deltaY * unit, 0, max)
    // Already at the edge in this direction: let a parent area (or the page) scroll instead.
    if (next === this.target) {
      if (this.contain) event.preventDefault()
      return
    }

    event.preventDefault() // also tells enclosing areas this wheel step is handled
    this.target = next
    this.start()
  }

  private onScroll = () => {
    if (this.writing) return
    const top = this.element.scrollTop
    if (this.frame && Math.abs(top - this.written) <= EXTERNAL_TOLERANCE_PX) return
    // Scrollbar drag, keyboard, focus or a programmatic jump: adopt it and stop gliding.
    cancelAnimationFrame(this.frame)
    this.frame = 0
    this.target = this.current = top
  }

  private start() {
    if (this.frame) return
    this.lastTime = performance.now()
    this.frame = requestAnimationFrame(this.tick)
  }

  private tick = (now: number) => {
    const elapsed = Math.min(64, now - this.lastTime)
    this.lastTime = now
    // Content can shrink or grow while we glide (e.g. a streaming answer).
    this.target = clamp(this.target, 0, this.max)

    const distance = this.target - this.current
    if (Math.abs(distance) < 0.5) {
      this.current = this.target
      this.write()
      this.frame = 0
      return
    }
    this.current += distance * (1 - Math.pow(1 - SMOOTHING, elapsed / (1000 / 60)))
    this.write()
    this.frame = requestAnimationFrame(this.tick)
  }

  private write() {
    this.writing = true
    this.element.scrollTop = this.current
    this.writing = false
    // Browsers round scrollTop; remember what it really became.
    this.written = this.element.scrollTop
  }
}

function clamp(value: number, min: number, max: number) {
  return Math.min(max, Math.max(min, value))
}

export function prefersReducedMotion() {
  return typeof window !== 'undefined' && typeof window.matchMedia === 'function' && window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

/** Enable inertia scrolling on `element`. Returns a cleanup function. */
export function attachInertiaScroll(element: HTMLElement, { contain = false } = {}): () => void {
  engines.get(element)?.destroy()
  const engine = new InertiaScroll(element, contain)
  engines.set(element, engine)
  return () => {
    engine.destroy()
    if (engines.get(element) === engine) engines.delete(element)
  }
}

/** Scroll `element` to `top`: a glide when it has inertia scrolling, otherwise an instant jump. */
export function smoothScrollTo(element: HTMLElement, top: number) {
  const engine = engines.get(element)
  if (engine && !prefersReducedMotion()) engine.scrollTo(top)
  else element.scrollTop = top
}

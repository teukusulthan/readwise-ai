import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { attachInertiaScroll, smoothScrollTo } from './inertia-scroll'

// A controllable animation clock: frames run only when the test says so.
let frames: FrameRequestCallback[] = []
let now = 0
function runFrames(count: number) {
  for (let i = 0; i < count && frames.length; i++) {
    now += 16.7
    const pending = frames
    frames = []
    pending.forEach((callback) => callback(now))
  }
}

function scrollBox({ height = 300, content = 1000 } = {}) {
  const element = document.createElement('div')
  let top = 0
  Object.defineProperty(element, 'clientHeight', { value: height })
  Object.defineProperty(element, 'scrollHeight', { value: content })
  Object.defineProperty(element, 'scrollTop', {
    get: () => top,
    set: (value: number) => {
      top = Math.max(0, Math.min(content - height, value))
      element.dispatchEvent(new Event('scroll'))
    },
  })
  document.body.appendChild(element)
  return element
}

function wheel(element: HTMLElement, deltaY: number, init: WheelEventInit = {}) {
  const event = new WheelEvent('wheel', { deltaY, cancelable: true, bubbles: true, ...init })
  element.dispatchEvent(event)
  return event
}

beforeEach(() => {
  frames = []
  now = 0
  vi.stubGlobal('requestAnimationFrame', (callback: FrameRequestCallback) => frames.push(callback))
  vi.stubGlobal('cancelAnimationFrame', () => {
    frames = []
  })
  vi.spyOn(performance, 'now').mockImplementation(() => now)
})

afterEach(() => {
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
  document.body.innerHTML = ''
})

describe('inertia scroll', () => {
  it('glides towards the wheel target instead of jumping, then settles exactly', () => {
    const element = scrollBox()
    attachInertiaScroll(element)
    expect(wheel(element, 200).defaultPrevented).toBe(true)
    expect(element.scrollTop).toBe(0) // nothing jumps

    runFrames(3)
    const midway = element.scrollTop
    expect(midway).toBeGreaterThan(0)
    expect(midway).toBeLessThan(200)

    runFrames(120)
    expect(element.scrollTop).toBe(200)
  })

  it('hands the wheel to the parent at an edge, unless told to contain it', () => {
    const element = scrollBox()
    attachInertiaScroll(element)
    expect(wheel(element, -100).defaultPrevented).toBe(false) // already at the top: page/parent scrolls

    const contained = scrollBox()
    attachInertiaScroll(contained, { contain: true })
    expect(wheel(contained, -100).defaultPrevented).toBe(true)
  })

  it('leaves pinch-zoom and events already handled by an inner area alone', () => {
    const element = scrollBox()
    attachInertiaScroll(element)
    expect(wheel(element, 100, { ctrlKey: true }).defaultPrevented).toBe(false)

    const inner = document.createElement('div')
    element.appendChild(inner)
    inner.addEventListener('wheel', (event) => event.preventDefault())
    wheel(inner, 100)
    runFrames(60)
    expect(element.scrollTop).toBe(0) // the inner area took it
  })

  it('adopts a scroll it did not start (scrollbar drag) and stops gliding', () => {
    const element = scrollBox()
    attachInertiaScroll(element)
    wheel(element, 400)
    runFrames(2)
    element.scrollTop = 50 // the user drags the scrollbar mid-glide
    runFrames(60)
    expect(element.scrollTop).toBe(50)
  })

  it('smoothScrollTo glides with inertia and jumps without it', () => {
    const smooth = scrollBox()
    attachInertiaScroll(smooth)
    smoothScrollTo(smooth, 700)
    expect(smooth.scrollTop).toBe(0)
    runFrames(200)
    expect(smooth.scrollTop).toBe(700) // clamped to the end

    const plain = scrollBox()
    smoothScrollTo(plain, 300)
    expect(plain.scrollTop).toBe(300)
  })
})

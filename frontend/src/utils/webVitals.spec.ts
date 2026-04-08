import { describe, it, expect, vi, beforeEach } from 'vitest'

// Mock PerformanceObserver
const mockObserve = vi.fn()
const mockDisconnect = vi.fn()

class MockPerformanceObserver {
  callback: (list: any) => void
  constructor(callback: (list: any) => void) {
    this.callback = callback
  }
  observe = mockObserve
  disconnect = mockDisconnect
}

vi.stubGlobal('PerformanceObserver', MockPerformanceObserver)

// Mock navigator.sendBeacon
vi.stubGlobal('navigator', {
  ...navigator,
  sendBeacon: vi.fn(),
})

// Mock performance.getEntriesByType
vi.spyOn(performance, 'getEntriesByType').mockReturnValue([
  {
    requestStart: 100,
    responseStart: 250,
  } as unknown as PerformanceEntry,
])

describe('webVitals', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should export initWebVitals function', async () => {
    const { initWebVitals } = await import('./webVitals')
    expect(typeof initWebVitals).toBe('function')
  })

  it('should call PerformanceObserver.observe when initialized', async () => {
    const { initWebVitals } = await import('./webVitals')
    initWebVitals()

    // LCP, FID, CLS, FCP 各调用一次 observe
    expect(mockObserve).toHaveBeenCalled()
  })

  it('should not throw when PerformanceObserver is undefined', async () => {
    const original = globalThis.PerformanceObserver
    // @ts-ignore
    globalThis.PerformanceObserver = undefined

    // Re-import to test the guard
    vi.resetModules()
    const { initWebVitals } = await import('./webVitals')
    expect(() => initWebVitals()).not.toThrow()

    globalThis.PerformanceObserver = original
  })
})

/**
 * Web Vitals 性能指标采集
 * 采集 LCP、FID、CLS、FCP、TTFB 等核心指标
 * 使用 PerformanceObserver API，无需额外依赖
 */

interface VitalMetric {
  name: string
  value: number
  rating: 'good' | 'needs-improvement' | 'poor'
}

type ReportCallback = (metric: VitalMetric) => void

const thresholds: Record<string, [number, number]> = {
  LCP: [2500, 4000],
  FID: [100, 300],
  CLS: [0.1, 0.25],
  FCP: [1800, 3000],
  TTFB: [800, 1800],
}

function getRating(name: string, value: number): VitalMetric['rating'] {
  const t = thresholds[name]
  if (!t) return 'good'
  if (value <= t[0]) return 'good'
  if (value <= t[1]) return 'needs-improvement'
  return 'poor'
}

function observeLCP(cb: ReportCallback) {
  try {
    const observer = new PerformanceObserver((list) => {
      const entries = list.getEntries()
      const last = entries[entries.length - 1] as PerformanceEntry
      if (last) {
        const value = last.startTime
        cb({ name: 'LCP', value, rating: getRating('LCP', value) })
      }
    })
    observer.observe({ type: 'largest-contentful-paint', buffered: true })
  } catch {
    // PerformanceObserver not supported
  }
}

function observeFID(cb: ReportCallback) {
  try {
    const observer = new PerformanceObserver((list) => {
      for (const entry of list.getEntries()) {
        const fidEntry = entry as PerformanceEventTiming
        const value = fidEntry.processingStart - fidEntry.startTime
        cb({ name: 'FID', value, rating: getRating('FID', value) })
      }
    })
    observer.observe({ type: 'first-input', buffered: true })
  } catch {
    // not supported
  }
}

function observeCLS(cb: ReportCallback) {
  try {
    let clsValue = 0
    const observer = new PerformanceObserver((list) => {
      for (const entry of list.getEntries()) {
        const layoutShift = entry as PerformanceEntry & { hadRecentInput: boolean; value: number }
        if (!layoutShift.hadRecentInput) {
          clsValue += layoutShift.value
        }
      }
      cb({ name: 'CLS', value: clsValue, rating: getRating('CLS', clsValue) })
    })
    observer.observe({ type: 'layout-shift', buffered: true })
  } catch {
    // not supported
  }
}

function observeFCP(cb: ReportCallback) {
  try {
    const observer = new PerformanceObserver((list) => {
      for (const entry of list.getEntries()) {
        if (entry.name === 'first-contentful-paint') {
          cb({ name: 'FCP', value: entry.startTime, rating: getRating('FCP', entry.startTime) })
        }
      }
    })
    observer.observe({ type: 'paint', buffered: true })
  } catch {
    // not supported
  }
}

function observeTTFB(cb: ReportCallback) {
  try {
    const nav = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming
    if (nav) {
      const value = nav.responseStart - nav.requestStart
      cb({ name: 'TTFB', value, rating: getRating('TTFB', value) })
    }
  } catch {
    // not supported
  }
}

/**
 * 初始化 Web Vitals 采集
 * 在生产环境自动上报到后端 /api/vitals（如果存在）
 */
export function initWebVitals() {
  if (typeof window === 'undefined' || typeof PerformanceObserver === 'undefined') return

  const report: ReportCallback = (metric) => {
    // 开发环境打印到控制台
    if (import.meta.env.DEV) {
      const color =
        metric.rating === 'good' ? 'green' : metric.rating === 'needs-improvement' ? 'orange' : 'red'
      console.log(
        `%c[WebVital] ${metric.name}: ${metric.value.toFixed(1)}ms (${metric.rating})`,
        `color: ${color}; font-weight: bold`
      )
    }

    // 生产环境可上报到后端（静默失败）
    if (import.meta.env.PROD) {
      try {
        navigator.sendBeacon?.(
          '/api/vitals',
          JSON.stringify({
            name: metric.name,
            value: metric.value,
            rating: metric.rating,
            url: location.pathname,
            timestamp: Date.now(),
          })
        )
      } catch {
        // 静默失败
      }
    }
  }

  observeLCP(report)
  observeFID(report)
  observeCLS(report)
  observeFCP(report)
  observeTTFB(report)
}

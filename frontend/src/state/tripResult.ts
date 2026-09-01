import { useCallback, useSyncExternalStore } from 'react'
import type { TripCheckResponse } from '../types/api'

const STORAGE_KEY = 'roadbuddy.tripResult'

/**
 * Session-scoped store for the most recent trip check.
 *
 * The result must survive a visit to the Risk Radar and a page refresh, but
 * must not outlive the browser tab: the trip form promises addresses are not
 * stored. sessionStorage matches that lifetime exactly.
 *
 * Snapshots are cached so useSyncExternalStore sees a stable reference;
 * re-parsing on every render would loop.
 */
let cachedRaw: string | null = null
let cachedValue: TripCheckResponse | null = null
const listeners = new Set<() => void>()

function readStorage(): string | null {
  try {
    return window.sessionStorage.getItem(STORAGE_KEY)
  } catch {
    // Private-mode browsers and blocked site data throw on access.
    return null
  }
}

/**
 * Read the stored trip result, reusing the previous object when unchanged.
 *
 * @returns The stored result, or null when absent or unparsable.
 */
function getSnapshot(): TripCheckResponse | null {
  const raw = readStorage()
  if (raw === cachedRaw) return cachedValue

  cachedRaw = raw
  if (raw === null) {
    cachedValue = null
    return cachedValue
  }
  try {
    cachedValue = JSON.parse(raw) as TripCheckResponse
  } catch {
    cachedValue = null
  }
  return cachedValue
}

/** @returns Always null; sessionStorage does not exist outside the browser. */
function getServerSnapshot(): TripCheckResponse | null {
  return null
}

/**
 * Subscribe to trip-result changes, including writes from other tabs.
 *
 * @param onStoreChange - Invoked when the stored result changes.
 * @returns An unsubscribe function.
 */
function subscribe(onStoreChange: () => void): () => void {
  listeners.add(onStoreChange)
  window.addEventListener('storage', onStoreChange)
  return () => {
    listeners.delete(onStoreChange)
    window.removeEventListener('storage', onStoreChange)
  }
}

function emit(): void {
  listeners.forEach((listener) => listener())
}

/**
 * Persist a trip check result for the rest of the browser session.
 *
 * @param result - The response to store.
 */
export function saveTripResult(result: TripCheckResponse): void {
  try {
    window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify(result))
  } catch {
    // Storage full or unavailable: this page still renders from memory.
  }
  emit()
}

/** Discard the stored result, used when starting another trip check. */
export function clearTripResult(): void {
  try {
    window.sessionStorage.removeItem(STORAGE_KEY)
  } catch {
    // Nothing to clear when storage is unavailable.
  }
  emit()
}

/**
 * Subscribe a component to the stored trip result.
 *
 * @returns The current result (null when none) and a function to clear it.
 */
export function useTripResult(): [TripCheckResponse | null, () => void] {
  const result = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot)
  const clear = useCallback(() => clearTripResult(), [])
  return [result, clear]
}

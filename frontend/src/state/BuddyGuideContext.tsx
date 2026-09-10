import { createContext, useCallback, useContext, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'

const ONBOARDING_SEEN_KEY = 'roadbuddy_onboarding_seen_v1'
const FINAL_STEP = 2

type BuddyGuideState = {
  isOpen: boolean
  currentStep: number
  openGuide: () => void
  closeGuide: () => void
  nextStep: () => void
  previousStep: () => void
}

const BuddyGuideContext = createContext<BuddyGuideState | null>(null)

function isFirstHomeVisit(pathname: string): boolean {
  if (pathname !== '/' || typeof window === 'undefined') return false
  try {
    return window.localStorage.getItem(ONBOARDING_SEEN_KEY) === null
  } catch {
    return true
  }
}

export function BuddyGuideProvider({ children }: { children: ReactNode }) {
  const { pathname } = useLocation()
  const navigate = useNavigate()
  const [isOpen, setIsOpen] = useState(() => isFirstHomeVisit(pathname))
  const [currentStep, setCurrentStep] = useState(0)

  const openGuide = useCallback(() => {
    navigate('/')
    setCurrentStep(0)
    setIsOpen(true)
  }, [navigate])

  const closeGuide = useCallback(() => {
    try {
      window.localStorage.setItem(ONBOARDING_SEEN_KEY, 'true')
    } catch {
      // Dismissal still works when browser storage is unavailable.
    }
    setIsOpen(false)
  }, [])

  const nextStep = useCallback(() => {
    if (currentStep === FINAL_STEP) closeGuide()
    else setCurrentStep((step) => Math.min(step + 1, FINAL_STEP))
  }, [currentStep, closeGuide])

  const previousStep = useCallback(() => {
    setCurrentStep((step) => Math.max(0, step - 1))
  }, [])

  const value = useMemo(() => ({
    isOpen, currentStep, openGuide, closeGuide, nextStep, previousStep,
  }), [isOpen, currentStep, openGuide, closeGuide, nextStep, previousStep])

  return <BuddyGuideContext.Provider value={value}>{children}</BuddyGuideContext.Provider>
}

export function useBuddyGuide(): BuddyGuideState {
  const guide = useContext(BuddyGuideContext)
  if (!guide) throw new Error('useBuddyGuide must be used inside BuddyGuideProvider')
  return guide
}

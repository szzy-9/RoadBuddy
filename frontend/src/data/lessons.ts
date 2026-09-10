export type Lesson = {
  id: 'wet' | 'night' | 'merge' | 'fatigue'
  topic: string
  shortLabel: string
  icon: string
  question: string
  options: string[]
  answerIndex: number
  why: string
  source: {
    name: string
    href: string
  }
}

const ROAD_TO_SOLO_DRIVING = {
  name: 'Road to Solo Driving',
  href: 'https://www.vicroads.vic.gov.au/-/media/files/formsandpublications/licences/english---road-to-solo-driving-handbook.ashx',
}

export const LESSONS: Lesson[] = [
  {
    id: 'wet',
    topic: 'Wet roads',
    shortLabel: 'Wet',
    icon: '☂',
    question: 'Rain on a 100 zone after dark. What changes first?',
    options: ['Your stopping distance', 'How far your lights reach', 'Nothing, if you stay at the limit'],
    answerIndex: 0,
    why: 'A wet surface stretches your braking distance before anything else about the drive changes. Your headlights reach the same distance wet or dry, so the gap you leave is the thing that has to grow.',
    source: ROAD_TO_SOLO_DRIVING,
  },
  {
    id: 'night',
    topic: 'Night driving',
    shortLabel: 'Night',
    icon: '☾',
    question: 'Driving after dark on an unfamiliar road. What should change first?',
    options: ['Your following distance', 'Your radio volume', 'Nothing, if you know the speed limit'],
    answerIndex: 0,
    why: 'At night you can only react to what your headlights reach. Increasing the gap in front buys back the time your eyes have lost.',
    source: ROAD_TO_SOLO_DRIVING,
  },
  {
    id: 'merge',
    topic: 'Freeway merging',
    shortLabel: 'Merge',
    icon: '↗',
    question: 'Joining a freeway where the on-ramp is short. What matters most?',
    options: ['Matching the speed of traffic before you merge', 'Merging as early as possible', 'Waiting for a very large gap'],
    answerIndex: 0,
    why: 'Most merge crashes involve a speed difference, not a gap that was too small. Matching traffic speed on the ramp means you slot in rather than cut in.',
    source: ROAD_TO_SOLO_DRIVING,
  },
  {
    id: 'fatigue',
    topic: 'Fatigue',
    shortLabel: 'Tired',
    icon: '◷',
    question: 'You are 20 minutes from home after a late shift and feel your eyes getting heavy. What works?',
    options: ['Pulling over for a short rest', 'Opening the window', 'Turning the music up'],
    answerIndex: 0,
    why: 'Air and noise wake you briefly but do nothing for the sleep debt behind the drowsiness. Only rest restores alertness.',
    source: {
      name: 'TAC — Tired driving',
      href: 'https://www.tac.vic.gov.au/road-safety/staying-safe/tired-driving',
    },
  },
]

export const COMPLETED_TOPICS_KEY = 'roadbuddy.completedTopics'

export function readCompletedTopics(): string[] {
  try {
    const stored = window.localStorage.getItem(COMPLETED_TOPICS_KEY)
    const parsed: unknown = stored ? JSON.parse(stored) : []
    if (!Array.isArray(parsed)) return []
    return [...new Set(parsed.filter((topic): topic is string => (
      typeof topic === 'string' && LESSONS.some((lesson) => lesson.topic === topic)
    )))]
  } catch {
    return []
  }
}

export function addCompletedTopics(topics: string[]): void {
  try {
    const validTopics = topics.filter((topic) => LESSONS.some((lesson) => lesson.topic === topic))
    const completed = [...new Set([...readCompletedTopics(), ...validTopics])]
    window.localStorage.setItem(COMPLETED_TOPICS_KEY, JSON.stringify(completed))
  } catch {
    // Practice still works when browser storage is unavailable.
  }
}

export function clearCompletedTopics(): void {
  try {
    window.localStorage.removeItem(COMPLETED_TOPICS_KEY)
  } catch {
    // Clearing is best effort; Me still resets its current view.
  }
}

import { LESSONS } from './lessons'
import type { Lesson } from './lessons'
import type { RiskFactor, TripCheckResponse } from '../types/api'

export type BuddyIntent = Lesson['id'] | 'trip' | 'prediction' | 'unknown'

export type BuddyAnswer = {
  intent: BuddyIntent | 'road-rules' | 'p1'
  icon: string
  heading: string
  body: string
  sources: Lesson['source'][]
  factors: Array<{ type: RiskFactor['type']; icon: string; label: string }>
  actions: Array<{ to: '/trip' | '/radar'; icon: string; label: string }>
}

const PREDICTION_PHRASES = [
  'will i crash',
  'will there be a crash',
  'chance of crash',
  'probability of crash',
  'predict a crash',
  'crash happen',
  'will an accident happen',
]

// Word boundaries keep "tonight" in trip, not night, and "train" out of rain.
const INTENT_KEYWORDS: Array<{ intent: BuddyIntent; pattern: RegExp }> = [
  { intent: 'fatigue', pattern: /\b(tired|fatigue|sleepy|drowsy)\b/ },
  { intent: 'wet', pattern: /\b(rain|raining|wet)\b/ },
  { intent: 'night', pattern: /\b(night|dark|darkness)\b/ },
  { intent: 'merge', pattern: /\b(merge|merging|freeway|on-ramp|ramp)\b/ },
  { intent: 'trip', pattern: /\b(trip|route|this drive|my drive|tonight)\b/ },
]

export function classifyBuddyQuestion(
  question: string,
  trip: TripCheckResponse | null = null,
): BuddyIntent {
  const normalized = question.trim().toLowerCase()
  if (PREDICTION_PHRASES.some((phrase) => normalized.includes(phrase))) return 'prediction'

  for (const { intent, pattern } of INTENT_KEYWORDS) {
    if (pattern.test(normalized)) return intent === 'trip' && !trip ? 'unknown' : intent
  }
  return 'unknown'
}

const TRIP_INDICATORS: Record<RiskFactor['type'], { icon: string; label: string }> = {
  rain: { icon: '☂', label: 'Wet' },
  after_dark: { icon: '☾', label: 'Night' },
  high_speed_zone: { icon: '◎', label: 'High speed' },
  significant_crash_history: { icon: '◈', label: 'Crash history' },
}

const handbookSource = LESSONS.find((lesson) => lesson.source.name === 'Road to Solo Driving')?.source

export function getBuddyAnswer(
  intent: BuddyIntent,
  trip: TripCheckResponse | null = null,
): BuddyAnswer {
  if (intent === 'prediction') {
    return {
      intent,
      icon: 'shield',
      heading: "Can't predict crashes",
      body: 'RoadBuddy can show recorded history instead.',
      sources: [],
      factors: [],
      actions: [{ to: '/radar', icon: '◈', label: 'Radar' }],
    }
  }

  if (intent === 'trip' && trip) {
    // Read only the response's reported factors; never infer conditions from
    // the clock, route, concern level or missing data.
    const types = [...new Set(trip.factors.map((factor) => factor.type))]
    return {
      intent,
      icon: 'route',
      heading: 'This trip',
      body: 'These are the indicators from your latest trip check.',
      sources: [],
      factors: types.flatMap((type) => (
        TRIP_INDICATORS[type] ? [{ type, ...TRIP_INDICATORS[type] }] : []
      )),
      actions: [
        { to: '/trip', icon: '→', label: 'Trip' },
        ...(types.includes('significant_crash_history')
          ? [{ to: '/radar' as const, icon: '→', label: 'Radar' }]
          : []),
      ],
    }
  }

  const lesson = LESSONS.find((item) => item.id === intent)
  if (lesson) {
    return {
      intent,
      icon: lesson.icon,
      heading: lesson.topic,
      body: lesson.why,
      sources: [lesson.source],
      factors: [],
      actions: [],
    }
  }

  return {
    intent: 'unknown',
    icon: 'book',
    heading: 'Not in my sources',
    body: 'Check Road to Solo Driving.',
    sources: handbookSource ? [handbookSource] : [],
    factors: [],
    actions: [],
  }
}

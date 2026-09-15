import type { BuddyAnswer } from './buddyAnswers'

export type PreparedQuestion = {
  id: string
  topic: 'night' | 'wet' | 'merge' | 'fatigue' | 'road-rules' | 'p1'
  question: string
} & (
  | { requiresTripContext: false; answer: string; sources: BuddyAnswer['sources'] }
  | { requiresTripContext: true; answer?: never; sources?: never }
)

// Contextual questions are catalogue entries only; they are not available to ask yet.
export const PREPARED_QUESTIONS: PreparedQuestion[] = [
  {
    "id": "night-01",
    "topic": "night",
    "question": "Why is night driving harder?",
    "answer": "In the dark, **reduced visibility** makes vehicles and other road users less easy to spot. Judging how far away they are can also be difficult when their lights affect your view, especially on roads without much street lighting.\n\nGive the road your full attention and **use your headlights correctly**. Where possible, arrange your travel so you are not behind the wheel during your usual sleeping hours.",
    "sources": [
      {
        "name": "Transport Accident Commission (TAC) — Drivers: Night driving",
        "href": "https://www.tac.vic.gov.au/road-safety/road-users/drivers"
      },
      {
        "name": "Transport Victoria — Safe driving tips",
        "href": "https://transport.vic.gov.au/road-and-active-transport/road-rules-and-safety/safe-driving-tips"
      }
    ],
    "requiresTripContext": false
  },
  {
    "id": "night-02",
    "topic": "night",
    "question": "How can I manage glare from headlights?",
    "answer": "When oncoming lights dazzle you, direct your gaze towards the **left edge of the road** and stay towards the left within your lane. Reduce your speed if needed; if you cannot see well enough, **stop somewhere safe** and let your vision recover before moving on.\n\nYour own lights matter too. Victorian rules require **low beam within 200 metres** of a vehicle ahead, including both oncoming traffic and vehicles you are following.",
    "sources": [
      {
        "name": "Transport Victoria — Headlights and high beams",
        "href": "https://transport.vic.gov.au/road-and-active-transport/road-rules-and-safety/headlights-and-high-beams"
      },
      {
        "name": "Transport Accident Commission (TAC) — Drivers: Night driving",
        "href": "https://www.tac.vic.gov.au/road-safety/road-users/drivers"
      }
    ],
    "requiresTripContext": false
  },
  {
    "id": "night-03",
    "topic": "night",
    "question": "When should I use high beams?",
    "answer": "Use high beam for a longer view of the road at night only when it will **not dazzle other road users**. Thick fog or mist can reflect that light back towards you and reduce what you can see.\n\nIn Victoria, a vehicle ahead that is **less than 200 metres away** means you must select **low beam**. This applies whether you are following it or it is coming towards you.",
    "sources": [
      {
        "name": "Transport Victoria — Headlights and high beams",
        "href": "https://transport.vic.gov.au/road-and-active-transport/road-rules-and-safety/headlights-and-high-beams"
      },
      {
        "name": "Transport Accident Commission (TAC) — Drivers",
        "href": "https://www.tac.vic.gov.au/road-safety/road-users/drivers"
      }
    ],
    "requiresTripContext": false
  },
  {
    "id": "night-04",
    "topic": "night",
    "question": "What should I do if I can’t see the road clearly?",
    "answer": "**Slow down** to suit what you can actually see, even when the posted limit allows a higher speed. If you cannot see enough of the road to continue safely, **pull over somewhere safe**. After headlight glare, allow your vision to recover before setting off again.\n\nTurn your headlights on when visibility drops. In hazardous conditions, choose **low beam**; daytime running lights alone are not enough.",
    "sources": [
      {
        "name": "Transport Victoria — Safe driving tips",
        "href": "https://transport.vic.gov.au/road-and-active-transport/road-rules-and-safety/safe-driving-tips"
      },
      {
        "name": "Transport Victoria — Headlights and high beams",
        "href": "https://transport.vic.gov.au/road-and-active-transport/road-rules-and-safety/headlights-and-high-beams"
      },
      {
        "name": "Transport Victoria — Snow and winter driving",
        "href": "https://transport.vic.gov.au/road-and-active-transport/road-rules-and-safety/snow-and-winter-driving"
      }
    ],
    "requiresTripContext": false
  },
  {
    "id": "night-trip",
    "topic": "night",
    "question": "Why was night driving flagged for this trip?",
    "requiresTripContext": true
  },
  {
    "id": "wet-01",
    "topic": "wet",
    "question": "Why do wet roads increase driving risk?",
    "answer": "Rain creates two problems at once: **less grip** between tyres and road, and a poorer view of traffic and hazards. With less grip, a vehicle needs more distance to stop and is more likely to skid or go out of control.\n\nAllow for both by **slowing down** and increasing the space ahead of you. Switch on your headlights whenever rain makes it harder to see.",
    "sources": [
      {
        "name": "Transport Victoria — Snow and winter driving",
        "href": "https://transport.vic.gov.au/road-and-active-transport/road-rules-and-safety/snow-and-winter-driving"
      },
      {
        "name": "Transport Accident Commission (TAC) — Drivers: Weather conditions",
        "href": "https://www.tac.vic.gov.au/road-safety/road-users/drivers"
      }
    ],
    "requiresTripContext": false
  },
  {
    "id": "wet-02",
    "topic": "wet",
    "question": "How should I adjust my speed and following distance in the rain?",
    "answer": "Allow **at least a four-second gap** in rain or fog, rather than the usual three seconds recommended by Transport Victoria. The extra space allows for the longer stopping distance on a wet surface.\n\nChoose a **lower speed that suits the conditions**, even if it is below the limit. Use the accelerator and brakes gently so changes in speed do not unnecessarily reduce tyre grip.",
    "sources": [
      {
        "name": "Transport Victoria — Safe driving tips",
        "href": "https://transport.vic.gov.au/road-and-active-transport/road-rules-and-safety/safe-driving-tips"
      },
      {
        "name": "Transport Victoria — Snow and winter driving",
        "href": "https://transport.vic.gov.au/road-and-active-transport/road-rules-and-safety/snow-and-winter-driving"
      }
    ],
    "requiresTripContext": false
  },
  {
    "id": "wet-03",
    "topic": "wet",
    "question": "What should I do if my car starts aquaplaning?",
    "answer": "If water lifts your tyres away from the road, you are aquaplaning. While waiting for contact to return, **hold the steering straight and steady**, gradually reduce pressure on the accelerator and **avoid braking**.\n\nLower your chances of this happening by keeping your tyres in good condition and **slowing down in wet weather**. Steer clear of large puddles where possible, and avoid abrupt turns or braking.",
    "sources": [
      {
        "name": "RACV — Why it's unsafe to drive through water on the road",
        "href": "https://www.racv.com.au/royalauto/transport/cars/the-dangers-of-driving-in-flood-water.html"
      },
      {
        "name": "Transport Victoria — Snow and winter driving",
        "href": "https://transport.vic.gov.au/road-and-active-transport/road-rules-and-safety/snow-and-winter-driving"
      }
    ],
    "requiresTripContext": false
  },
  {
    "id": "wet-04",
    "topic": "wet",
    "question": "What should I do if heavy rain makes it hard to see?",
    "answer": "When rain obscures the road, **reduce your speed** and leave more room ahead. If you can no longer see clearly enough to drive, **stop in a safe place** and wait for better conditions. **Never enter floodwater**.\n\nHelp other drivers see you by switching on low-beam headlights. Use your wipers for rain on the glass and your demister or air conditioning as needed to keep the windscreen clear.",
    "sources": [
      {
        "name": "Transport Accident Commission (TAC) — Drivers: Weather conditions",
        "href": "https://www.tac.vic.gov.au/road-safety/road-users/drivers"
      },
      {
        "name": "Transport Victoria — Snow and winter driving",
        "href": "https://transport.vic.gov.au/road-and-active-transport/road-rules-and-safety/snow-and-winter-driving"
      },
      {
        "name": "Transport Victoria — Safe driving tips",
        "href": "https://transport.vic.gov.au/road-and-active-transport/road-rules-and-safety/safe-driving-tips"
      }
    ],
    "requiresTripContext": false
  },
  {
    "id": "wet-trip",
    "topic": "wet",
    "question": "Why were wet conditions flagged for this trip?",
    "requiresTripContext": true
  },
  {
    "id": "merge-01",
    "topic": "merge",
    "question": "How do I merge safely onto a freeway?",
    "answer": "Join freeway traffic through a **safe gap**, remembering that vehicles already on the freeway have priority. The entrance ramp gives you room to build towards their speed, but you must **stay within the speed limit**.\n\nSignal your intention early. While checking mirrors and blind spots, look for an opening you can enter smoothly. Keep watching nearby vehicles as you move into the freeway lane.",
    "sources": [
      {
        "name": "Transport Victoria — Freeway driving rules in Victoria",
        "href": "https://transport.vic.gov.au/road-and-active-transport/road-rules-and-safety/freeways"
      },
      {
        "name": "Transport Victoria — Merging lanes",
        "href": "https://transport.vic.gov.au/road-and-active-transport/road-rules-and-safety/merging-lanes"
      }
    ],
    "requiresTripContext": false
  },
  {
    "id": "merge-02",
    "topic": "merge",
    "question": "How do I choose a safe gap in traffic?",
    "answer": "A gap is not safe if entering it would make someone else **brake or take avoiding action**. Begin looking early on the ramp so you have time to adjust your speed for a suitable opening.\n\nKeep track of traffic alongside and behind you through your mirrors and a **head check**. Motorcycles can be hidden in blind spots, so include them in your checks before moving across.",
    "sources": [
      {
        "name": "Transport Victoria — Freeway driving rules in Victoria",
        "href": "https://transport.vic.gov.au/road-and-active-transport/road-rules-and-safety/freeways"
      },
      {
        "name": "VicRoads — Drive Test: Gap Selection",
        "href": "https://www.vicroads.vic.gov.au/~/media/files/formsandpublications/licences/driving_instructors_drive_test_criteria.ashx"
      }
    ],
    "requiresTripContext": false
  },
  {
    "id": "merge-03",
    "topic": "merge",
    "question": "What if I reach the end of the merging lane without a safe gap?",
    "answer": "Reaching the end of a lane does not give you priority. When crossing a marked line, **give way to traffic in the lane you want to enter**; do not squeeze in and make another driver brake or avoid you.\n\nWhile merging space remains, adjust your speed and keep searching for a safe opening. On a freeway ramp, try to **keep moving unless traffic is very slow or congested**: starting from rest makes matching freeway speeds harder.",
    "sources": [
      {
        "name": "Transport Victoria — Merging lanes",
        "href": "https://transport.vic.gov.au/road-and-active-transport/road-rules-and-safety/merging-lanes"
      },
      {
        "name": "VicRoads — Freeways",
        "href": "https://www-sit10-b.vicroads.vic.gov.au/safety-and-road-rules/road-rules/a-to-z-of-road-rules/freeways"
      }
    ],
    "requiresTripContext": false
  },
  {
    "id": "merge-04",
    "topic": "merge",
    "question": "Who gives way when two lanes merge?",
    "answer": "Look at the **lane markings** to work out priority. Crossing a line into an occupied lane means **you must give way**, including when your own lane is ending.\n\nWhere two streams become one without a lane line separating them, the zip-merge rule applies: the driver behind gives way to the vehicle **further ahead**, even if it is only slightly ahead. Do not assume an alternating turn-taking arrangement without checking the markings.",
    "sources": [
      {
        "name": "Transport Victoria — Merging lanes",
        "href": "https://transport.vic.gov.au/road-and-active-transport/road-rules-and-safety/merging-lanes"
      }
    ],
    "requiresTripContext": false
  },
  {
    "id": "merge-05",
    "topic": "merge",
    "question": "What’s the difference between merging and changing lanes?",
    "answer": "The key difference is whether you **cross a marked lane line**. If you do, you are changing lanes and must give way to traffic already in the destination lane. A freeway entry with a marked line works this way too.\n\nA **zip merge** is where two streams of traffic join without a separating lane marking at that point. Priority goes to the vehicle further ahead, even slightly; **the driver behind gives way**.",
    "sources": [
      {
        "name": "Transport Victoria — Merging lanes",
        "href": "https://transport.vic.gov.au/road-and-active-transport/road-rules-and-safety/merging-lanes"
      },
      {
        "name": "Transport Victoria — Freeway driving rules in Victoria",
        "href": "https://transport.vic.gov.au/road-and-active-transport/road-rules-and-safety/freeways"
      }
    ],
    "requiresTripContext": false
  },
  {
    "id": "tired-01",
    "topic": "fatigue",
    "question": "What are the early signs of driver fatigue?",
    "answer": "Fatigue can show up in your driving before you nod off: you might wander across your lane, struggle to hold a steady speed or respond late at an intersection. **Poor concentration** or gaps in your memory of the recent drive are warnings too.\n\nNotice physical changes such as repeated yawning, heavy eyes or blurred vision, as well as a wandering mind. **Act on these signs early**; you do not need to be falling asleep for fatigue to affect your driving.",
    "sources": [
      {
        "name": "Transport Victoria — Fatigue and driving",
        "href": "https://transport.vic.gov.au/road-and-active-transport/road-rules-and-safety/fatigue-and-driving"
      },
      {
        "name": "Transport Accident Commission (TAC) — Tired driving",
        "href": "https://www.tac.vic.gov.au/road-safety/staying-safe/tired-driving"
      }
    ],
    "requiresTripContext": false
  },
  {
    "id": "tired-02",
    "topic": "fatigue",
    "question": "What should I do if I feel sleepy while driving?",
    "answer": "Make **stopping somewhere safe** your next priority when you feel sleepy. Pushing yourself to stay awake does not resolve fatigue; recovering requires sleep.\n\nOnce stopped, a **15–20 minute powernap** may give your alertness a temporary lift. Still feeling tired means **do not resume driving**. Where possible, let a well-rested driver take over or find another way to travel.",
    "sources": [
      {
        "name": "Transport Victoria — Fatigue and driving",
        "href": "https://transport.vic.gov.au/road-and-active-transport/road-rules-and-safety/fatigue-and-driving"
      },
      {
        "name": "Transport Accident Commission (TAC) — Tired driving",
        "href": "https://www.tac.vic.gov.au/road-safety/staying-safe/tired-driving"
      }
    ],
    "requiresTripContext": false
  },
  {
    "id": "tired-03",
    "topic": "fatigue",
    "question": "Do coffee, loud music or an open window help with fatigue?",
    "answer": "Coffee, music and fresh air can give a brief feeling of alertness without dealing with the tiredness underneath. **Do not treat that feeling as proof you can drive safely**.\n\nDrowsiness calls for a safe stop and a **15–20 minute powernap**, rather than another way to keep yourself awake. If tiredness remains, stay off the road: sleep is needed to recover from fatigue.",
    "sources": [
      {
        "name": "Transport Accident Commission (TAC) — Driver Fatigue",
        "href": "https://www.tac.vic.gov.au/__data/assets/pdf_file/0010/735436/SSC23_ENTRY_BRIEF_DRIVERFATIGUE-2_compressed.pdf"
      },
      {
        "name": "Transport Victoria — Fatigue and driving",
        "href": "https://transport.vic.gov.au/road-and-active-transport/road-rules-and-safety/fatigue-and-driving"
      }
    ],
    "requiresTripContext": false
  },
  {
    "id": "tired-04",
    "topic": "fatigue",
    "question": "How should I plan breaks for a longer trip?",
    "answer": "Build rest stops into your plan before leaving, and begin the journey well rested. Transport Victoria recommends **15–30 minute breaks at least every two hours**, with an earlier stop whenever you feel tired. Use the stop to leave the car, stretch and walk a little.\n\nAlso plan the total time at the wheel: Transport Victoria recommends **no more than eight hours of driving in 24 hours** for long-distance travel. Sharing the driving can help, provided the other driver is rested and fit to take over.",
    "sources": [
      {
        "name": "Transport Victoria — Fatigue and driving",
        "href": "https://transport.vic.gov.au/road-and-active-transport/road-rules-and-safety/fatigue-and-driving"
      },
      {
        "name": "Transport Accident Commission (TAC) — Tired driving",
        "href": "https://www.tac.vic.gov.au/road-safety/staying-safe/tired-driving"
      }
    ],
    "requiresTripContext": false
  },
  {
    "id": "tired-05",
    "topic": "fatigue",
    "question": "Why can driving at night make fatigue worse?",
    "answer": "Night travel can put you behind the wheel during your normal sleep time, with fatigue risk especially high in the **early morning hours**. Being tired reduces your ability to focus and react promptly and safely.\n\nWhere possible, plan travel outside your usual sleeping hours. If night driving is necessary, start well rested and **stop when drowsiness appears**.",
    "sources": [
      {
        "name": "Transport Victoria — Fatigue and driving",
        "href": "https://transport.vic.gov.au/road-and-active-transport/road-rules-and-safety/fatigue-and-driving"
      },
      {
        "name": "Transport Accident Commission (TAC) — Tired driving",
        "href": "https://www.tac.vic.gov.au/road-safety/staying-safe/tired-driving"
      }
    ],
    "requiresTripContext": false
  },
  {
    "id": "road-rules-01",
    "topic": "road-rules",
    "question": "Who gives way at an intersection?",
    "answer": "The give-way rule depends on the **signs, traffic lights and layout** of the intersection.\n\nIf there are no lights, signs or road markings controlling the intersection, give way to traffic approaching from your **right**. If you are turning right, you must also wait for oncoming vehicles travelling straight ahead or turning left.\n\nAt a **T-intersection**, a driver coming from the road that ends must give way to traffic on the continuing road. When turning, also watch for and give way to pedestrians crossing the road you are entering.",
    "sources": [
      {
        "name": "Transport Victoria — Intersections and giving way",
        "href": "https://transport.vic.gov.au/road-and-active-transport/road-rules-and-safety/intersections-and-giving-way"
      }
    ],
    "requiresTripContext": false
  },
  {
    "id": "road-rules-02",
    "topic": "road-rules",
    "question": "How do I use a roundabout correctly?",
    "answer": "Before entering a roundabout, check for traffic already circulating and **give way before entering** when required. You must also give way to a tram entering or approaching the roundabout.\n\nYour indicator should show where you intend to go: signal **left** for a left turn and **right** for a right turn. When travelling straight ahead, you normally do not signal on approach. Where practical, signal left as you leave the roundabout.\n\nAt a multi-lane roundabout, follow the **lane arrows and signs** and stay in an appropriate lane for the direction you are travelling.",
    "sources": [
      {
        "name": "Transport Victoria — Roundabouts",
        "href": "https://transport.vic.gov.au/road-and-active-transport/road-rules-and-safety/roundabouts"
      }
    ],
    "requiresTripContext": false
  },
  {
    "id": "road-rules-03",
    "topic": "road-rules",
    "question": "When do I need to indicate?",
    "answer": "Use your indicators before you **turn, change lanes, merge or move out from a stationary position** so other road users have warning of what you intend to do.\n\nGive the signal early enough to be useful, but not so early that it could confuse someone about where you plan to turn. When moving out from a parked or stationary position at the side of the road, you must indicate for **at least five seconds** before moving.\n\nAt roundabouts, the signal you use depends on whether you are turning left, right or travelling straight ahead.",
    "sources": [
      {
        "name": "VicRoads — Road to Solo Driving: Signalling your moves",
        "href": "https://www.vicroads.vic.gov.au/-/media/files/formsandpublications/licences/english---road-to-solo-driving-handbook.ashx"
      },
      {
        "name": "Transport Victoria — Roundabouts",
        "href": "https://transport.vic.gov.au/road-and-active-transport/road-rules-and-safety/roundabouts"
      },
      {
        "name": "Transport Victoria — Merging lanes",
        "href": "https://transport.vic.gov.au/road-and-active-transport/road-rules-and-safety/merging-lanes"
      }
    ],
    "requiresTripContext": false
  },
  {
    "id": "road-rules-04",
    "topic": "road-rules",
    "question": "What should I do when traffic lights aren’t working?",
    "answer": "If traffic lights are not operating or are flashing yellow, **slow down and approach the intersection carefully**.\n\nIn Victoria, you must then follow the give-way rules that apply at an intersection controlled by a **stop or give-way sign or line**. Check the signs, markings and other traffic before entering, and be prepared to stop when required.\n\nDo not assume that you have priority simply because another driver appears to be waiting. **Proceed only when it is safe**.",
    "sources": [
      {
        "name": "Transport Victoria — Traffic lights",
        "href": "https://transport.vic.gov.au/road-and-active-transport/road-rules-and-safety/traffic-lights"
      },
      {
        "name": "Transport Victoria — Intersections and giving way",
        "href": "https://transport.vic.gov.au/road-and-active-transport/road-rules-and-safety/intersections-and-giving-way"
      }
    ],
    "requiresTripContext": false
  },
  {
    "id": "road-rules-05",
    "topic": "road-rules",
    "question": "How do I safely pass a cyclist?",
    "answer": "Only overtake a bicycle rider when you have **enough space and a clear view ahead**.\n\nIn Victoria, leave at least **1 metre** between your vehicle and the bicycle where the relevant speed is 60 km/h or lower. Where it is above 60 km/h, the minimum passing distance is **1.5 metres**.\n\nIf there is not enough room, slow down and wait for a safer opportunity. After passing, make sure you are clearly ahead of the rider before moving back across their path.",
    "sources": [
      {
        "name": "Transport Victoria — Driving with bike riders",
        "href": "https://transport.vic.gov.au/road-and-active-transport/active-transport/bicycles/driving-with-bike-riders"
      }
    ],
    "requiresTripContext": false
  },
  {
    "id": "p1-01",
    "topic": "p1",
    "question": "What restrictions apply to me as a P1 driver?",
    "answer": "Victorian P1 drivers have several extra conditions while gaining driving experience. You need to display **red P plates** at the front and rear of the vehicle and maintain a **0.00 BAC** whenever you drive.\n\nP1 drivers also have additional restrictions covering **peer passengers, electronic devices, towing and prohibited vehicles**.\n\nIf your licence has an `A` condition because you completed your test in an automatic vehicle, you are restricted to driving automatic vehicles until that condition is removed.",
    "sources": [
      {
        "name": "Transport Victoria — Learner and probationary driver road rules",
        "href": "https://transport.vic.gov.au/road-and-active-transport/road-rules-and-safety/learner-and-probationary-driver-road-rules"
      },
      {
        "name": "Transport Victoria — Alcohol and driving laws",
        "href": "https://transport.vic.gov.au/road-and-active-transport/road-rules-and-safety/alcohol-drugs-and-driving/alcohol-and-driving-laws"
      }
    ],
    "requiresTripContext": false
  },
  {
    "id": "p1-02",
    "topic": "p1",
    "question": "Can I use my phone for navigation?",
    "answer": "**Yes, but only under strict conditions.** As a Victorian P1 driver, you can use navigation on a phone that is properly mounted, as long as the navigation is **set up before the journey starts**.\n\nWhile driving, you must **not touch the mounted phone or use voice controls** to operate it. This restriction still applies when you are temporarily stopped in traffic or at traffic lights. If you need to enter a new destination or change the setup, pull over and park first.\n\nA loose or unmounted phone is treated differently: it cannot have an ongoing navigation activity while you drive, even if you started the navigation before leaving.",
    "sources": [
      {
        "name": "Transport Victoria — Device rules for new and young drivers and motorcyclists",
        "href": "https://transport.vic.gov.au/road-and-active-transport/road-rules-and-safety/mobile-phones-and-devices/device-rules-for-new-and-young-drivers-and-motorcyclists"
      },
      {
        "name": "Transport Victoria — Learner and probationary driver road rules",
        "href": "https://transport.vic.gov.au/road-and-active-transport/road-rules-and-safety/learner-and-probationary-driver-road-rules"
      }
    ],
    "requiresTripContext": false
  },
  {
    "id": "p1-03",
    "topic": "p1",
    "question": "Who can I carry as a passenger?",
    "answer": "A Victorian P1 driver is generally limited to **one peer passenger** at a time.\n\nFor this restriction, a peer passenger is someone aged **16 to under 22**. Your spouse or domestic partner, sibling or step-sibling does not count as a peer passenger under this rule.\n\nSome exemptions can apply in particular circumstances, so check the official rules if your passenger situation falls outside the usual case.",
    "sources": [
      {
        "name": "Transport Victoria — Learner and probationary driver road rules",
        "href": "https://transport.vic.gov.au/road-and-active-transport/road-rules-and-safety/learner-and-probationary-driver-road-rules"
      }
    ],
    "requiresTripContext": false
  },
  {
    "id": "p1-04",
    "topic": "p1",
    "question": "Can I drive any car on my P1 licence?",
    "answer": "**No.** Some vehicles are restricted for Victorian probationary drivers.\n\nBefore driving an unfamiliar vehicle, check it in the official probationary vehicle database. A vehicle may be restricted if it is listed as **Banned**, has a power-to-mass ratio above **130 kW per tonne**, or has certain engine modifications that increase its performance.\n\nLimited exemptions exist for particular situations, but do not assume an exemption applies unless you meet the official requirements.",
    "sources": [
      {
        "name": "Transport Victoria — Vehicles for probationary drivers",
        "href": "https://transport.vic.gov.au/road-and-active-transport/registration-and-licensing/licences/probationary-licence/vehicles-for-probationary-drivers"
      }
    ],
    "requiresTripContext": false
  },
  {
    "id": "p1-05",
    "topic": "p1",
    "question": "Where can I check the official P1 rules?",
    "answer": "For Victorian P1 requirements, start with **Transport Victoria's learner and probationary driver rules**. This covers the main licence conditions and restrictions that apply to P1 drivers.\n\nFor questions about phones and navigation, use the dedicated **device rules for new and young drivers**. If you are unsure whether a particular vehicle is permitted, check the official **probationary vehicle database**.\n\nRoad and licence rules can change. RoadBuddy can help explain them in simpler language, but the linked Victorian Government information should be used when you need the **latest official rule**.",
    "sources": [
      {
        "name": "Transport Victoria — Learner and probationary driver road rules",
        "href": "https://transport.vic.gov.au/road-and-active-transport/road-rules-and-safety/learner-and-probationary-driver-road-rules"
      },
      {
        "name": "Transport Victoria — Device rules for new and young drivers and motorcyclists",
        "href": "https://transport.vic.gov.au/road-and-active-transport/road-rules-and-safety/mobile-phones-and-devices/device-rules-for-new-and-young-drivers-and-motorcyclists"
      },
      {
        "name": "Transport Victoria — Vehicles for probationary drivers",
        "href": "https://transport.vic.gov.au/road-and-active-transport/registration-and-licensing/licences/probationary-licence/vehicles-for-probationary-drivers"
      }
    ],
    "requiresTripContext": false
  }
]

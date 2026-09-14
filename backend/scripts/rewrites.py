# Rewritten distractors for every question with status == "review".
# Key: question_id -> (correct_text_or_None, [distractor, distractor, distractor])
# correct_text_or_None: None keeps the workbook's existing correct-option text.
# Each distractor is intended to be plausible to someone who has not learned the
# point, rather than self-evidently absurd.

REWRITES = {
    # --- night_driving ---------------------------------------------------
    "NIGHT_Q003": (None, [
        "To work out where the next speed-limit sign will be",
        "Because looking further ahead makes oncoming headlights less dazzling",
        "To keep the vehicle centred between the lane markings",
    ]),
    "NIGHT_Q004": (None, [
        "The posted limit, since it already allows for night conditions",
        "The same speed as the vehicle in front, so the gap stays constant",
        "Slightly faster, so less time is spent on the dark section",
    ]),
    "NIGHT_Q005": (None, [
        "How quickly the brakes can slow the vehicle",
        "How much grip the tyres have on the road surface",
        "How far the vehicle travels while you react",
    ]),
    "NIGHT_Q006": (None, [
        "Vehicles generally travel faster on unlit roads",
        "Unlit roads usually carry a higher speed limit",
        "Tyres lose grip as the air temperature drops",
    ]),
    "NIGHT_Q007": (None, [
        "Switch to high beam and hold your current speed",
        "Move towards the centre line to see further around the bend",
        "Brake firmly once you are already in the bend",
    ]),
    "NIGHT_Q008": (None, [
        "Flash your own high beam so the other driver dips theirs",
        "Close one eye until the vehicle has passed",
        "Speed up so you are past the bright lights sooner",
    ]),

    # --- wet_weather -----------------------------------------------------
    "WET_Q003": (None, [
        "It allows you to maintain a higher speed safely",
        "It prevents aquaplaning entirely",
        "It means braking can be left later and applied harder",
    ]),
    "WET_Q004": (None, [
        "Grip, but not visibility, because the wipers restore your view",
        "Visibility, but not grip, because tyres are designed to clear water",
        "Neither, provided you stay under the posted limit",
    ]),
    "WET_Q005": (None, [
        "Turn on the hazard lights and continue at the same speed",
        "Slow to a crawl and stay in the left lane until it eases",
        "Stop in the left lane and wait there with your lights on",
    ]),
    "WET_Q006": (None, [
        "Light rain washes the surface and improves grip",
        "Grip is only reduced once water begins to pool on the road",
        "Modern tyres remove the effect of light rain",
    ]),
    "WET_Q007": (None, [
        "Brake firmly and early so you stop well short",
        "Change lanes so you can keep moving at the same speed",
        "Stay close behind so the driver behind you sees the queue",
    ]),
    "WET_Q008": (None, [
        "Other traffic is still travelling at the posted limit",
        "The road surface has recently been resurfaced",
        "The rain started less than a minute ago",
    ]),

    # --- speed_management ------------------------------------------------
    "SPEED_Q003": (None, [
        "60 km/h is safe in any condition because it is the posted limit",
        "The limit becomes advisory once visibility drops",
        "You should hold 60 km/h so you do not obstruct other traffic",
    ]),
    "SPEED_Q004": (None, [
        "Both need the same distance, since the brakes are the same",
        "The faster driver reacts sooner because they are concentrating harder",
        "The difference only becomes significant above 100 km/h",
    ]),
    "SPEED_Q005": (None, [
        "Whoever set the posted speed limit for that road",
        "The vehicle's speed-limiting or driver-assistance systems",
        "The driver in front, whose speed you should match",
    ]),
    "SPEED_Q006": (None, [
        "Whether the traffic around you is travelling above the limit",
        "How much time is left to reach the destination",
        "Whether the road has street lighting",
    ]),
    "SPEED_Q007": (None, [
        "It transfers responsibility for the hazard to the driver behind",
        "It allows a smaller following gap to remain safe",
        "It guarantees you can stop within the distance you can see",
    ]),
    "SPEED_Q008": (None, [
        "The speed you normally use on that road",
        "The posted limit, which applies in all conditions",
        "The speed of the traffic around you",
    ]),
    "SPEED_Q009": (None, [
        "Maintain speed and sound the horn as you approach",
        "Move towards the centre line without changing speed",
        "Continue at the limit unless they step onto the road",
    ]),

    # --- hazard_awareness ------------------------------------------------
    "HAZARD_Q003": (None, [
        "Sound the horn and maintain your speed",
        "Steer around the ball without slowing",
        "Stop immediately in the traffic lane and wait",
    ]),
    "HAZARD_Q004": (None, [
        "To judge whether you are permitted to overtake",
        "So you can match the speed of the fastest vehicle ahead",
        "Because the vehicle in front will brake before you need to",
    ]),
    "HAZARD_Q005": (None, [
        "To confirm the indicator is flashing",
        "To check the gap behind is large enough to brake in",
        "To signal to the driver beside you that you intend to move",
    ]),
    "HAZARD_Q006": (None, [
        "It usually means another driver has broken a road rule",
        "It indicates which lane has the shortest delay",
        "It confirms the road is unsafe for all traffic",
    ]),
    "HAZARD_Q007": (None, [
        "Whether the vehicles are angle-parked or parallel-parked",
        "The total number of vehicles in the row",
        "Whether the row ends before the next side street",
    ]),
    "HAZARD_Q008": (None, [
        "Mirrors give a wider view of the road ahead than the windscreen",
        "Mirrors must be checked at fixed time intervals",
        "Rear vision is only relevant when reversing or parking",
    ]),
    "HAZARD_Q009": (None, [
        "The road has been made safer since those crashes were recorded",
        "Those records show where the next crash is most likely to occur",
        "The recorded crash count should determine your speed there",
    ]),

    # --- following_distance ----------------------------------------------
    "FOLLOW_Q003": (None, [
        "It gives the same stopping distance in every condition",
        "It is the legal minimum that police enforce",
        "It works out the same for every length of vehicle",
    ]),
    "FOLLOW_Q004": (None, [
        "Keep it the same and use high beam instead",
        "Reduce it so the tail-lights ahead stay clearly visible",
        "Replace it with a fixed distance measured in car lengths",
    ]),
    "FOLLOW_Q005": (None, [
        "The same two seconds, since the rule does not change",
        "One second, provided you are travelling below 60 km/h",
        "Two car lengths for every 10 km/h of speed",
    ]),
    "FOLLOW_Q006": (None, [
        "Estimating how many car lengths separate the two vehicles",
        "Judging whether the vehicle ahead is exceeding the limit",
        "Deciding when it is safe to begin overtaking",
    ]),
    "FOLLOW_Q007": (None, [
        "Rain makes the vehicle ahead brake more suddenly",
        "Wet roads reduce how far your headlights reach",
        "Water on the road makes the gap look larger than it is",
    ]),
    "FOLLOW_Q008": (None, [
        "Letting them overtake when it is safe to do so",
        "Increasing your own following gap to the vehicle in front",
        "Continuing at a steady, predictable speed",
    ]),

    # --- intersections ----------------------------------------------------
    "INTER_Q003": (None, [
        "Enter on the green and wait behind the far line",
        "Enter if the light will stay green long enough",
        "Enter slowly so you do not hold up the vehicle behind",
    ]),
    "INTER_Q004": (None, [
        "Stop only if another vehicle is crossing",
        "Slow down and proceed if the way is clear",
        "Give way rather than stop when no other vehicle is present",
    ]),
    "INTER_Q005": (None, [
        "Give way only to vehicles approaching from your right",
        "Enter first if you reached the line before them",
        "Give way only if the other vehicle is indicating",
    ]),
    "INTER_Q006": (None, [
        "Priority only applies at intersections that are signed",
        "Scanning transfers responsibility to the other driver",
        "You must give way to anyone arriving at the same time",
    ]),
    "INTER_Q007": (None, [
        "It tells you which exit you are required to take",
        "It decides who has priority at the roundabout",
        "A vehicle that is signalling must give way to you",
    ]),
    "INTER_Q008": (None, [
        "Edge forward until other traffic sees you and stops",
        "Rely on the vehicle in front having checked before you",
        "Proceed normally if the intersection has traffic lights",
    ]),

    # --- signs_markings ---------------------------------------------------
    "SIGNS_Q003": (None, [
        "Warning sign",
        "Guide or direction sign",
        "Temporary roadworks marker",
    ]),
    "SIGNS_Q004": (None, [
        "To set a legally enforceable speed limit for that section",
        "To mark the point where a road rule stops applying",
        "To show the distance to the next town",
    ]),
    "SIGNS_Q006": (None, [
        "Follow the permanent signs, since temporary ones are advisory",
        "Follow the temporary limit only while workers are present",
        "Follow whichever of the two limits is higher",
    ]),
    "SIGNS_Q007": (None, [
        "To show where the road surface was last resurfaced",
        "To mark the boundary of the speed-limit zone",
        "To indicate where overtaking is always permitted",
    ]),
    "SIGNS_Q008": (None, [
        "Assume it means the same as a similar shape you already know",
        "Continue and look up the meaning once the trip has finished",
        "Do whatever the vehicle ahead of you does",
    ]),

    # --- sharing_road -----------------------------------------------------
    "SHARE_Q001": (None, [
        "They always have right of way in every situation",
        "They are not permitted on roads with a limit above 60 km/h",
        "They are required to wear high-visibility clothing at all times",
    ]),
    "SHARE_Q002": (None, [
        "Pass immediately, staying as close as the lane allows",
        "Cross the centre line at once regardless of oncoming traffic",
        "Stay directly behind until the cyclist leaves the road",
    ]),
    "SHARE_Q003": (None, [
        "Pedestrians must give way to vehicles already on the road",
        "Parked cars reduce the width available to oncoming traffic",
        "Pedestrian areas always carry a lower speed limit",
    ]),
    "SHARE_Q004": (None, [
        "They are permitted to travel faster than other traffic",
        "They must be given way to at every intersection",
        "They cannot brake as quickly as a car can",
    ]),
    "SHARE_Q005": (None, [
        "Always giving way, even where you have priority",
        "Keeping to the left lane at all times",
        "Matching the speed of surrounding traffic whatever the limit",
    ]),
    "SHARE_Q006": (None, [
        "Cyclists are required to stop behind a parked vehicle",
        "The mirror does not show the footpath side of the vehicle",
        "Opening a door into a lane requires indicating first",
    ]),
    "SHARE_Q007": (None, [
        "Continue at the limit unless a pedestrian has already stepped on",
        "Give way only to pedestrians on your side of the road",
        "Sound the horn to warn pedestrians you are approaching",
    ]),
    "SHARE_Q008": (None, [
        "It means you should never overtake a cyclist",
        "It sets one fixed distance that applies at every speed",
        "It applies only on roads with a marked bicycle lane",
    ]),

    # --- distraction ------------------------------------------------------
    "DISTRACT_Q002": (None, [
        "While stopped at a red light",
        "While stopped in a queue of traffic",
        "As soon as you notice the route is wrong",
    ]),
    "DISTRACT_Q003": (None, [
        "It drains the vehicle's battery while driving",
        "It interferes with the vehicle's safety systems",
        "It is only risky at speeds above 60 km/h",
    ]),
    "DISTRACT_Q004": (None, [
        "Yes, because the vehicle is stationary",
        "Yes, provided the handbrake is applied",
        "Yes, for navigation but not for messages",
    ]),
    "DISTRACT_Q005": (None, [
        "Adjust it while stopped at the next set of lights",
        "Adjust it on a straight section where there is no traffic",
        "Make the change quickly so your eyes leave the road only briefly",
    ]),
    "DISTRACT_Q006": (None, [
        "Short glances only matter on roads above 80 km/h",
        "The vehicle drifts sideways whenever you look away",
        "A few seconds is longer than the legal limit for looking away",
    ]),
    "DISTRACT_Q007": (None, [
        "Check it at the next red light",
        "Glance at it while the traffic ahead is stopped",
        "Deal with it quickly so it stops being a distraction",
    ]),
    "DISTRACT_Q008": (None, [
        "Mount the phone where it is easiest to reach while driving",
        "Turn the music up so notifications are less noticeable",
        "Plan to make any adjustments at the first set of lights",
    ]),

    # --- p_plate_rules ----------------------------------------------------
    "PPLATE_Q002": (None, [
        "They may drive provided they stay under 0.05",
        "They may drive if a full licence holder is in the car",
        "They may drive once enough time has passed since the drink",
    ]),
    "PPLATE_Q004": (None, [
        "As guidance that applies only during the first six months",
        "As rules that apply only when carrying passengers",
        "As conditions that apply only on high-speed roads",
    ]),
    "PPLATE_Q008": (None, [
        "Below 0.05, the same as a full licence holder",
        "Below 0.02",
        "Zero for P1 and below 0.05 for P2",
    ]),

    # --- fatigue ----------------------------------------------------------
    "FATIGUE_Q002": (None, [
        "Only reaction time; judgement is unaffected",
        "Only night vision",
        "Only the ability to hold a lane on long, straight roads",
    ]),
    "FATIGUE_Q003": (None, [
        "Traffic volumes are higher late at night",
        "Fatigue only affects drivers who have worked a full shift",
        "Fatigue only builds up after two hours of continuous driving",
    ]),
    "FATIGUE_Q005": (None, [
        "Open a window and keep driving",
        "Have a coffee and continue immediately",
        "Take a short break, then complete the trip regardless",
    ]),
    "FATIGUE_Q006": (None, [
        "How much time can I save by leaving now?",
        "Will coffee keep me going until I arrive?",
        "Is the route short enough that fatigue will not matter?",
    ]),
    "FATIGUE_Q007": (None, [
        "It makes the driver more likely to be stopped by police",
        "It causes the driver to sit in an unsafe position",
        "It only matters on trips longer than two hours",
    ]),

    # --- vehicle_safety ---------------------------------------------------
    "VEHICLE_Q001": (None, [
        "It determines how long the registration stays valid",
        "It affects fuel use more than it affects safety",
        "Modern safety systems compensate for poor vehicle condition",
    ]),
    "VEHICLE_Q002": (None, [
        "They are the only part of the vehicle checked at registration",
        "They affect fuel use rather than braking",
        "Tread depth only matters on unsealed roads",
    ]),
    "VEHICLE_Q003": (None, [
        "Faulty lights make the speedometer read inaccurately",
        "Lights are only required on roads without street lighting",
        "One working headlight is enough to see and be seen",
    ]),
    "VEHICLE_Q004": (None, [
        "To hold the driver in a comfortable seating position",
        "To stop the vehicle starting until everyone is seated",
        "To protect front-seat occupants only",
    ]),
    "VEHICLE_Q005": (None, [
        "Drive gently and have it checked after the trip",
        "Continue if the vehicle still has current registration",
        "Continue if no dashboard warning light has appeared",
    ]),
    "VEHICLE_Q006": (None, [
        "An obscured windscreen reduces how well the wipers work",
        "It stops the demister from clearing the glass",
        "It is only a problem when driving towards the sun",
    ]),
    "VEHICLE_Q007": (None, [
        "Any fault immediately cancels the vehicle's registration",
        "A fault that is not visible cannot affect safety",
        "Faults only matter on trips at highway speed",
    ]),
    "VEHICLE_Q008": (None, [
        "At the first stop during the trip",
        "When the vehicle next needs fuel",
        "At the next scheduled service",
    ]),
}

# Questions that test RoadBuddy's own content-governance process rather than
# driving. Kept in the file for traceability, not served to drivers.
EXCLUDED = {
    "NIGHT_Q009": "Asks which app lesson to show, not a road-safety point.",
    "WET_Q009": "Asks how the app should behave, not a road-safety point.",
    "SIGNS_Q005": "Asks what RoadBuddy should teach, not a road rule.",
    "PPLATE_Q003": "Asks about the team's source-review process.",
    "PPLATE_Q005": "Asks about the team's source-review process.",
    "PPLATE_Q006": "Asks about the team's content-governance process.",
    "PPLATE_Q007": "Asks what a content reviewer should verify.",
    "FATIGUE_Q004": "Asks what the app should avoid claiming, not a road-safety point.",
    "FATIGUE_Q008": "Asks how Buddy should reply, not a road-safety point.",
}

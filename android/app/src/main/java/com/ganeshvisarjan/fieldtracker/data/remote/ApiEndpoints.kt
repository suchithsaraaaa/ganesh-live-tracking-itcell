package com.ganeshvisarjan.fieldtracker.data.remote

/**
 * Every endpoint path this app depends on, in one place, so the real Django
 * contract can be updated centrally without touching Retrofit interfaces,
 * ViewModels, or UI (spec sections 5/49). See docs/API_CONTRACT.md for which
 * of these are CONFIRMED against apps/<app>/urls.py in the Django repo today vs.
 * CONCEPTUAL / awaiting backend implementation.
 */
object ApiEndpoints {
    // --- CONFIRMED (apps/accounts/urls.py) ---
    const val LOGIN = "auth/login/"
    const val LOGOUT = "auth/logout/"
    const val CURRENT_USER = "auth/me/"

    // --- CONFIRMED (apps/idols/urls.py, apps/assignments/urls.py) ---
    // Dedicated "my active assignment" endpoint, confirmed 2026-09-23
    // (CurrentAssignmentView) — the real source for "my active assignment".
    const val ASSIGNMENT_CURRENT = "assignments/current/"
    // General assignment list — still jurisdiction-filtered/real, just no
    // longer used for "my active assignment" now that ASSIGNMENT_CURRENT exists.
    const val ASSIGNMENTS = "assignments/"
    const val IDOL_DETAIL = "idols/{gpid}/" // path param: gpid

    // --- CONFIRMED (apps/tracking/urls.py) ---
    // tracking/start/ is the real, tested, server-side 50m + geocoding-confidence
    // start gate — there is no separate procession-start endpoint (see below).
    const val TRACKING_START = "tracking/start/"
    const val TRACKING_STOP = "tracking/stop/"
    const val TRACKING_LOCATION_BATCH = "tracking/location/batch/"

    // --- CONCEPTUAL / TODO-BACKEND — no apps/processions app exists.
    // Re-confirmed 2026-09-23: still fictional. The real start-gate action goes
    // through TRACKING_START above instead — see docs/API_CONTRACT.md
    // "Procession lifecycle". Kept as named constants (unused by the real start
    // flow) so this scaffolding is ready if a real procession API is ever built.
    const val PROCESSION_START = "processions/start/"
    const val PROCESSION_EVENTS = "processions/events/"
}

package com.ganeshvisarjan.fieldtracker.navigation

/** Flat, deliberately small nav graph (spec section 45) — no screens beyond the core workflow. */
object Destinations {
    const val SPLASH = "splash"
    const val LOGIN = "login"
    const val HOME = "home"
    const val ASSIGNMENT = "assignment"

    /** No args — TrackingScreen derives the active session reactively from Room, so this
     * route works identically whether reached right after Start Procession or by
     * re-opening an already-active session from Home. */
    const val TRACKING = "tracking"

    const val PROFILE = "profile"
    const val DEBUG = "debug"
}

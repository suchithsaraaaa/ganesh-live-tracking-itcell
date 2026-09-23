package com.ganeshvisarjan.fieldtracker.domain.model

/**
 * Idol height classification. Independent of tracking/procession status — never
 * use this as a stand-in for whether an idol is being tracked. Backend does not
 * currently return a classification field, so this is computed client-side from
 * the raw height; if the backend later adds its own classification, prefer that
 * value and keep this as the fallback so behavior doesn't change silently.
 */
enum class HeightClass {
    BELOW_OPERATIONAL_THRESHOLD,
    GREEN,   // 15-20 ft
    YELLOW,  // 21-25 ft
    RED,     // 26+ ft
    UNKNOWN; // height not recorded

    companion object {
        fun fromHeightFeet(heightFeet: Double?): HeightClass {
            if (heightFeet == null) return UNKNOWN
            return when {
                heightFeet < 15.0 -> BELOW_OPERATIONAL_THRESHOLD
                heightFeet <= 20.0 -> GREEN
                heightFeet <= 25.0 -> YELLOW
                else -> RED
            }
        }

        /**
         * The backend now computes this itself (IdolListSerializer/IdolDetailSerializer
         * .get_height_classification — GREEN/YELLOW/RED/SUBTHRESHOLD/UNKNOWN). Prefer
         * this over [fromHeightFeet] whenever present, per spec section 10 ("prefer
         * a reusable enum... if the backend eventually provides classifications").
         */
        fun fromBackendValue(raw: String?, heightFeet: Double?): HeightClass = when (raw) {
            "GREEN" -> GREEN
            "YELLOW" -> YELLOW
            "RED" -> RED
            "SUBTHRESHOLD" -> BELOW_OPERATIONAL_THRESHOLD
            "UNKNOWN" -> UNKNOWN
            else -> fromHeightFeet(heightFeet) // backend didn't send a value — fall back locally
        }
    }
}

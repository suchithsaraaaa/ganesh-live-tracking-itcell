package com.ganeshvisarjan.fieldtracker.data.mock

import com.ganeshvisarjan.fieldtracker.domain.model.Assignment
import com.ganeshvisarjan.fieldtracker.domain.model.AssignmentStatus
import com.ganeshvisarjan.fieldtracker.domain.model.BackendProcessionState
import com.ganeshvisarjan.fieldtracker.domain.model.GeoPoint
import com.ganeshvisarjan.fieldtracker.domain.model.HeightClass
import com.ganeshvisarjan.fieldtracker.domain.model.Idol
import com.ganeshvisarjan.fieldtracker.domain.model.Role
import com.ganeshvisarjan.fieldtracker.domain.model.User

/**
 * Sample data for MOCK builds only (spec section 31) — lets the whole app run
 * end-to-end without the Django backend. Never referenced by dev/staging/prod
 * flavors.
 */
object MockData {

    val officer = User(
        id = 1001,
        username = "mock.constable",
        displayName = "R. Kumar",
        role = Role.CONSTABLE,
        policeStation = "Charminar",
        zone = "Zone 4",
        division = "South",
    )

    // A real-looking landmark near Charminar — reference/display data only.
    // Start Procession has no proximity requirement against this (2026-09-23
    // product decision), so this is not something "Check Location" is measured
    // against anymore.
    private val idolOrigin = GeoPoint(17.361200, 78.474900)

    val idol = Idol(
        gpid = "HYD-CMRZ-CMNR-0234",
        ownerName = "Ramesh Reddy",
        associationName = "Charminar Youth Ganesh Mandal",
        heightFeet = 26.0,
        heightClass = HeightClass.fromHeightFeet(26.0),
        isOperationalEligible = true,
        originAddress = "Near Charminar, Pathergatti",
        originZone = "Zone 4",
        originLocation = idolOrigin,
        startGateEligible = true, // informational backend field only — no longer used as a start gate
        destinationAddress = "Hussain Sagar Visarjan Point",
        currentZone = "Zone 4",
        currentLocation = null,
        contactNumber = "9XXXXXXXXX",
        backendProcessionState = BackendProcessionState.NOT_STARTED,
    )

    val assignment = Assignment(
        assignmentId = "mock-assignment-1",
        officerId = officer.id,
        idol = idol,
        status = AssignmentStatus.ACTIVE,
        assignedAt = "2026-09-22T09:00:00Z",
    )
}

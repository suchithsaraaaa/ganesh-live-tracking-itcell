package com.ganeshvisarjan.fieldtracker.data.repository

import com.ganeshvisarjan.fieldtracker.core.network.ApiResult
import com.ganeshvisarjan.fieldtracker.data.remote.api.AssignmentApi
import com.ganeshvisarjan.fieldtracker.data.remote.dto.IdolDto
import com.ganeshvisarjan.fieldtracker.core.network.safeApiCall
import com.ganeshvisarjan.fieldtracker.domain.model.Assignment
import com.ganeshvisarjan.fieldtracker.domain.model.AssignmentStatus
import com.ganeshvisarjan.fieldtracker.domain.model.BackendProcessionState
import com.ganeshvisarjan.fieldtracker.domain.model.GeoPoint
import com.ganeshvisarjan.fieldtracker.domain.model.HeightClass
import com.ganeshvisarjan.fieldtracker.domain.model.Idol
import com.ganeshvisarjan.fieldtracker.domain.repository.AssignmentRepository
import javax.inject.Inject
import javax.inject.Singleton

private fun IdolDto.toDomain(): Idol = Idol(
    gpid = gpid,
    ownerName = name ?: associationName ?: gpid,
    associationName = associationName,
    heightFeet = idolHeightFeet,
    heightClass = HeightClass.fromBackendValue(heightClassification, idolHeightFeet),
    isOperationalEligible = isOperationalEligible,
    originAddress = address,
    originZone = zone,
    originLocation = GeoPoint.ofOrNull(latitude, longitude),
    startGateEligible = startGateEligible,
    destinationAddress = riverName,
    currentZone = zone,
    currentLocation = null,
    contactNumber = contactInfo?.mobileNo,
    backendProcessionState = BackendProcessionState.fromRaw(processionState),
)

@Singleton
class AssignmentRepositoryImpl @Inject constructor(
    private val assignmentApi: AssignmentApi,
) : AssignmentRepository {

    /**
     * Uses the confirmed `GET /assignments/current/` (re-verified 2026-09-23 —
     * see docs/API_CONTRACT.md), scoped server-side to the authenticated
     * officer. Replaces the earlier "page 1 of the list, pick is_active"
     * workaround, which could silently miss an officer's active assignment if
     * it wasn't on page 1.
     */
    override suspend fun getActiveAssignment(): ApiResult<Assignment?> = safeApiCall {
        val dto = assignmentApi.currentAssignment().activeAssignment ?: return@safeApiCall null
        val idol = assignmentApi.idolDetail(dto.gpid).toDomain()
        Assignment(
            assignmentId = dto.assignmentId.toString(),
            officerId = null, // not returned by this endpoint — see Assignment.officerId kdoc
            idol = idol,
            status = AssignmentStatus.ACTIVE, // this endpoint only ever returns the caller's active row, or null
            assignedAt = dto.startedAt,
        )
    }
}

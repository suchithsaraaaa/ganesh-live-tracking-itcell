package com.ganeshvisarjan.fieldtracker.data.remote.api

import com.ganeshvisarjan.fieldtracker.data.remote.ApiEndpoints
import com.ganeshvisarjan.fieldtracker.data.remote.dto.AssignmentListResponseDto
import com.ganeshvisarjan.fieldtracker.data.remote.dto.CurrentAssignmentResponseDto
import com.ganeshvisarjan.fieldtracker.data.remote.dto.IdolDto
import retrofit2.http.GET
import retrofit2.http.Path
import retrofit2.http.Query

interface AssignmentApi {
    /** The real "my active assignment" endpoint — confirmed 2026-09-23, scoped server-side to the caller. */
    @GET(ApiEndpoints.ASSIGNMENT_CURRENT)
    suspend fun currentAssignment(): CurrentAssignmentResponseDto

    /** General jurisdiction-filtered assignment list (common/permissions.py) — not used for "my active assignment" anymore. */
    @GET(ApiEndpoints.ASSIGNMENTS)
    suspend fun myAssignments(@Query("page") page: Int = 1): AssignmentListResponseDto

    @GET(ApiEndpoints.IDOL_DETAIL)
    suspend fun idolDetail(@Path("gpid") gpid: String): IdolDto
}

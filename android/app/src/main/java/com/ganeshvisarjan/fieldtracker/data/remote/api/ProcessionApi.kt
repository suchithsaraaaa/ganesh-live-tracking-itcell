package com.ganeshvisarjan.fieldtracker.data.remote.api

import com.ganeshvisarjan.fieldtracker.data.remote.ApiEndpoints
import com.ganeshvisarjan.fieldtracker.data.remote.dto.ProcessionEventRequestDto
import com.ganeshvisarjan.fieldtracker.data.remote.dto.ProcessionStartRequestDto
import com.ganeshvisarjan.fieldtracker.data.remote.dto.ProcessionStateResponseDto
import retrofit2.http.Body
import retrofit2.http.POST

/** CONCEPTUAL — see docs/API_CONTRACT.md. No apps/processions app exists in the backend yet. */
interface ProcessionApi {
    @POST(ApiEndpoints.PROCESSION_START)
    suspend fun startProcession(@Body request: ProcessionStartRequestDto): ProcessionStateResponseDto

    @POST(ApiEndpoints.PROCESSION_EVENTS)
    suspend fun submitEvent(@Body request: ProcessionEventRequestDto): ProcessionStateResponseDto
}

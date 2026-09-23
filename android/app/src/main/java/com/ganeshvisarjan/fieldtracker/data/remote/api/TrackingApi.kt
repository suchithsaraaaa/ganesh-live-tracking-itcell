package com.ganeshvisarjan.fieldtracker.data.remote.api

import com.ganeshvisarjan.fieldtracker.data.remote.ApiEndpoints
import com.ganeshvisarjan.fieldtracker.data.remote.dto.StartTrackingRequestDto
import com.ganeshvisarjan.fieldtracker.data.remote.dto.StartTrackingResponseDto
import com.ganeshvisarjan.fieldtracker.data.remote.dto.StopTrackingRequestDto
import com.ganeshvisarjan.fieldtracker.data.remote.dto.TelemetryBatchRequestDto
import com.ganeshvisarjan.fieldtracker.data.remote.dto.TelemetryBatchResponseDto
import retrofit2.http.Body
import retrofit2.http.POST

interface TrackingApi {
    @POST(ApiEndpoints.TRACKING_START)
    suspend fun startTracking(@Body request: StartTrackingRequestDto): StartTrackingResponseDto

    @POST(ApiEndpoints.TRACKING_STOP)
    suspend fun stopTracking(@Body request: StopTrackingRequestDto)

    @POST(ApiEndpoints.TRACKING_LOCATION_BATCH)
    suspend fun submitTelemetryBatch(@Body request: TelemetryBatchRequestDto): TelemetryBatchResponseDto
}

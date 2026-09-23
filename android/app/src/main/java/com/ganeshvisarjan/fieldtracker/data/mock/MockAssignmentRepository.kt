package com.ganeshvisarjan.fieldtracker.data.mock

import com.ganeshvisarjan.fieldtracker.core.network.ApiResult
import com.ganeshvisarjan.fieldtracker.domain.model.Assignment
import com.ganeshvisarjan.fieldtracker.domain.repository.AssignmentRepository
import kotlinx.coroutines.delay
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class MockAssignmentRepository @Inject constructor() : AssignmentRepository {
    override suspend fun getActiveAssignment(): ApiResult<Assignment?> {
        delay(300)
        return ApiResult.Success(MockData.assignment)
    }
}

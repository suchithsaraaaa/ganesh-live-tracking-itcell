package com.ganeshvisarjan.fieldtracker.domain.repository

import com.ganeshvisarjan.fieldtracker.core.network.ApiResult
import com.ganeshvisarjan.fieldtracker.domain.model.Assignment

/**
 * The officer's currently active assignment — never a list the officer picks
 * from (spec "User-to-Idol Assignment" section 3: the officer tracks ONLY the
 * idol assigned to them). Assigning a GPID to an officer is a web/admin action,
 * not something this app can do.
 */
interface AssignmentRepository {
    suspend fun getActiveAssignment(): ApiResult<Assignment?>
}

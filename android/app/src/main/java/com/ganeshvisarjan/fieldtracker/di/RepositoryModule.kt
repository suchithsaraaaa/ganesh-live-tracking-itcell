package com.ganeshvisarjan.fieldtracker.di

import com.ganeshvisarjan.fieldtracker.core.config.AppEnvironment
import com.ganeshvisarjan.fieldtracker.data.mock.MockAssignmentRepository
import com.ganeshvisarjan.fieldtracker.data.mock.MockAuthRepository
import com.ganeshvisarjan.fieldtracker.data.mock.MockProcessionRepository
import com.ganeshvisarjan.fieldtracker.data.mock.MockTrackingRepository
import com.ganeshvisarjan.fieldtracker.data.repository.AssignmentRepositoryImpl
import com.ganeshvisarjan.fieldtracker.data.repository.AuthRepositoryImpl
import com.ganeshvisarjan.fieldtracker.data.repository.ProcessionRepositoryImpl
import com.ganeshvisarjan.fieldtracker.data.repository.TrackingRepositoryImpl
import com.ganeshvisarjan.fieldtracker.domain.repository.AssignmentRepository
import com.ganeshvisarjan.fieldtracker.domain.repository.AuthRepository
import com.ganeshvisarjan.fieldtracker.domain.repository.ProcessionRepository
import com.ganeshvisarjan.fieldtracker.domain.repository.TrackingRepository
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent
import javax.inject.Singleton

/**
 * The ONE place mock vs. real is decided (spec section 32) — everything above
 * this (ViewModels, UI, sync workers) depends only on the domain interfaces and
 * never branches on `if (mock)`.
 */
@Module
@InstallIn(SingletonComponent::class)
object RepositoryModule {

    @Provides
    @Singleton
    fun provideAuthRepository(
        mock: MockAuthRepository,
        real: AuthRepositoryImpl,
    ): AuthRepository = if (AppEnvironment.current.usesMockApi) mock else real

    @Provides
    @Singleton
    fun provideAssignmentRepository(
        mock: MockAssignmentRepository,
        real: AssignmentRepositoryImpl,
    ): AssignmentRepository = if (AppEnvironment.current.usesMockApi) mock else real

    @Provides
    @Singleton
    fun provideTrackingRepository(
        mock: MockTrackingRepository,
        real: TrackingRepositoryImpl,
    ): TrackingRepository = if (AppEnvironment.current.usesMockApi) mock else real

    @Provides
    @Singleton
    fun provideProcessionRepository(
        mock: MockProcessionRepository,
        real: ProcessionRepositoryImpl,
    ): ProcessionRepository = if (AppEnvironment.current.usesMockApi) mock else real
}

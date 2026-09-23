package com.ganeshvisarjan.fieldtracker.di

import android.content.Context
import androidx.room.Room
import com.ganeshvisarjan.fieldtracker.data.local.AppDatabase
import com.ganeshvisarjan.fieldtracker.data.local.dao.ProcessionEventDao
import com.ganeshvisarjan.fieldtracker.data.local.dao.TelemetryDao
import com.ganeshvisarjan.fieldtracker.data.local.dao.TrackingSessionDao
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.android.qualifiers.ApplicationContext
import dagger.hilt.components.SingletonComponent
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
object DatabaseModule {

    @Provides
    @Singleton
    fun provideAppDatabase(@ApplicationContext context: Context): AppDatabase =
        Room.databaseBuilder(context, AppDatabase::class.java, AppDatabase.DATABASE_NAME)
            // No destructive fallback: telemetry is operational data. A future
            // schema change must ship a real Migration, not a wipe.
            .build()

    @Provides
    fun provideTrackingSessionDao(db: AppDatabase): TrackingSessionDao = db.trackingSessionDao()

    @Provides
    fun provideTelemetryDao(db: AppDatabase): TelemetryDao = db.telemetryDao()

    @Provides
    fun provideProcessionEventDao(db: AppDatabase): ProcessionEventDao = db.processionEventDao()
}

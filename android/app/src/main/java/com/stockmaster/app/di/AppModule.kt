package com.stockmaster.app.di

import com.stockmaster.app.BuildConfig
import com.stockmaster.core.network.BaseUrlProvider
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
object AppModule {

    @Provides
    @Singleton
    fun provideBaseUrlProvider(): BaseUrlProvider = object : BaseUrlProvider {
        override val baseUrl: String = BuildConfig.BASE_URL
    }
}

package com.stockmaster.data.di

import com.stockmaster.core.network.TokenRefreshService
import com.stockmaster.data.remote.AuthApiService
import com.stockmaster.data.remote.StockApiService
import com.stockmaster.data.repository.AuthRepositoryImpl
import com.stockmaster.data.repository.StockRepositoryImpl
import com.stockmaster.domain.repository.AuthRepository
import com.stockmaster.domain.repository.StockRepository
import dagger.Binds
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent
import retrofit2.Retrofit
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
abstract class DataModule {

    @Binds
    @Singleton
    abstract fun bindAuthRepository(impl: AuthRepositoryImpl): AuthRepository

    @Binds
    @Singleton
    abstract fun bindStockRepository(impl: StockRepositoryImpl): StockRepository

    @Binds
    @Singleton
    abstract fun bindTokenRefreshService(impl: AuthRepositoryImpl): TokenRefreshService

    companion object {
        @Provides
        @Singleton
        fun provideAuthApiService(retrofit: Retrofit): AuthApiService {
            return retrofit.create(AuthApiService::class.java)
        }

        @Provides
        @Singleton
        fun provideStockApiService(retrofit: Retrofit): StockApiService {
            return retrofit.create(StockApiService::class.java)
        }
    }
}

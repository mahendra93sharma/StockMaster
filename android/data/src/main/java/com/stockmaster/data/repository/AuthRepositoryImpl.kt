package com.stockmaster.data.repository

import com.stockmaster.core.auth.TokenStore
import com.stockmaster.core.network.TokenPair
import com.stockmaster.core.network.TokenRefreshService
import com.stockmaster.data.mapper.toDomain
import com.stockmaster.data.remote.AuthApiService
import com.stockmaster.data.remote.dto.GoogleAuthRequestDto
import com.stockmaster.data.remote.dto.RefreshRequestDto
import com.stockmaster.domain.model.AuthTokens
import com.stockmaster.domain.repository.AuthRepository
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class AuthRepositoryImpl @Inject constructor(
    private val authApi: AuthApiService,
    private val tokenStore: TokenStore,
) : AuthRepository, TokenRefreshService {

    override suspend fun loginWithGoogle(firebaseIdToken: String): AuthTokens {
        val response = authApi.loginWithGoogle(GoogleAuthRequestDto(idToken = firebaseIdToken))
        tokenStore.saveTokens(response.accessToken, response.refreshToken)
        return response.toDomain()
    }

    override suspend fun refresh(refreshToken: String): TokenPair? {
        return try {
            val response = authApi.refresh(RefreshRequestDto(refreshToken = refreshToken))
            tokenStore.saveTokens(response.accessToken, response.refreshToken)
            TokenPair(response.accessToken, response.refreshToken)
        } catch (e: Exception) {
            null
        }
    }

    override suspend fun logout() {
        try {
            authApi.logout()
        } finally {
            tokenStore.clearTokens()
        }
    }
}

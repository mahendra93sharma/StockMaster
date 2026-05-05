package com.stockmaster.core.network

/**
 * Interface for refreshing tokens — implemented in the data layer.
 */
interface TokenRefreshService {
    suspend fun refreshTokens(refreshToken: String): TokenPair?
}

data class TokenPair(
    val accessToken: String,
    val refreshToken: String,
)

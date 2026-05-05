package com.stockmaster.core.network

import com.stockmaster.core.auth.TokenStore
import kotlinx.coroutines.runBlocking
import okhttp3.Authenticator
import okhttp3.Request
import okhttp3.Response
import okhttp3.Route
import timber.log.Timber
import javax.inject.Inject
import javax.inject.Singleton

/**
 * Handles 401 responses by refreshing the access token once and retrying.
 */
@Singleton
class TokenRefreshAuthenticator @Inject constructor(
    private val tokenStore: TokenStore,
    private val refreshService: TokenRefreshService,
) : Authenticator {

    override fun authenticate(route: Route?, response: Response): Request? {
        // Don't retry if we already tried refreshing
        if (response.request.header("X-Retry-Auth") != null) {
            return null
        }

        val refreshToken = runBlocking { tokenStore.getRefreshToken() } ?: return null

        val newTokens = runBlocking {
            try {
                refreshService.refresh(refreshToken)
            } catch (e: Exception) {
                Timber.e(e, "Token refresh failed")
                null
            }
        } ?: return null

        runBlocking {
            tokenStore.saveTokens(newTokens.accessToken, newTokens.refreshToken)
        }

        return response.request.newBuilder()
            .header("Authorization", "Bearer ${newTokens.accessToken}")
            .header("X-Retry-Auth", "true")
            .build()
    }
}

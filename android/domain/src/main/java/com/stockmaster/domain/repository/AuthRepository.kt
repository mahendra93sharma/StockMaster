package com.stockmaster.domain.repository

import com.stockmaster.domain.model.AuthTokens

interface AuthRepository {
    suspend fun loginWithGoogle(firebaseIdToken: String): AuthTokens
    suspend fun refresh(refreshToken: String): AuthTokens
    suspend fun logout()
}

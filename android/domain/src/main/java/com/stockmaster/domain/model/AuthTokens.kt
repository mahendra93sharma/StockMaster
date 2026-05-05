package com.stockmaster.domain.model

data class AuthTokens(
    val accessToken: String,
    val refreshToken: String,
    val user: User,
)

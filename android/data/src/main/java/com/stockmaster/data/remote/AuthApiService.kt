package com.stockmaster.data.remote

import com.stockmaster.data.remote.dto.GoogleAuthRequestDto
import com.stockmaster.data.remote.dto.RefreshRequestDto
import com.stockmaster.data.remote.dto.TokenResponseDto
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST

interface AuthApiService {

    @POST("api/v1/auth/google")
    suspend fun loginWithGoogle(@Body body: GoogleAuthRequestDto): TokenResponseDto

    @POST("api/v1/auth/refresh")
    suspend fun refresh(@Body body: RefreshRequestDto): TokenResponseDto

    @POST("api/v1/auth/logout")
    suspend fun logout()

    @GET("api/v1/auth/me")
    suspend fun getMe(): com.stockmaster.data.remote.dto.UserDto
}

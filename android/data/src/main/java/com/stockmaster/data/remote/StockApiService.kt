package com.stockmaster.data.remote

import com.stockmaster.data.remote.dto.ClosedTradeDto
import com.stockmaster.data.remote.dto.HomeFeedResponseDto
import com.stockmaster.data.remote.dto.PaginatedResponse
import com.stockmaster.data.remote.dto.RecommendationDto
import retrofit2.http.GET
import retrofit2.http.Query

interface StockApiService {

    @GET("api/v1/feed/home")
    suspend fun getHomeFeed(
        @Query("limit") limit: Int = 30,
    ): HomeFeedResponseDto

    @GET("api/v1/stocks/recommendations")
    suspend fun getRecommendations(
        @Query("horizon") horizon: String,
        @Query("status") status: String = "active",
        @Query("cursor") cursor: String? = null,
        @Query("limit") limit: Int = 20,
    ): PaginatedResponse<RecommendationDto>

    @GET("api/v1/stocks/closed-trades")
    suspend fun getClosedTrades(
        @Query("cursor") cursor: String? = null,
        @Query("limit") limit: Int = 20,
    ): PaginatedResponse<ClosedTradeDto>
}

package com.stockmaster.data.remote.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.JsonObject

@Serializable
data class RecommendationDto(
    val id: String,
    @SerialName("instrument_name") val instrumentName: String,
    val exchange: String,
    val action: String,
    val entry: Double,
    val target: Double,
    val stoploss: Double,
    val confidence: Double,
    val rationale: String,
    @SerialName("risk_factors") val riskFactors: List<String> = emptyList(),
    val horizon: String,
    @SerialName("created_at") val createdAt: String,
)

@Serializable
data class ClosedTradeDto(
    val id: String,
    @SerialName("instrument_name") val instrumentName: String,
    val exchange: String,
    val action: String,
    val entry: Double,
    @SerialName("exit_price") val exitPrice: Double,
    @SerialName("pnl_pct") val pnlPct: Double,
    @SerialName("close_reason") val closeReason: String,
    val horizon: String,
    @SerialName("closed_at") val closedAt: String,
)

@Serializable
data class PaginatedResponse<T>(
    val items: List<T>,
    val cursor: String? = null,
)

@Serializable
data class FeedItemDto(
    val type: String,
    val ts: String,
    val title: String,
    val subtitle: String,
    val meta: JsonObject? = null,
)

@Serializable
data class HomeFeedResponseDto(
    val items: List<FeedItemDto>,
    val count: Int,
)

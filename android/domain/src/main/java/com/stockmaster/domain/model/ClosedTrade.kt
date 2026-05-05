package com.stockmaster.domain.model

data class ClosedTrade(
    val id: String,
    val instrumentName: String,
    val exchange: String,
    val action: RecommendationAction,
    val entry: Double,
    val exitPrice: Double,
    val pnlPct: Double,
    val closeReason: String,
    val horizon: Horizon,
    val closedAt: String,
)

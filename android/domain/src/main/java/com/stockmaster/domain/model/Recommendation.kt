package com.stockmaster.domain.model

enum class Horizon(val label: String) {
    SHORT("1–7 days"),
    MID("1–3 months"),
    LONG("6–24 months"),
}

enum class RecommendationAction { BUY, SELL, HOLD }

data class Recommendation(
    val id: String,
    val instrumentName: String,
    val exchange: String,
    val action: RecommendationAction,
    val entry: Double,
    val target: Double,
    val stopLoss: Double,
    val confidence: Double,
    val rationale: String,
    val riskFactors: List<String>,
    val horizon: Horizon,
    val createdAt: String,
)

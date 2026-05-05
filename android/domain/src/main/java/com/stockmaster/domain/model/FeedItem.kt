package com.stockmaster.domain.model

data class FeedItem(
    val type: FeedItemType,
    val timestamp: String,
    val title: String,
    val subtitle: String,
)

enum class FeedItemType(val label: String, val icon: String) {
    BULK_DEAL("Deal", "📊"),
    BLOCK_DEAL("Block", "📈"),
    NEWS("News", "📰"),
    RECOMMENDATION("Signal", "🎯"),
    CORPORATE_ACTION("Event", "📋"),
    UNKNOWN("", ""),
}

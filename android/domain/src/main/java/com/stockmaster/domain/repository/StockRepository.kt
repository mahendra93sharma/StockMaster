package com.stockmaster.domain.repository

import com.stockmaster.domain.model.ClosedTrade
import com.stockmaster.domain.model.FeedItem
import com.stockmaster.domain.model.Recommendation

interface StockRepository {
    suspend fun getHomeFeed(): List<FeedItem>
    suspend fun getRecommendations(horizon: String, cursor: String? = null): List<Recommendation>
    suspend fun getClosedTrades(cursor: String? = null): List<ClosedTrade>
}

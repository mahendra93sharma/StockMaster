package com.stockmaster.data.repository

import com.stockmaster.data.mapper.toDomain
import com.stockmaster.data.remote.StockApiService
import com.stockmaster.domain.model.ClosedTrade
import com.stockmaster.domain.model.FeedItem
import com.stockmaster.domain.model.Recommendation
import com.stockmaster.domain.repository.StockRepository
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class StockRepositoryImpl @Inject constructor(
    private val stockApi: StockApiService,
) : StockRepository {

    override suspend fun getHomeFeed(): List<FeedItem> {
        return stockApi.getHomeFeed().items.map { it.toDomain() }
    }

    override suspend fun getRecommendations(horizon: String, cursor: String?): List<Recommendation> {
        return stockApi.getRecommendations(horizon = horizon, cursor = cursor)
            .items.map { it.toDomain() }
    }

    override suspend fun getClosedTrades(cursor: String?): List<ClosedTrade> {
        return stockApi.getClosedTrades(cursor = cursor)
            .items.map { it.toDomain() }
    }
}

package com.stockmaster.data.mapper

import com.stockmaster.data.remote.dto.ClosedTradeDto
import com.stockmaster.data.remote.dto.FeedItemDto
import com.stockmaster.data.remote.dto.RecommendationDto
import com.stockmaster.data.remote.dto.TokenResponseDto
import com.stockmaster.data.remote.dto.UserDto
import com.stockmaster.domain.model.AuthTokens
import com.stockmaster.domain.model.ClosedTrade
import com.stockmaster.domain.model.FeedItem
import com.stockmaster.domain.model.FeedItemType
import com.stockmaster.domain.model.Horizon
import com.stockmaster.domain.model.Recommendation
import com.stockmaster.domain.model.RecommendationAction
import com.stockmaster.domain.model.User

fun UserDto.toDomain(): User = User(
    id = id,
    email = email,
    displayName = displayName,
    photoUrl = photoUrl,
    role = role,
)

fun TokenResponseDto.toDomain(): AuthTokens = AuthTokens(
    accessToken = accessToken,
    refreshToken = refreshToken,
    user = user.toDomain(),
)

fun RecommendationDto.toDomain(): Recommendation = Recommendation(
    id = id,
    instrumentName = instrumentName,
    exchange = exchange,
    action = RecommendationAction.valueOf(action),
    entry = entry,
    target = target,
    stopLoss = stoploss,
    confidence = confidence,
    rationale = rationale,
    riskFactors = riskFactors,
    horizon = when (horizon) {
        "short" -> Horizon.SHORT
        "mid" -> Horizon.MID
        "long" -> Horizon.LONG
        else -> Horizon.SHORT
    },
    createdAt = createdAt,
)

fun ClosedTradeDto.toDomain(): ClosedTrade = ClosedTrade(
    id = id,
    instrumentName = instrumentName,
    exchange = exchange,
    action = RecommendationAction.valueOf(action),
    entry = entry,
    exitPrice = exitPrice,
    pnlPct = pnlPct,
    closeReason = closeReason,
    horizon = when (horizon) {
        "short" -> Horizon.SHORT
        "mid" -> Horizon.MID
        "long" -> Horizon.LONG
        else -> Horizon.SHORT
    },
    closedAt = closedAt,
)

fun FeedItemDto.toDomain(): FeedItem = FeedItem(
    type = when (type) {
        "bulk_deal" -> FeedItemType.BULK_DEAL
        "block_deal" -> FeedItemType.BLOCK_DEAL
        "news" -> FeedItemType.NEWS
        "recommendation" -> FeedItemType.RECOMMENDATION
        "corporate_action" -> FeedItemType.CORPORATE_ACTION
        else -> FeedItemType.UNKNOWN
    },
    timestamp = ts,
    title = title,
    subtitle = subtitle,
)

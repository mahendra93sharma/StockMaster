package com.stockmaster.core.network

/**
 * Provides the base URL for the current build variant.
 * Implemented in the app module which has access to BuildConfig.
 */
interface BaseUrlProvider {
    val baseUrl: String
}

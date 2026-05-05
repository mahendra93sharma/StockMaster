package com.stockmaster.core.network

import javax.inject.Inject
import javax.inject.Singleton

/**
 * Provides the base URL for the current build variant.
 * Injected by the app module which has access to BuildConfig.
 */
@Singleton
class BaseUrlProvider @Inject constructor() {
    var baseUrl: String = ""
        internal set
}

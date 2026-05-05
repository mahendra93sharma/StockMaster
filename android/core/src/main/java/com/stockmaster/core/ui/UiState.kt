package com.stockmaster.core.ui

/**
 * Sealed interface representing the state of a UI operation.
 */
sealed interface UiState<out T> {
    data object Loading : UiState<Nothing>
    data class Success<T>(val data: T) : UiState<T>
    data class Error(val message: String, val retry: () -> Unit) : UiState<Nothing>
}

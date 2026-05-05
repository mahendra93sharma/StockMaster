package com.stockmaster.feature.home

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.stockmaster.core.ui.UiState
import com.stockmaster.domain.model.FeedItem
import com.stockmaster.domain.repository.StockRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class HomeViewModel @Inject constructor(
    private val stockRepository: StockRepository,
) : ViewModel() {

    private val _state = MutableStateFlow<UiState<List<FeedItem>>>(UiState.Loading)
    val state: StateFlow<UiState<List<FeedItem>>> = _state.asStateFlow()

    init {
        load()
    }

    fun load() {
        _state.value = UiState.Loading
        viewModelScope.launch {
            try {
                val feed = stockRepository.getHomeFeed()
                _state.value = UiState.Success(feed)
            } catch (e: Exception) {
                _state.value = UiState.Error(
                    message = e.message ?: "Failed to load feed",
                    retry = ::load,
                )
            }
        }
    }
}

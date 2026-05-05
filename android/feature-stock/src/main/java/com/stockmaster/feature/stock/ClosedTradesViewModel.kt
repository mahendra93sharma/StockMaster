package com.stockmaster.feature.stock

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.stockmaster.core.ui.UiState
import com.stockmaster.domain.model.ClosedTrade
import com.stockmaster.domain.repository.StockRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class ClosedTradesViewModel @Inject constructor(
    private val stockRepository: StockRepository,
) : ViewModel() {

    private val _state = MutableStateFlow<UiState<List<ClosedTrade>>>(UiState.Loading)
    val state: StateFlow<UiState<List<ClosedTrade>>> = _state.asStateFlow()

    init {
        load()
    }

    fun load() {
        _state.value = UiState.Loading
        viewModelScope.launch {
            try {
                val trades = stockRepository.getClosedTrades()
                _state.value = UiState.Success(trades)
            } catch (e: Exception) {
                _state.value = UiState.Error(
                    message = e.message ?: "Failed to load closed trades",
                    retry = ::load,
                )
            }
        }
    }
}

package com.stockmaster.feature.stock

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.stockmaster.core.ui.UiState
import com.stockmaster.domain.model.Recommendation
import com.stockmaster.domain.repository.StockRepository
import dagger.assisted.Assisted
import dagger.assisted.AssistedFactory
import dagger.assisted.AssistedInject
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

@HiltViewModel(assistedFactory = RecommendationViewModel.Factory::class)
class RecommendationViewModel @AssistedInject constructor(
    @Assisted private val horizon: String,
    private val stockRepository: StockRepository,
) : ViewModel() {

    @AssistedFactory
    interface Factory {
        fun create(horizon: String): RecommendationViewModel
    }

    private val _state = MutableStateFlow<UiState<List<Recommendation>>>(UiState.Loading)
    val state: StateFlow<UiState<List<Recommendation>>> = _state.asStateFlow()

    init {
        load()
    }

    fun load() {
        _state.value = UiState.Loading
        viewModelScope.launch {
            try {
                val recommendations = stockRepository.getRecommendations(horizon)
                _state.value = UiState.Success(recommendations)
            } catch (e: Exception) {
                _state.value = UiState.Error(
                    message = e.message ?: "Failed to load recommendations",
                    retry = ::load,
                )
            }
        }
    }
}

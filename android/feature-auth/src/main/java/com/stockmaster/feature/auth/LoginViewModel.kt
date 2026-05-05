package com.stockmaster.feature.auth

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.stockmaster.core.ui.UiState
import com.stockmaster.domain.model.AuthTokens
import com.stockmaster.domain.repository.AuthRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import timber.log.Timber
import javax.inject.Inject

@HiltViewModel
class LoginViewModel @Inject constructor(
    private val authRepository: AuthRepository,
    private val googleAuthManager: GoogleAuthManager,
) : ViewModel() {

    private val _loginState = MutableStateFlow<UiState<AuthTokens>>(UiState.Loading)
    val loginState: StateFlow<UiState<AuthTokens>> = _loginState.asStateFlow()

    private val _isIdle = MutableStateFlow(true)
    val isIdle: StateFlow<Boolean> = _isIdle.asStateFlow()

    fun loginWithGoogle(activityContext: android.content.Context) {
        if (!_isIdle.value) return

        _isIdle.value = false
        _loginState.value = UiState.Loading

        viewModelScope.launch {
            try {
                // Step 1: Get Firebase ID token via Credential Manager
                val firebaseIdToken = googleAuthManager.signIn(activityContext)

                // Step 2: Exchange for backend JWT
                val tokens = authRepository.loginWithGoogle(firebaseIdToken)

                _loginState.value = UiState.Success(tokens)
            } catch (e: Exception) {
                Timber.e(e, "Login failed")
                _loginState.value = UiState.Error(
                    message = e.message ?: "Login failed. Please try again.",
                    retry = { loginWithGoogle(activityContext) }
                )
            } finally {
                _isIdle.value = true
            }
        }
    }
}

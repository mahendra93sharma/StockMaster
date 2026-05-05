package com.stockmaster.app

import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import com.stockmaster.app.ui.theme.StockMasterTheme
import com.stockmaster.feature.auth.LoginScreen
import com.stockmaster.feature.auth.LoginViewModel

@Composable
fun StockMasterNavHost() {
    val navController = rememberNavController()

    StockMasterTheme {
        NavHost(navController = navController, startDestination = "login") {
            composable("login") {
                val viewModel: LoginViewModel = hiltViewModel()
                LoginScreen(
                    viewModel = viewModel,
                    onLoginSuccess = {
                        navController.navigate("main") {
                            popUpTo("login") { inclusive = true }
                        }
                    }
                )
            }
            composable("main") {
                MainScreen()
            }
        }
    }
}

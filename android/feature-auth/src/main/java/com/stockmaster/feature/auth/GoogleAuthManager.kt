package com.stockmaster.feature.auth

import android.content.Context
import androidx.credentials.CredentialManager
import androidx.credentials.GetCredentialRequest
import androidx.credentials.GetCredentialResponse
import com.google.android.libraries.identity.googleid.GetGoogleIdOption
import com.google.android.libraries.identity.googleid.GoogleIdTokenCredential
import com.google.firebase.auth.FirebaseAuth
import com.google.firebase.auth.GoogleAuthProvider
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.tasks.await
import timber.log.Timber
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class GoogleAuthManager @Inject constructor(
    @ApplicationContext private val context: Context,
) {
    private val credentialManager = CredentialManager.create(context)
    private val firebaseAuth = FirebaseAuth.getInstance()

    /**
     * Initiates Google sign-in via Credential Manager API.
     * Returns the Firebase ID token on success.
     */
    suspend fun signIn(activityContext: Context): String {
        val googleIdOption = GetGoogleIdOption.Builder()
            .setFilterByAuthorizedAccounts(false)
            .setAutoSelectEnabled(true)
            .setServerClientId(getWebClientId())
            .build()

        val request = GetCredentialRequest.Builder()
            .addCredentialOption(googleIdOption)
            .build()

        val response: GetCredentialResponse = credentialManager.getCredential(
            request = request,
            context = activityContext,
        )

        val googleIdTokenCredential = GoogleIdTokenCredential.createFrom(response.credential.data)
        val googleIdToken = googleIdTokenCredential.idToken

        // Exchange Google ID token for Firebase credential
        val firebaseCredential = GoogleAuthProvider.getCredential(googleIdToken, null)
        val authResult = firebaseAuth.signInWithCredential(firebaseCredential).await()

        // Get the Firebase ID token to send to our backend
        val firebaseIdToken = authResult.user?.getIdToken(false)?.await()?.token
            ?: throw IllegalStateException("Failed to get Firebase ID token")

        Timber.d("Firebase sign-in successful")
        return firebaseIdToken
    }

    fun signOut() {
        firebaseAuth.signOut()
    }

    private fun getWebClientId(): String {
        // This is read from google-services.json at build time via string resource
        return context.getString(com.stockmaster.feature.auth.R.string.default_web_client_id)
    }
}

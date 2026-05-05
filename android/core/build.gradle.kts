plugins {
    alias(libs.plugins.android.library)
    alias(libs.plugins.kotlin.android)
    alias(libs.plugins.kotlin.serialization)
    alias(libs.plugins.hilt)
    alias(libs.plugins.ksp)
}

android {
    namespace = "com.stockmaster.core"
    compileSdk = 34

    defaultConfig {
        minSdk = 26
    }

    buildFeatures {
        buildConfig = true
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = "17"
    }
}

dependencies {
    implementation(libs.core.ktx)
    implementation(libs.hilt.android)
    ksp(libs.hilt.compiler)

    // Network
    api(libs.retrofit)
    api(libs.retrofit.serialization)
    api(libs.okhttp)
    api(libs.okhttp.logging)
    api(libs.serialization.json)

    // DataStore
    api(libs.datastore)

    // Coroutines
    api(libs.coroutines.core)
    api(libs.coroutines.android)

    // Timber
    api(libs.timber)
}

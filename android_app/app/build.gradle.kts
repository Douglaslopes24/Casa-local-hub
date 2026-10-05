plugins {
    id("com.android.application")
}

android {
    namespace = "com.casalocal.hub"
    compileSdk = 37

    defaultConfig {
        applicationId = "com.casalocal.hub"
        minSdk = 26
        targetSdk = 36
        versionCode = 1
        versionName = "0.1.0"
    }

    buildTypes {
        release {
            isMinifyEnabled = false
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
}

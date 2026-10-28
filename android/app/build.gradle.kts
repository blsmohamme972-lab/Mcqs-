plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.plugin.compose")
    id("org.jetbrains.kotlin.plugin.serialization")
    id("com.google.devtools.ksp")
}

android {
    namespace = "com.mcqs.app"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.mcqs.app"
        minSdk = 26
        targetSdk = 35
        // CI passes the run number so every published build is a newer version.
        val build = System.getenv("BUILD_NUMBER")?.toIntOrNull() ?: 0
        versionCode = 100 + build
        versionName = "0.2.$build"
        buildConfigField("String", "UPDATE_INDEX_URL",
            "\"https://github.com/blsmohamme972-lab/Mcqs-/releases/latest/download/index.json\"")
    }

    // The signing key never lives in the repo: CI decodes it from the MCQS_KEYSTORE_B64 secret.
    // One fixed key means in-app updates install over the previous version.
    val keystorePath = System.getenv("MCQS_KEYSTORE_PATH")
    signingConfigs {
        if (keystorePath != null) {
            create("personal") {
                storeFile = file(keystorePath)
                storePassword = System.getenv("MCQS_KEYSTORE_PASSWORD")
                keyAlias = "mcqs"
                keyPassword = System.getenv("MCQS_KEYSTORE_PASSWORD")
            }
        }
    }

    buildTypes {
        val personal = signingConfigs.findByName("personal")
        debug {
            if (personal != null) signingConfig = personal
        }
        release {
            isMinifyEnabled = false
            signingConfig = personal
        }
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions {
        jvmTarget = "17"
    }
    buildFeatures {
        compose = true
        buildConfig = true
    }
    testOptions {
        unitTests.isIncludeAndroidResources = true
        unitTests.all {
            // Robolectric fetches its Android runtime itself; Maven Central rate-limits cloud builds.
            it.systemProperty("robolectric.dependency.repo.url", "https://maven-central.storage-download.googleapis.com/maven2")
        }
    }
}

ksp {
    arg("room.schemaLocation", "$projectDir/schemas")
}

dependencies {
    val composeBom = platform("androidx.compose:compose-bom:2024.12.01")
    implementation(composeBom)
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.compose.material:material-icons-core")
    implementation("androidx.compose.ui:ui-tooling-preview")
    debugImplementation("androidx.compose.ui:ui-tooling")

    implementation("androidx.core:core-ktx:1.15.0")
    implementation("androidx.activity:activity-compose:1.9.3")
    implementation("androidx.lifecycle:lifecycle-runtime-compose:2.8.7")
    implementation("androidx.lifecycle:lifecycle-viewmodel-compose:2.8.7")

    implementation("androidx.room:room-runtime:2.6.1")
    implementation("androidx.room:room-ktx:2.6.1")
    ksp("androidx.room:room-compiler:2.6.1")

    implementation("androidx.media3:media3-exoplayer:1.5.1")
    implementation("androidx.media3:media3-ui:1.5.1")

    implementation("org.jetbrains.kotlinx:kotlinx-serialization-json:1.7.3")

    testImplementation("junit:junit:4.13.2")
    testImplementation("org.robolectric:robolectric:4.14.1")
    testImplementation(composeBom)
    testImplementation("androidx.compose.ui:ui-test-junit4")
    debugImplementation("androidx.compose.ui:ui-test-manifest")
}

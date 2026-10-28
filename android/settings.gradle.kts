pluginManagement {
    repositories {
        google()
        // Google-hosted mirror of Maven Central (Central rate-limits CI/cloud builds).
        maven("https://maven-central.storage-download.googleapis.com/maven2/")
        mavenCentral()
        gradlePluginPortal()
    }
}
dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {
        google()
        // Google-hosted mirror of Maven Central (Central rate-limits CI/cloud builds).
        maven("https://maven-central.storage-download.googleapis.com/maven2/")
        mavenCentral()
    }
}
rootProject.name = "MCQs"
include(":app")

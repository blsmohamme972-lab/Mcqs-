package com.mcqs.app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.BackHandler
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import com.mcqs.app.data.Repository
import com.mcqs.app.ui.HomeScreen
import com.mcqs.app.ui.McqsTheme
import com.mcqs.app.ui.SceneDetailScreen
import com.mcqs.app.ui.ScenesScreen
import com.mcqs.app.ui.StudyScreen

/** Routes are "home", "study/<deck>", "scenes/<deck>", "scene/<deck>/<scene>" (ids never contain '/'). */
class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        val repo = Repository(applicationContext)
        setContent {
            McqsTheme {
                var stack by rememberSaveable { mutableStateOf(listOf("home")) }
                val push = remember { { route: String -> stack = stack + route } }
                val pop = { stack = stack.dropLast(1) }
                BackHandler(enabled = stack.size > 1) { pop() }

                val parts = stack.last().split('/')
                when (parts[0]) {
                    "study" -> StudyScreen(repo, parts[1], onBack = pop,
                        onOpenScene = { push("scene/${parts[1]}/$it") })
                    "scenes" -> ScenesScreen(repo, parts[1], onBack = pop,
                        onOpen = { push("scene/${parts[1]}/$it") })
                    "scene" -> SceneDetailScreen(repo, parts[1], parts[2], onBack = pop)
                    else -> HomeScreen(repo, onStudy = { push("study/$it") }, onScenes = { push("scenes/$it") })
                }
            }
        }
    }
}

package com.mcqs.app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.BackHandler
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material3.Icon
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.NavigationBarItemDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import com.mcqs.app.data.Repository
import com.mcqs.app.data.Sync
import com.mcqs.app.ui.HomeScreen
import com.mcqs.app.ui.Ink
import com.mcqs.app.ui.McqsTheme
import com.mcqs.app.ui.Panel
import com.mcqs.app.ui.Panel2
import com.mcqs.app.ui.Pink
import com.mcqs.app.ui.ReelsScreen
import com.mcqs.app.ui.SceneDetailScreen
import com.mcqs.app.ui.ScenesScreen
import com.mcqs.app.ui.StudyScreen
import com.mcqs.app.ui.TextLo

/** Routes are "home", "study/<deck>", "scenes/<deck>", "scene/<deck>/<scene>" (ids never contain '/'). */
class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        val repo = Repository(applicationContext)
        val sync = Sync(applicationContext, repo)
        setContent {
            McqsTheme {
                var stack by rememberSaveable { mutableStateOf(listOf("home")) }
                var tab by rememberSaveable { mutableIntStateOf(0) }
                val push = remember { { route: String -> stack = stack + route } }
                val pop = { stack = stack.dropLast(1) }
                BackHandler(enabled = stack.size > 1 || tab != 0) { if (stack.size > 1) pop() else tab = 0 }

                Box(Modifier.fillMaxSize().background(Ink)) {
                    val parts = stack.last().split('/')
                    when (parts[0]) {
                        "study" -> StudyScreen(repo, parts[1], onBack = pop, onOpenScene = { push("scene/${parts[1]}/$it") })
                        "scenes" -> ScenesScreen(repo, parts[1], onBack = pop, onOpen = { push("scene/${parts[1]}/$it") })
                        "scene" -> SceneDetailScreen(repo, parts[1], parts[2], onBack = pop)
                        else -> Column(Modifier.fillMaxSize()) {
                            Box(Modifier.weight(1f)) {
                                if (tab == 0) {
                                    HomeScreen(repo, sync, onStudy = { push("study/$it") }, onScenes = { push("scenes/$it") })
                                } else {
                                    ReelsScreen(repo, onStudy = { push("study/$it") }, onScene = { d, s -> push("scene/$d/$s") })
                                }
                            }
                            NavigationBar(containerColor = if (tab == 1) Color.Black else Panel) {
                                val colors = NavigationBarItemDefaults.colors(
                                    selectedIconColor = Pink, selectedTextColor = Pink,
                                    unselectedIconColor = TextLo, unselectedTextColor = TextLo,
                                    indicatorColor = Panel2,
                                )
                                NavigationBarItem(tab == 0, { tab = 0 }, { Icon(Icons.Filled.Home, null) },
                                    label = { Text("Decks") }, colors = colors)
                                NavigationBarItem(tab == 1, { tab = 1 }, { Icon(Icons.Filled.PlayArrow, null) },
                                    label = { Text("Reels") }, colors = colors)
                            }
                        }
                    }
                }
            }
        }
    }
}

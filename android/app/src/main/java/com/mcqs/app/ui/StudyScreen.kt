package com.mcqs.app.ui

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.lifecycle.ViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewModelScope
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.lifecycle.viewmodel.initializer
import androidx.lifecycle.viewmodel.viewModelFactory
import com.mcqs.app.data.CardEntity
import com.mcqs.app.data.DeckEntity
import com.mcqs.app.data.Repository
import com.mcqs.app.data.SceneEntity
import com.mcqs.app.pkg.CardType
import com.mcqs.app.pkg.RegionDef
import com.mcqs.app.pkg.manifestJson
import com.mcqs.app.srs.DAY_MS
import com.mcqs.app.srs.Rating
import com.mcqs.app.srs.formatInterval
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import kotlinx.serialization.builtins.ListSerializer
import kotlinx.serialization.builtins.serializer
import kotlin.random.Random

data class StudyUi(
    val loading: Boolean = true,
    val deck: DeckEntity? = null,
    val card: CardEntity? = null,
    val scene: SceneEntity? = null,
    val regions: List<RegionDef> = emptyList(),
    /** MCQ options in display order: (original index, text). */
    val options: List<Pair<Int, String>> = emptyList(),
    val chosen: Int? = null,
    val revealed: Boolean = false,
    val intervals: Map<Rating, String> = emptyMap(),
    val reviewedThisSession: Int = 0,
    val done: Boolean = false,
)

class StudyViewModel(private val repo: Repository, private val deckId: String) : ViewModel() {
    val ui = MutableStateFlow(StudyUi())
    private var shownAt = 0L

    init {
        viewModelScope.launch { loadNext() }
    }

    private suspend fun loadNext() {
        val deck = repo.dao.deck(deckId)
        val card = repo.nextCard(deckId)
        if (deck == null || card == null) {
            ui.update { StudyUi(loading = false, deck = deck, done = true, reviewedThisSession = it.reviewedThisSession) }
            return
        }
        val scene = card.sceneId?.let { repo.dao.scene(deckId, it) }
        val regions = scene?.let {
            manifestJson.decodeFromString(ListSerializer(RegionDef.serializer()), it.regionsJson)
        } ?: emptyList()
        val options = manifestJson.decodeFromString(ListSerializer(String.serializer()), card.optionsJson)
            .withIndex().map { it.index to it.value }
            // Reshuffle daily so the answer's position can't be memorised.
            .shuffled(Random(card.uid.hashCode() * 31L + System.currentTimeMillis() / DAY_MS))
        shownAt = System.currentTimeMillis()
        ui.update {
            StudyUi(loading = false, deck = deck, card = card, scene = scene, regions = regions,
                options = options, reviewedThisSession = it.reviewedThisSession)
        }
    }

    /** Called when the screen is (re)opened: a finished session may have new due cards by now. */
    fun refresh() {
        if (ui.value.done) viewModelScope.launch { loadNext() }
    }

    fun reveal() {
        val card = ui.value.card ?: return
        viewModelScope.launch {
            val now = System.currentTimeMillis()
            val preview = repo.scheduler.preview(repo.srsCard(card.uid, now), now)
            ui.update { it.copy(revealed = true, intervals = preview.mapValues { (_, ms) -> formatInterval(ms) }) }
        }
    }

    fun choose(originalIndex: Int) {
        if (ui.value.revealed) return
        ui.update { it.copy(chosen = originalIndex) }
        reveal()
    }

    fun answer(rating: Rating) {
        val card = ui.value.card ?: return
        viewModelScope.launch {
            repo.answer(card, rating, System.currentTimeMillis() - shownAt)
            ui.update { it.copy(reviewedThisSession = it.reviewedThisSession + 1) }
            loadNext()
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun StudyScreen(repo: Repository, deckId: String, onBack: () -> Unit, onOpenScene: (String) -> Unit) {
    val vm: StudyViewModel = viewModel(key = "study-$deckId", factory = viewModelFactory {
        initializer { StudyViewModel(repo, deckId) }
    })
    val ui by vm.ui.collectAsStateWithLifecycle()
    LaunchedEffect(Unit) { vm.refresh() }

    Scaffold(topBar = {
        TopAppBar(
            title = { Text(ui.deck?.title ?: "", maxLines = 1) },
            navigationIcon = {
                IconButton(onClick = onBack) { Icon(Icons.AutoMirrored.Filled.ArrowBack, "Back") }
            },
        )
    }) { padding ->
        Box(Modifier.padding(padding).fillMaxSize()) {
            when {
                ui.loading -> CircularProgressIndicator(Modifier.align(Alignment.Center))
                ui.done -> DoneView(ui.reviewedThisSession, onBack, Modifier.align(Alignment.Center))
                else -> CardView(ui, vm, onOpenScene)
            }
        }
    }
}

@Composable
private fun DoneView(reviewed: Int, onBack: () -> Unit, modifier: Modifier) {
    Column(modifier.padding(24.dp), horizontalAlignment = Alignment.CenterHorizontally) {
        Text("All caught up", style = MaterialTheme.typography.headlineSmall)
        Spacer(Modifier.height(8.dp))
        Text(
            "Reviewed $reviewed card(s) this session.\nCome back later for the next due cards.",
            textAlign = TextAlign.Center,
        )
        Spacer(Modifier.height(16.dp))
        Button(onClick = onBack) { Text("Back to decks") }
    }
}

@Composable
private fun CardView(ui: StudyUi, vm: StudyViewModel, onOpenScene: (String) -> Unit) {
    val card = ui.card ?: return
    val deck = ui.deck ?: return
    Column(Modifier.fillMaxSize()) {
        Column(
            Modifier
                .weight(1f)
                .verticalScroll(rememberScrollState())
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Text(card.front, style = MaterialTheme.typography.titleMedium)

            val imageRel = if (card.type == CardType.OCCLUSION) ui.scene?.image else card.image
            val bitmap = rememberBitmap(imageRel?.let { java.io.File(deck.dir, it) })
            if (bitmap != null) {
                SceneImage(
                    bitmap = bitmap,
                    regions = if (card.type == CardType.OCCLUSION) ui.regions else emptyList(),
                    targetId = card.regionId,
                    revealed = ui.revealed,
                )
            }

            if (card.type == CardType.MCQ) {
                for ((index, text) in ui.options) {
                    McqOption(text, index, card.answer, ui.chosen, ui.revealed) { vm.choose(index) }
                }
            }

            if (ui.revealed) {
                HorizontalDivider()
                card.back?.let { Text(it, style = MaterialTheme.typography.bodyLarge) }
                card.explanation?.let { Text(it, style = MaterialTheme.typography.bodyMedium) }
                card.source?.let {
                    Text("Source: $it", style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
                val scene = ui.scene
                if (scene != null && (scene.video != null || card.type != CardType.OCCLUSION)) {
                    OutlinedButton(onClick = { onOpenScene(scene.id) }) {
                        Icon(Icons.Filled.PlayArrow, null)
                        Text(" Scene: ${scene.title}")
                    }
                }
            }
        }

        Surface(tonalElevation = 3.dp) {
            Box(Modifier.fillMaxWidth().padding(12.dp)) {
                when {
                    ui.revealed -> RatingRow(ui, wrongMcq = card.type == CardType.MCQ && ui.chosen != card.answer, vm::answer)
                    card.type == CardType.MCQ -> Text("Choose an answer", Modifier.align(Alignment.Center))
                    else -> Button(onClick = vm::reveal, modifier = Modifier.fillMaxWidth().height(52.dp)) {
                        Text("Show answer")
                    }
                }
            }
        }
    }
}

@Composable
private fun McqOption(text: String, index: Int, answer: Int?, chosen: Int?, revealed: Boolean, onClick: () -> Unit) {
    val color = when {
        !revealed -> MaterialTheme.colorScheme.outline
        index == answer -> CorrectGreen
        index == chosen -> WrongRed
        else -> MaterialTheme.colorScheme.outlineVariant
    }
    OutlinedButton(
        onClick = onClick,
        enabled = !revealed || index == answer || index == chosen,
        border = BorderStroke(if (revealed && (index == answer || index == chosen)) 2.dp else 1.dp, color),
        modifier = Modifier.fillMaxWidth(),
    ) {
        Text(text, Modifier.fillMaxWidth(), textAlign = TextAlign.Start,
            color = if (revealed && index == answer) CorrectGreen else Color.Unspecified)
    }
}

@Composable
private fun RatingRow(ui: StudyUi, wrongMcq: Boolean, onRate: (Rating) -> Unit) {
    Row(horizontalArrangement = Arrangement.spacedBy(6.dp), modifier = Modifier.fillMaxWidth()) {
        for (rating in Rating.entries) {
            // A wrong MCQ answer can only be rated Again: the card wasn't known.
            val enabled = !wrongMcq || rating == Rating.Again
            val colors = when (rating) {
                Rating.Again -> ButtonDefaults.buttonColors(containerColor = WrongRed, contentColor = Color.White)
                Rating.Good -> ButtonDefaults.buttonColors()
                else -> ButtonDefaults.filledTonalButtonColors()
            }
            Button(onClick = { onRate(rating) }, enabled = enabled, colors = colors,
                modifier = Modifier.weight(1f).height(56.dp),
                contentPadding = ButtonDefaults.TextButtonContentPadding) {
                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    Text(rating.name, style = MaterialTheme.typography.labelLarge)
                    Text(ui.intervals[rating] ?: "", style = MaterialTheme.typography.labelSmall)
                }
            }
        }
    }
}

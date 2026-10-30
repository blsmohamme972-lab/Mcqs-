package com.mcqs.app.ui

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.core.tween
import androidx.compose.animation.expandVertically
import androidx.compose.animation.fadeIn
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.SolidColor
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
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.TextButton
import androidx.compose.ui.platform.LocalClipboardManager
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.AnnotatedString
import android.widget.Toast
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
import com.mcqs.app.data.GptCopy
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

    /** "Copy for GPT": the next [n] cards (due first, then new) as text for a voice examiner; null when none. */
    suspend fun gptText(n: Int): Pair<Int, String>? {
        val deck = ui.value.deck ?: repo.dao.deck(deckId) ?: return null
        val now = System.currentTimeMillis()
        val batch = repo.nextBatch(deckId, n, now)
        return if (batch.isEmpty()) null else batch.size to GptCopy.text(deck.title, batch, now)
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

    Scaffold(containerColor = Ink, topBar = {
        TopAppBar(
            title = { Text(ui.deck?.title ?: "", maxLines = 1, style = MaterialTheme.typography.titleMedium) },
            navigationIcon = {
                IconButton(onClick = onBack) { Icon(Icons.AutoMirrored.Filled.ArrowBack, "Back") }
            },
            actions = { CopyForGpt(vm) },
            colors = TopAppBarDefaults.topAppBarColors(containerColor = Ink),
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

/** Copy 10 / 20 / 30 questions with their answers for a ChatGPT voice examiner, then rate them here as usual. */
@Composable
private fun CopyForGpt(vm: StudyViewModel) {
    val context = LocalContext.current
    val clipboard = LocalClipboardManager.current
    val scope = rememberCoroutineScope()
    var open by remember { mutableStateOf(false) }
    Box {
        TextButton(onClick = { open = true }) { Text("Copy for GPT", color = Cyan, style = MaterialTheme.typography.labelLarge) }
        DropdownMenu(expanded = open, onDismissRequest = { open = false }) {
            for (n in listOf(10, 20, 30)) {
                DropdownMenuItem(text = { Text("Copy $n questions") }, onClick = {
                    open = false
                    scope.launch {
                        val copied = vm.gptText(n)
                        if (copied == null) {
                            Toast.makeText(context, "No questions left to copy", Toast.LENGTH_SHORT).show()
                        } else {
                            clipboard.setText(AnnotatedString(copied.second))
                            Toast.makeText(context, "Copied ${copied.first} questions: paste them in ChatGPT", Toast.LENGTH_SHORT).show()
                        }
                    }
                })
            }
        }
    }
}

@Composable
private fun DoneView(reviewed: Int, onBack: () -> Unit, modifier: Modifier) {
    Column(modifier.padding(24.dp), horizontalAlignment = Alignment.CenterHorizontally) {
        Text("All caught up", style = MaterialTheme.typography.headlineLarge.brand())
        Spacer(Modifier.height(8.dp))
        Text(
            "Reviewed $reviewed card(s) this session.\nCome back later for the next due cards.",
            textAlign = TextAlign.Center, color = TextLo,
        )
        Spacer(Modifier.height(20.dp))
        GradientButton(onClick = onBack) { Text("Back to decks", style = MaterialTheme.typography.labelLarge, color = Color.White) }
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
                .padding(horizontal = 16.dp, vertical = 8.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp),
        ) {
            Text(card.front, style = MaterialTheme.typography.titleLarge)

            val imageRel = if (card.type == CardType.OCCLUSION) ui.scene?.image else card.image
            val bitmap = rememberBitmap(imageRel?.let { java.io.File(deck.dir, it) })
            if (bitmap != null) {
                SceneImage(
                    bitmap = bitmap,
                    regions = if (card.type == CardType.OCCLUSION) ui.regions else emptyList(),
                    targetId = card.regionId,
                    revealed = ui.revealed,
                    modifier = Modifier.clip(RoundedCornerShape(20.dp)).border(1.dp, Line, RoundedCornerShape(20.dp)),
                )
            }

            if (card.type == CardType.MCQ) {
                for ((index, text) in ui.options) {
                    McqOption(text, index, card.answer, ui.chosen, ui.revealed) { vm.choose(index) }
                }
            }

            AnimatedVisibility(ui.revealed, enter = fadeIn(tween(180)) + expandVertically(tween(180))) {
                Column(
                    Modifier.fillMaxWidth().clip(RoundedCornerShape(20.dp)).background(Panel)
                        .border(1.dp, Line, RoundedCornerShape(20.dp)).padding(16.dp),
                    verticalArrangement = Arrangement.spacedBy(10.dp),
                ) {
                    card.back?.let { Text(it, style = MaterialTheme.typography.titleMedium.copy(color = Cyan)) }
                    card.explanation?.let { Text(it, style = MaterialTheme.typography.bodyMedium, color = TextHi) }
                    card.source?.let { Text("Source: $it", style = MaterialTheme.typography.labelSmall, color = TextLo) }
                    val scene = ui.scene
                    if (scene != null && (scene.video != null || scene.lectureJson != null || card.type != CardType.OCCLUSION)) {
                        GradientButton(onClick = { onOpenScene(scene.id) }, brush = CoolGradient,
                            contentPadding = PaddingValues(horizontal = 16.dp, vertical = 8.dp)) {
                            Row(verticalAlignment = Alignment.CenterVertically) {
                                Icon(Icons.Filled.PlayArrow, null, tint = Color.White)
                                Text(" Watch: ${scene.title}", color = Color.White, style = MaterialTheme.typography.labelLarge,
                                    maxLines = 1)
                            }
                        }
                    }
                }
            }
        }

        Box(Modifier.fillMaxWidth().background(Panel).navigationBarsPadding().padding(12.dp)) {
            when {
                ui.revealed -> RatingRow(ui, wrongMcq = card.type == CardType.MCQ && ui.chosen != card.answer, vm::answer)
                card.type == CardType.MCQ -> Text("Choose an answer", Modifier.align(Alignment.Center).padding(14.dp), color = TextLo)
                else -> GradientButton(onClick = vm::reveal, modifier = Modifier.fillMaxWidth().height(54.dp)) {
                    Text("Show answer", style = MaterialTheme.typography.titleMedium, color = Color.White)
                }
            }
        }
    }
}

@Composable
private fun McqOption(text: String, index: Int, answer: Int?, chosen: Int?, revealed: Boolean, onClick: () -> Unit) {
    val (border, fill, textColor) = when {
        !revealed -> Triple(Line, Panel, TextHi)
        index == answer -> Triple(CorrectGreen, CorrectGreen.copy(alpha = 0.12f), CorrectGreen)
        index == chosen -> Triple(WrongRed, WrongRed.copy(alpha = 0.12f), WrongRed)
        else -> Triple(Line, Panel, TextLo.copy(alpha = 0.6f))
    }
    Text(
        text,
        style = MaterialTheme.typography.bodyLarge,
        color = textColor,
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(16.dp))
            .background(fill)
            .border(if (revealed && (index == answer || index == chosen)) 2.dp else 1.dp, border, RoundedCornerShape(16.dp))
            .clickable(enabled = !revealed, onClick = onClick)
            .padding(horizontal = 16.dp, vertical = 14.dp),
    )
}

@Composable
private fun RatingRow(ui: StudyUi, wrongMcq: Boolean, onRate: (Rating) -> Unit) {
    Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.fillMaxWidth()) {
        for (rating in Rating.entries) {
            // A wrong MCQ answer can only be rated Again: the card wasn't known.
            val enabled = !wrongMcq || rating == Rating.Again
            val brush = when (rating) {
                Rating.Again -> SolidColor(WrongRed)
                Rating.Hard -> SolidColor(Panel2)
                Rating.Good -> BrandGradient
                Rating.Easy -> CoolGradient
            }
            GradientButton(onClick = { onRate(rating) }, enabled = enabled, brush = brush,
                modifier = Modifier.weight(1f).height(58.dp), contentPadding = PaddingValues(4.dp)) {
                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    Text(rating.name, style = MaterialTheme.typography.labelLarge, color = Color.White)
                    Text(ui.intervals[rating] ?: "", style = MaterialTheme.typography.labelSmall, color = Color.White.copy(alpha = 0.8f))
                }
            }
        }
    }
}

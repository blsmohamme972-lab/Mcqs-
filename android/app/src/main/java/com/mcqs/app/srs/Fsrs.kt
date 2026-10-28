package com.mcqs.app.srs

import kotlin.math.exp
import kotlin.math.floor
import kotlin.math.max
import kotlin.math.min
import kotlin.math.pow
import kotlin.math.roundToLong
import kotlin.random.Random

/**
 * FSRS-6 scheduler, a line-by-line port of py-fsrs 6.3.2 (`fsrs.scheduler.Scheduler`).
 * Times are epoch milliseconds (UTC). Verified against py-fsrs by `FsrsTest` golden vectors.
 */
enum class CardState(val code: Int) {
    Learning(1), Review(2), Relearning(3);

    companion object {
        fun of(code: Int) = entries.first { it.code == code }
    }
}

enum class Rating(val value: Int) {
    Again(1), Hard(2), Good(3), Easy(4);

    companion object {
        fun of(value: Int) = entries.first { it.value == value }
    }
}

data class SrsCard(
    val state: CardState = CardState.Learning,
    val step: Int? = 0,
    val stability: Double? = null,
    val difficulty: Double? = null,
    val due: Long,
    val lastReview: Long? = null,
)

const val MINUTE_MS = 60_000L
const val DAY_MS = 86_400_000L

val DEFAULT_PARAMETERS = doubleArrayOf(
    0.212, 1.2931, 2.3065, 8.2956, 6.4133, 0.8334, 3.0194, 0.001, 1.8722, 0.1666, 0.796,
    1.4835, 0.0614, 0.2629, 1.6483, 0.6014, 1.8729, 0.5425, 0.0912, 0.0658, 0.1542,
)

private const val STABILITY_MIN = 0.001
private const val MIN_DIFFICULTY = 1.0
private const val MAX_DIFFICULTY = 10.0

/** Python's round(): half to even. */
private fun pyRound(x: Double): Long = Math.rint(x).toLong()

/** Python's timedelta.days: floor of whole days. */
private fun floorDays(ms: Long): Long = Math.floorDiv(ms, DAY_MS)

class Scheduler(
    private val w: DoubleArray = DEFAULT_PARAMETERS,
    val desiredRetention: Double = 0.9,
    val learningSteps: List<Long> = listOf(1 * MINUTE_MS, 10 * MINUTE_MS),
    val relearningSteps: List<Long> = listOf(10 * MINUTE_MS),
    val maximumInterval: Int = 36500,
    val enableFuzzing: Boolean = true,
    private val random: Random = Random.Default,
) {
    init {
        require(w.size == 21) { "Expected 21 parameters, got ${w.size}" }
    }

    private val decay = -w[20]
    private val factor = 0.9.pow(1 / decay) - 1

    fun retrievability(card: SrsCard, now: Long): Double {
        val last = card.lastReview ?: return 0.0
        val s = card.stability ?: return 0.0
        val elapsedDays = max(0L, floorDays(now - last))
        return (1 + factor * elapsedDays / s).pow(decay)
    }

    fun review(card: SrsCard, rating: Rating, now: Long): SrsCard {
        val daysSinceLast = card.lastReview?.let { floorDays(now - it) }
        var state = card.state
        var step = card.step
        var s = card.stability
        var d = card.difficulty
        val nextInterval: Long

        when (card.state) {
            CardState.Learning, CardState.Relearning -> {
                val steps = if (card.state == CardState.Learning) learningSteps else relearningSteps
                val st = checkNotNull(step)
                if (card.state == CardState.Learning && (s == null || d == null)) {
                    s = initialStability(rating)
                    d = clampDifficulty(initialDifficulty(rating))
                } else if (daysSinceLast != null && daysSinceLast < 1) {
                    s = shortTermStability(s!!, rating)
                    d = nextDifficulty(d!!, rating)
                } else {
                    s = nextStability(d!!, s!!, retrievability(card, now), rating)
                    d = nextDifficulty(d, rating)
                }

                if (steps.isEmpty() || (st >= steps.size && rating != Rating.Again)) {
                    state = CardState.Review
                    step = null
                    nextInterval = nextIntervalDays(s) * DAY_MS
                } else {
                    when (rating) {
                        Rating.Again -> {
                            step = 0
                            nextInterval = steps[0]
                        }
                        Rating.Hard -> nextInterval = when {
                            st == 0 && steps.size == 1 -> (steps[0] * 1.5).toLong()
                            st == 0 && steps.size >= 2 -> (steps[0] + steps[1]) / 2
                            else -> steps[st]
                        }
                        Rating.Good -> if (st + 1 == steps.size) {
                            state = CardState.Review
                            step = null
                            nextInterval = nextIntervalDays(s) * DAY_MS
                        } else {
                            step = st + 1
                            nextInterval = steps[st + 1]
                        }
                        Rating.Easy -> {
                            state = CardState.Review
                            step = null
                            nextInterval = nextIntervalDays(s) * DAY_MS
                        }
                    }
                }
            }

            CardState.Review -> {
                s = if (daysSinceLast != null && daysSinceLast < 1) {
                    shortTermStability(s!!, rating)
                } else {
                    nextStability(d!!, s!!, retrievability(card, now), rating)
                }
                d = nextDifficulty(d!!, rating)
                if (rating == Rating.Again && relearningSteps.isNotEmpty()) {
                    state = CardState.Relearning
                    step = 0
                    nextInterval = relearningSteps[0]
                } else {
                    nextInterval = nextIntervalDays(s) * DAY_MS
                }
            }
        }

        val finalInterval = if (enableFuzzing && state == CardState.Review) fuzz(nextInterval) else nextInterval
        return SrsCard(state, step, s, d, due = now + finalInterval, lastReview = now)
    }

    /** Preview of the due time for each rating, for labelling the answer buttons. */
    fun preview(card: SrsCard, now: Long): Map<Rating, Long> =
        Rating.entries.associateWith { review(card, it, now).due - now }

    private fun clampDifficulty(d: Double) = min(max(d, MIN_DIFFICULTY), MAX_DIFFICULTY)
    private fun clampStability(s: Double) = max(s, STABILITY_MIN)

    private fun initialStability(r: Rating) = clampStability(w[r.value - 1])

    private fun initialDifficulty(r: Rating) = w[4] - exp(w[5] * (r.value - 1)) + 1

    private fun nextIntervalDays(s: Double): Long {
        val raw = (s / factor) * (desiredRetention.pow(1 / decay) - 1)
        return min(max(pyRound(raw), 1L), maximumInterval.toLong())
    }

    private fun shortTermStability(s: Double, r: Rating): Double {
        var inc = exp(w[17] * (r.value - 3 + w[18])) * s.pow(-w[19])
        if (r != Rating.Again) inc = max(inc, 1.0)
        return clampStability(s * inc)
    }

    private fun nextDifficulty(d: Double, r: Rating): Double {
        val arg1 = initialDifficulty(Rating.Easy)
        val delta = -(w[6] * (r.value - 3))
        val arg2 = d + (10.0 - d) * delta / 9.0
        return clampDifficulty(w[7] * arg1 + (1 - w[7]) * arg2)
    }

    private fun nextStability(d: Double, s: Double, r: Double, rating: Rating): Double {
        val next = if (rating == Rating.Again) {
            min(
                w[11] * d.pow(-w[12]) * ((s + 1).pow(w[13]) - 1) * exp((1 - r) * w[14]),
                s / exp(w[17] * w[18]),
            )
        } else {
            val hardPenalty = if (rating == Rating.Hard) w[15] else 1.0
            val easyBonus = if (rating == Rating.Easy) w[16] else 1.0
            s * (1 + exp(w[8]) * (11 - d) * s.pow(-w[9]) * (exp((1 - r) * w[10]) - 1) * hardPenalty * easyBonus)
        }
        return clampStability(next)
    }

    internal fun fuzz(intervalMs: Long): Long {
        val days = floorDays(intervalMs)
        if (days < 2.5) return intervalMs
        var delta = 1.0
        for ((start, end, f) in FUZZ_RANGES) {
            delta += f * max(min(days.toDouble(), end) - start, 0.0)
        }
        var minIvl = max(2L, pyRound(days - delta))
        val maxIvl = min(pyRound(days + delta), maximumInterval.toLong())
        minIvl = min(minIvl, maxIvl)
        val fuzzed = random.nextDouble() * (maxIvl - minIvl + 1) + minIvl
        return min(pyRound(fuzzed), maximumInterval.toLong()) * DAY_MS
    }

    private companion object {
        val FUZZ_RANGES = listOf(
            Triple(2.5, 7.0, 0.15),
            Triple(7.0, 20.0, 0.1),
            Triple(20.0, Double.POSITIVE_INFINITY, 0.05),
        )
    }
}

/** Human label for an interval: "1m", "10m", "3d", "2mo", "1.2y". */
fun formatInterval(ms: Long): String {
    val minutes = ms / MINUTE_MS.toDouble()
    val days = ms / DAY_MS.toDouble()
    return when {
        minutes < 60 -> "${max(1L, minutes.roundToLong())}m"
        days < 1 -> "${(minutes / 60).roundToLong()}h"
        days < 30 -> "${floor(days + 0.5).toLong()}d"
        days < 365 -> "${(days / 30).roundToLong()}mo"
        else -> "%.1fy".format(days / 365)
    }
}

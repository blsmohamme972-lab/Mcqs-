"""Compartment-pressure chart for the 30 s compartment syndrome lesson.

Renders a transparent overlay that FFmpeg places over the 3D layer from
11.0 s to 24.4 s (see ../ffmpeg/compose.sh). The pressure curve is the same
function as `pressure()` in ../compartment_3d.src.html, so both stay in sync.

Uses Text only (Pango), so no LaTeX install is needed.

Check without rendering:  manim --dry_run pressure_curve.py PressureCurve
Render (alpha .mov):      manim -qh -t --fps 30 pressure_curve.py PressureCurve
"""
from manim import (
    DOWN, LEFT, RIGHT, UP, Axes, DashedLine, Dot, Line, Rectangle,
    RoundedRectangle, Scene, Text, ValueTracker, VGroup, always_redraw, config,
    interpolate_color, linear, ManimColor,
)

config.pixel_width = 960
config.pixel_height = 640
config.frame_width = 9.6
config.frame_height = 6.4
config.frame_rate = 30
config.background_opacity = 0.0  # overlay layer

T0, T1 = 11.0, 24.4            # lesson seconds this overlay covers
DIASTOLIC, THRESHOLD = 70, 40  # ΔP = 30 mmHg (McQueen & Court-Brown 1996, PMID 8898137)

PANEL = ManimColor("#0b121a")
LINE = ManimColor("#263445")
FG = ManimColor("#eef3f7")
MUTED = ManimColor("#8d9fb2")
ANT = ManimColor("#35c3b6")
DANGER = ManimColor("#ff4040")
NERVE = ManimColor("#ffd54f")
MONO = "JetBrains Mono"


def smooth(a, b, x):
    t = min(1.0, max(0.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)


def pressure(t):
    """mmHg at lesson time t; mirrors pressure() in compartment_3d.src.html."""
    if t < 11.6:
        return 8.0
    if t < 21.6:
        return 8 + (50 - 8) * smooth(11.6, 19.6, t)
    return 50 + (12 - 50) * smooth(21.8, 23.4, t)


class PressureCurve(Scene):
    def construct(self):
        clock = ValueTracker(T0)
        now = clock.get_value

        card = RoundedRectangle(width=9.2, height=6.0, corner_radius=0.18,
                                fill_color=PANEL, fill_opacity=0.82, stroke_color=LINE, stroke_width=2)

        axes = Axes(
            x_range=[T0, T1, 2], y_range=[0, 80, 20], x_length=7.6, y_length=3.6,
            axis_config={"color": LINE, "stroke_width": 2, "include_ticks": False},
        ).shift(DOWN * 0.55 + RIGHT * 0.2)
        y_labels = VGroup(*[
            Text(str(v), font=MONO, font_size=20, color=MUTED).next_to(axes.c2p(T0, v), LEFT, buff=0.15)
            for v in (0, 20, 40, 60, 80)
        ])

        danger_zone = Rectangle(
            width=axes.x_length, height=axes.c2p(0, DIASTOLIC)[1] - axes.c2p(0, THRESHOLD)[1],
            fill_color=DANGER, fill_opacity=0.08, stroke_width=0,
        ).move_to(axes.c2p((T0 + T1) / 2, (DIASTOLIC + THRESHOLD) / 2))
        diastolic = DashedLine(axes.c2p(T0, DIASTOLIC), axes.c2p(T1, DIASTOLIC), color=FG, stroke_width=2, dash_length=0.12)
        threshold = DashedLine(axes.c2p(T0, THRESHOLD), axes.c2p(T1, THRESHOLD), color=DANGER, stroke_width=3, dash_length=0.12)
        dia_lbl = Text("diastolic 70", font=MONO, font_size=20, color=FG).next_to(diastolic, UP, buff=0.08).align_to(diastolic, RIGHT)
        thr_lbl = Text("ΔP ≤ 30 → 40 mmHg", font=MONO, font_size=20, color=DANGER).next_to(threshold, DOWN, buff=0.08).align_to(threshold, RIGHT)

        def colour_at(t):
            return DANGER if DIASTOLIC - pressure(t) <= 30 else ANT

        curve = always_redraw(lambda: axes.plot(
            pressure, x_range=[T0, max(T0 + 0.05, now()), 0.05],
            color=colour_at(now()), stroke_width=6,
        ))
        dot = always_redraw(lambda: Dot(axes.c2p(now(), pressure(now())), radius=0.09, color=colour_at(now())))
        gap = always_redraw(lambda: Line(axes.c2p(now(), DIASTOLIC), axes.c2p(now(), pressure(now())), color=NERVE, stroke_width=4))

        reading = always_redraw(lambda: VGroup(
            Text(f"{pressure(now()):.0f}", font=MONO, font_size=54, weight="BOLD", color=colour_at(now())),
            Text("mmHg", font=MONO, font_size=24, color=MUTED),
        ).arrange(RIGHT, buff=0.15, aligned_edge=DOWN).to_corner(UP + LEFT, buff=0.75))
        delta = always_redraw(lambda: VGroup(
            Text("ΔP", font=MONO, font_size=26, color=MUTED),
            Text(f"{DIASTOLIC - pressure(now()):.0f}", font=MONO, font_size=34, weight="BOLD",
                 color=interpolate_color(NERVE, DANGER, smooth(36, 30, DIASTOLIC - pressure(now())))),
        ).arrange(RIGHT, buff=0.15).to_corner(UP + RIGHT, buff=0.75))
        note = Text("compartment pressure · illustrative values", font=MONO, font_size=18, color=MUTED).next_to(card.get_bottom(), UP, buff=0.22)

        static = VGroup(card, danger_zone, axes, y_labels, diastolic, threshold, dia_lbl, thr_lbl, note)
        self.add(static, curve, gap, dot, reading, delta)

        # One linear pass of lesson time keeps every frame locked to the 3D timeline.
        self.play(clock.animate.set_value(T1), run_time=T1 - T0, rate_func=linear)

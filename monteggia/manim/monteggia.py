"""Monteggia fracture, 30 s, 2D, keywords only. Manim version of ../monteggia.html.

Same bone outlines (the SVG path strings are shared), same timeline in seconds, same
Manim CE colours. Text only (Pango), so no LaTeX install is needed. No audio.

Check without rendering:  manim --dry_run monteggia.py Monteggia
Render:                   manim -qh --fps 30 monteggia.py Monteggia

Sources: Bado JL, Clin Orthop Relat Res 1967;50:71-86 (PMID 6029027);
Ring D, Jupiter JB, Simpson NS, J Bone Joint Surg Am 1998;80(12):1733-44 (PMID 9875931).
Schematic lateral view, elbow extended, anterior up.
"""
from manim import (
    BLUE_C, DEGREES, DOWN, GOLD_C, GREEN_C, GREY_B, GREY_C, LEFT, RED_C, RIGHT, UL, UP, WHITE, YELLOW_C,
    BLACK, ORIGIN, Arc, Circle, Rectangle, Create, DashedVMobject, DrawBorderThenFill, FadeIn, FadeOut, Flash, GrowArrow,
    Arrow, Indicate, LaggedStart, Line, RoundedRectangle, Scene, Text, ValueTracker, VGroup, VMobject, Write,
    always_redraw, config, linear, smooth,
)
from manim.mobject.svg.svg_mobject import VMobjectFromSVGPath
import numpy as np
import svgelements as se

config.frame_rate = 30
MUTED = "#8a8a93"
FONT = "STIX Two Text"

# SVG path strings shared with ../monteggia.html (SVG units, y down)
HUMERUS = "M0 208 L270 200 C320 196 350 205 362 222 L362 290 C345 306 310 306 280 300 L0 292 Z"
ULNA_FULL = ("M340 252 Q336 238 328 234 Q316 244 318 270 Q322 318 372 342 L540 350 L940 342 Q960 336 958 328 "
             "Q958 318 940 316 L486 298 Q446 290 430 268 A46 46 0 1 1 340 252 Z")
ULNA_PROX = ("M340 252 Q336 238 328 234 Q316 244 318 270 Q322 318 372 342 L540 350 L548 338 L536 326 L546 314 "
             "L540 304 L486 298 Q446 290 430 268 A46 46 0 1 1 340 252 Z")
ULNA_DIST = "M540 304 L546 314 L536 326 L548 338 L540 350 L940 342 Q960 336 958 328 Q958 318 940 316 Z"
RADIUS = ("M428 200 Q428 194 436 194 L446 194 Q452 194 452 200 L452 212 L482 214 C600 208 800 198 942 196 "
          "Q960 200 958 230 Q958 262 940 266 C800 258 620 250 524 246 Q508 254 494 246 L482 240 L452 242 "
          "L452 252 Q452 258 446 258 L436 258 Q428 258 428 252 Z")
PIVOT_SVG = (950, 290)
NERVE = [((230, 150), 0), ((380, 168), 0), ((466, 190), 1), ((496, 222), 1), ((486, 266), 1), ((620, 286), 1), ((900, 292), 1)]

S = 0.0105                      # SVG unit -> Manim unit
OFFSET = np.array([-1.6, 0.1, 0])


def pt(x, y):
    return np.array([(x - 500) * S, -(y - 280) * S, 0]) + OFFSET


def shape(d, colour, fill=0.18, width=4):
    m = VMobjectFromSVGPath(se.Path(d))
    m.flip(RIGHT)                                   # SVG y down -> Manim y up
    m.scale(S, about_point=np.array([0, 0, 0]))
    # place by the path's own SVG bounding box so every shape shares one frame
    bb = se.Path(d).bbox()
    m.move_to(pt((bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2))
    return m.set_stroke(colour, width).set_fill(colour, fill)


def dislocated(points, d):
    """Rotate about the wrist and shorten: the forearm unit's pose for 0 <= d <= 1 (anterior = up)."""
    piv = pt(*PIVOT_SVG)
    a = -7 * d * DEGREES                            # clockwise on screen
    rot = np.array([[np.cos(a), -np.sin(a), 0], [np.sin(a), np.cos(a), 0], [0, 0, 1]])
    shift = np.array([-18 * S * d, 6 * S * d, 0])
    return [piv + rot @ (p - piv) + shift for p in points]


class Monteggia(Scene):
    def until(self, t):
        if t - self.time > 1e-3:
            self.wait(t - self.time)

    def keywords(self, items):
        """items: (text, colour); stacked in a column on the right."""
        g = VGroup(*[Text(s, font=FONT, font_size=30, color=c) for s, c in items]).arrange(DOWN, aligned_edge=LEFT, buff=0.3)
        return g.move_to(RIGHT * 5.0 + UP * 0.4, aligned_edge=LEFT).shift(LEFT * 0.9)

    def construct(self):
        # ---- title ----
        title = Text("Monteggia fracture", font=FONT, weight="BOLD", font_size=64)
        sub = Text("proximal ulna fracture + radial head dislocation", font=FONT, slant="ITALIC", font_size=28, color=GREY_B).next_to(title, DOWN)
        self.play(Write(title), run_time=1.6)
        self.play(FadeIn(sub, shift=UP * 0.2), run_time=0.5)
        self.until(2.6)
        self.play(title.animate.scale(0.55).to_corner(UL), FadeOut(sub), run_time=0.7)

        # ---- normal anatomy ----
        humerus = shape(HUMERUS, GREY_B, 0.12)
        trochlea = DashedVMobject(Circle(radius=40 * S, color=GREY_C).move_to(pt(384, 266)), num_dashes=28)
        capitellum = Circle(radius=32 * S, color=GOLD_C).set_fill(GOLD_C, 0.22).move_to(pt(392, 226))
        ulna = shape(ULNA_FULL, BLUE_C)
        radius = shape(RADIUS, GREEN_C)
        self.play(LaggedStart(DrawBorderThenFill(humerus), Create(trochlea), DrawBorderThenFill(capitellum),
                              DrawBorderThenFill(ulna), DrawBorderThenFill(radius), lag_ratio=0.3), run_time=1.7)
        labels = VGroup(
            Text("Humerus", font=FONT, font_size=26, color=GREY_B).move_to(pt(150, 180)),
            Text("Capitellum", font=FONT, font_size=22, color=GOLD_C).move_to(pt(392, 172)),
            Text("Radius", font=FONT, font_size=26, color=GREEN_C).move_to(pt(720, 176)),
            Text("Ulna", font=FONT, font_size=26, color=BLUE_C).move_to(pt(720, 396)),
        )
        tag = Text("lateral view · anterior ↑", font=FONT, slant="ITALIC", font_size=20, color=MUTED).move_to(pt(110, 116))
        self.play(LaggedStart(*[FadeIn(m) for m in labels], FadeIn(tag), lag_ratio=0.2), run_time=0.7)

        # ---- radiocapitellar line ----
        d = ValueTracker(0)
        rcl_ends = [pt(300, 226), pt(770, 226)]
        rcl_colour = [YELLOW_C]
        rcl = always_redraw(lambda: DashedVMobject(Line(*dislocated(rcl_ends, d.get_value()), color=rcl_colour[0], stroke_width=3), num_dashes=34))
        self.until(5.4)
        self.play(Create(rcl), run_time=0.8)
        kw = self.keywords([("Radiocapitellar line", YELLOW_C), ("→ capitellum ✓", GREEN_C)])
        self.play(Indicate(capitellum, color=YELLOW_C), FadeIn(kw[0], shift=UP * 0.2), run_time=0.7)
        badge_pos = pt(300, 150)

        def badge(mark, colour):
            return VGroup(Circle(radius=26 * S, color=colour, stroke_width=4), Text(mark, font=FONT, weight="BOLD", font_size=28, color=colour)).move_to(badge_pos)

        ok = badge("✓", GREEN_C)
        self.play(FadeIn(ok), FadeIn(kw[1], shift=UP * 0.2), FadeOut(labels), run_time=0.5)

        # ---- mechanism ----
        self.until(8.2)
        foosh = Arrow(pt(1040, 286), pt(968, 286), buff=0, color=WHITE, stroke_width=6)
        # rotation about the forearm's long axis: an open ellipse round the shaft
        pron = Arc(radius=1, start_angle=110 * DEGREES, angle=320 * DEGREES, color=WHITE, stroke_width=5)
        pron.stretch(30 * S, 0, about_point=ORIGIN).stretch(104 * S, 1, about_point=ORIGIN).shift(pt(760, 268))
        pron.add_tip(tip_length=0.18)
        kw2 = self.keywords([("FOOSH", WHITE), ("Hyperpronation", WHITE)])
        self.play(FadeOut(kw), FadeOut(ok), GrowArrow(foosh), FadeIn(kw2[0], shift=UP * 0.2), run_time=0.6)
        self.play(Create(pron), FadeIn(kw2[1], shift=UP * 0.2), run_time=0.8)

        # ---- fracture and dislocation ----
        self.until(10.6)
        prox = shape(ULNA_PROX, BLUE_C)
        dist = shape(ULNA_DIST, BLUE_C)
        unit_base = VGroup(dist, radius.copy())
        self.play(Flash(pt(542, 326), color=WHITE, line_length=0.5, flash_radius=0.35), FadeOut(foosh), FadeOut(pron), FadeOut(kw2), run_time=0.45)
        self.remove(ulna, radius)
        unit = always_redraw(lambda: unit_base.copy().apply_function(lambda p: dislocated([p], d.get_value())[0]))
        self.add(prox, unit)
        kw3 = self.keywords([("Proximal ⅓ ulna fracture", BLUE_C), ("Radial head → anterior", GREEN_C), ("Misses capitellum ✗", RED_C)])
        self.play(FadeIn(kw3[0], shift=UP * 0.2), run_time=0.4)
        self.play(d.animate.set_value(1), run_time=1.6, rate_func=smooth)            # 11.0 -> 12.6
        rcl_colour[0] = RED_C
        bad = badge("✗", RED_C)
        self.play(FadeIn(kw3[1], shift=UP * 0.2), FadeIn(bad), FadeIn(kw3[2], shift=UP * 0.2), run_time=0.5)

        # ---- Bado classification ----
        self.until(14.6)
        cards = VGroup()
        for n, direction, l1, l2, colour in [
            ("I", "Anterior", "ulnar shaft", "apex anterior · most common", YELLOW_C),
            ("II", "Posterior", "ulnar shaft", "apex posterior", BLUE_C),
            ("III", "Lateral", "ulnar metaphysis", "just below coronoid", GREEN_C),
            ("IV", "Anterior", "radius + ulna", "both proximal ⅓", RED_C),
        ]:
            box = RoundedRectangle(width=4.6, height=2.3, corner_radius=0.14, color=colour)
            body = VGroup(
                Text(direction, font=FONT, weight="BOLD", font_size=32),
                Text(l1, font=FONT, font_size=22, color=GREY_B),
                Text(l2, font=FONT, font_size=22, color=GREY_B),
            ).arrange(DOWN, aligned_edge=LEFT, buff=0.12)
            num = Text(n, font=FONT, weight="BOLD", font_size=60, color=colour)
            VGroup(num, body).arrange(RIGHT, buff=0.35, aligned_edge=UP).move_to(box)
            cards.add(VGroup(box, num, body))
        cards.arrange_in_grid(2, 2, buff=0.3).move_to(LEFT * 1.6 + DOWN * 0.2)
        bado_kw = self.keywords([("Bado I – IV", YELLOW_C)])
        # a black veil dims the diagram (live always_redraw parts would undo set_opacity)
        veil = Rectangle(width=config.frame_width, height=config.frame_height, stroke_width=0).set_fill(BLACK, 0.88)
        self.play(FadeIn(veil), FadeOut(kw3), FadeIn(bado_kw, shift=UP * 0.2), run_time=0.4)
        self.play(LaggedStart(*[FadeIn(c, shift=UP * 0.3) for c in cards], lag_ratio=0.6), run_time=2.6)
        self.until(18.0)
        self.play(Indicate(cards[0], color=YELLOW_C, scale_factor=1.06), run_time=0.9)
        self.until(19.6)
        self.play(FadeOut(cards), FadeOut(bado_kw), FadeOut(veil), run_time=0.5)

        # ---- posterior interosseous nerve ----
        self.until(20.2)
        nerve = always_redraw(lambda: VMobject(color=YELLOW_C, stroke_width=5).set_points_smoothly(
            [dislocated([pt(*q)], d.get_value())[0] if att else pt(*q) for q, att in NERVE]))
        pinch = always_redraw(lambda: Circle(radius=20 * S, color=RED_C, stroke_width=4).move_to(dislocated([pt(494, 222)], d.get_value())[0]))
        kw4 = self.keywords([("PIN palsy", YELLOW_C), ("Finger drop", WHITE), ("Wrist extension spared", MUTED)])
        self.play(Create(nerve), FadeIn(kw4[0], shift=UP * 0.2), run_time=1.0)
        self.add(pinch)
        self.play(Indicate(pinch, color=RED_C), FadeIn(kw4[1], shift=UP * 0.2), run_time=0.75)
        self.play(Indicate(pinch, color=RED_C), FadeIn(kw4[2], shift=UP * 0.2), run_time=0.75)
        self.play(Indicate(pinch, color=RED_C), run_time=0.75)
        self.until(24.2)

        # ---- treatment: restore ulnar length, the radial head follows ----
        kw5 = self.keywords([("Restore ulnar length", BLUE_C), ("→ radial head reduces", GREEN_C),
                             ("Child: closed reduction", WHITE), ("Adult: ORIF ulna", WHITE)])
        self.play(FadeOut(kw4), FadeOut(pinch), FadeOut(bad), FadeIn(kw5[0], shift=UP * 0.2), run_time=0.2)
        self.play(d.animate.set_value(0), run_time=1.4, rate_func=smooth)            # 24.4 -> 25.8
        rcl_colour[0] = GREEN_C
        self.play(Flash(pt(440, 226), color=WHITE, flash_radius=0.35), FadeIn(badge("✓", GREEN_C)), FadeIn(kw5[1], shift=UP * 0.2), run_time=0.45)
        self.until(26.4)
        plate = VGroup(
            RoundedRectangle(width=210 * S, height=14 * S, corner_radius=0.04, color="#dddddd").set_fill("#dddddd", 0.25).move_to(pt(545, 357)),
            *[Line(pt(x, 358), pt(x, 318), color="#dddddd", stroke_width=4) for x in (470, 510, 580, 620)],
        )
        self.play(FadeIn(kw5[2], shift=UP * 0.2), Create(plate), FadeIn(kw5[3], shift=UP * 0.2), run_time=0.9)

        # ---- mnemonic ----
        self.until(28.0)
        end_veil = Rectangle(width=config.frame_width, height=config.frame_height, stroke_width=0).set_fill(BLACK, 0.94)
        self.play(FadeIn(end_veil), FadeOut(kw5), run_time=0.3)
        m1 = Text("Monteggia  →  Ulna fracture", font=FONT, weight="BOLD", font_size=52, t2c={"U": BLUE_C, "→": MUTED})
        m2 = Text("Galeazzi  →  Radius fracture", font=FONT, weight="BOLD", font_size=52, t2c={"R": GREEN_C, "→": MUTED})
        m3 = Text("MUGR", font=FONT, slant="ITALIC", font_size=36, color=MUTED)
        VGroup(m1, m2, m3).arrange(DOWN, buff=0.35)
        self.play(Write(m1), run_time=0.5)
        self.play(Write(m2), run_time=0.5)
        self.play(FadeIn(m3), run_time=0.4)
        self.until(30.0)

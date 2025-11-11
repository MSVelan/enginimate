from manim import *


class DefaultTemplate(Scene):
    def construct(self):
        circle = Circle()  # create a circle
        circle.set_fill(PINK, opacity=0.5)  # set color and transparency

        square = Square()  # create a square
        square.flip(RIGHT)  # flip horizontally
        square.rotate(-3 * TAU / 8)  # rotate a certain amount

        self.play(Create(square))  # animate the creation of the square
        self.play(Transform(square, circle))  # interpolate the square into the circle
        self.play(FadeOut(square))  # fade out animation


# from manim import *
#
#
# class Enginimate(Scene):
#     def construct(self):
#         square = Square(side_length=2, color=WHITE)
#         circle = Circle(radius=1, color=YELLOW)
#         self.add(square, circle)

#
# from manim import *
# import numpy as np
#
#
# class Enginimate(Scene):
#     def construct(self):
#         # Start with a zoomed‑out view showing the whole square and circle
#         # self.camera.frame.set_width(14)  # zoomed‑out (default is ~14)
#
#         # Title
#         title = Tex(r"Approximating $\pi$ with Monte Carlo Method")
#         title.to_edge(UP)
#
#         # Introductory text
#         intro = Tex(
#             r"We will estimate the area of the unit circle by randomly sampling points."
#         )
#         intro.next_to(title, DOWN, buff=0.6)
#
#         # Show title and intro
#         self.play(Write(title, run_time=1.5), Write(intro, run_time=2))
#         self.wait(1)
#
#         # Unit circle (radius = 1) centered at origin
#         circle = Circle(radius=1, color=BLUE)
#         circle.set_fill(BLUE_E, opacity=0.3)
#
#         # Surrounding square (bounding box) with side length 2
#         square = Square(side_length=2, color=WHITE)
#         square.set_stroke(WHITE, width=2)
#         square.move_to(ORIGIN)
#
#         # Add circle and square to the scene
#         self.play(Create(square, run_time=2), Create(circle, run_time=2))
#         self.wait(1)
#
#         # Parameters
#         num_points = 200  # reduced for reasonable runtime
#         inside_color = GREEN
#         outside_color = RED
#
#         # Containers for points and counters
#         points = VGroup()
#         inside_count = ValueTracker(0)
#
#         # Generate random points (invisible initially)
#         for _ in range(num_points):
#             x, y = np.random.uniform(-1, 1, 2)
#             dot = Dot([x, y, 0], radius=0.03, fill_opacity=1)
#             dot.set_color(inside_color if np.hypot(x, y) <= 1 else outside_color)
#             dot.set_opacity(0)  # start invisible
#             points.add(dot)
#
#         # Updater to count visible inside points
#         def update_inside_count(_):
#             inside = sum(
#                 1 for d in points if d.color == inside_color and d.get_opacity() > 0
#             )
#             inside_count.set_value(inside)
#
#         points.add_updater(update_inside_count)
#
#         # Add points (still invisible)
#         self.add(points)
#
#         # MathTex object to display current π approximation, updating dynamically
#         pi_display = always_redraw(
#             lambda: MathTex(
#                 r"\pi \approx",
#                 f"{4 * (inside_count.get_value() / num_points):.5f}",
#                 font_size=36,
#             ).to_corner(DR)
#         )
#         self.add(pi_display)
#
#         # ---------- Progress bar and counter ----------
#         processed_tracker = ValueTracker(0)
#
#         # Background bar
#         bar_bg = Rectangle(width=4, height=0.3, stroke_color=WHITE, fill_opacity=0)
#         bar_bg.to_edge(DOWN, buff=0.5)
#
#         # Foreground (filled) bar
#         bar_fg = always_redraw(
#             lambda: Rectangle(
#                 width=4 * (processed_tracker.get_value() / num_points),
#                 height=0.3,
#                 fill_color=GREEN,
#                 fill_opacity=0.7,
#                 stroke_width=0,
#             ).align_to(bar_bg.get_left(), LEFT)
#         )
#
#         # Counter text
#         counter_text = always_redraw(
#             lambda: Tex(
#                 f"{int(processed_tracker.get_value())}/{num_points}",
#                 font_size=24,
#                 color=YELLOW,
#             ).next_to(bar_bg, UP, buff=0.2)
#         )
#
#         self.add(bar_bg, bar_fg, counter_text)
#
#         # Animate points appearing one by one with a short delay and update progress
#         for i, dot in enumerate(points):
#             self.play(
#                 dot.animate.set_opacity(1),
#                 processed_tracker.animate.set_value(i + 1),
#                 run_time=0.07,
#                 rate_func=linear,
#             )
#         self.wait(1)
#
#         # Show the formula used for the estimation
#         formula = Tex(
#             r"\pi \approx 4 \times \frac{\text{inside}}{\text{total}}",
#             font_size=36,
#         )
#         formula.next_to(pi_display, DOWN, buff=0.5)
#         self.play(Write(formula), run_time=2)
#         self.wait(1)
#
#         # Emphasize the final estimate by moving it to the top centre and scaling it
#         self.play(
#             pi_display.animate.scale(2).to_edge(UP),
#             run_time=2,
#         )
#         self.wait(1)
#
#         # Zoom in on the circle to highlight the final result
#         self.play(
#             self.camera.frame.animate.set_width(4).move_to(circle.get_center()),
#             run_time=2,
#         )
#         self.wait(2)
#
#         # Clean up: remove updaters
#         points.remove_updater(update_inside_count)
#
#         # Keep the final view for a moment
#         self.wait(3)

"""
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
"""

from manim import (
    Scene,
    Square,
    Text,
    VGroup,
    Arrow,
    LEFT,
    RIGHT,
    UP,
    DOWN,
    ORIGIN,
    BLUE,
    GREEN,
    RED,
    YELLOW,
    Write,
    Rectangle,
)


class Enginimate(Scene):
    def construct(self):
        # Stack boundary rectangle for visual reference
        stack_boundary = Rectangle(width=2, height=4, color="WHITE")
        stack_boundary.move_to(ORIGIN)

        # Define initial empty position for TOP arrow (points to top of stack_boundary)
        empty_top_start = stack_boundary.get_top() + DOWN * 0.5
        empty_top_end = stack_boundary.get_top()

        # Create first element 'A'
        element_a = Square(side_length=1, color="BLUE")
        label_a = Text("A", color="white", font_size=24)
        label_a.move_to(element_a.get_center())
        element_a_group = VGroup(element_a, label_a)
        element_a_group.next_to(stack_boundary, DOWN, buff=0.1)

        # Create TOP pointer initially pointing to empty position
        top_arrow = Arrow(start=empty_top_start, end=empty_top_end, color="RED")

        # Add stack boundary and initial elements
        self.add(stack_boundary, element_a_group, top_arrow)
        self.wait(2)  # Increased wait time

        # Animate pushing 'A' into stack (move TOP from empty to 'A')
        new_start = element_a_group.get_center() + UP * 0.5
        new_end = element_a_group.get_center() + UP * 1
        self.play(
            top_arrow.animate.put_start_and_end_on(new_start, new_end), run_time=1
        )
        self.wait(2)  # Increased wait time

        # Create second element 'B'
        element_b = Square(side_length=1, color="GREEN")
        label_b = Text("B", color="white", font_size=24)
        label_b.move_to(element_b.get_center())
        element_b_group = VGroup(element_b, label_b)
        element_b_group.shift(RIGHT * 4)  # Start further right for slide-in

        # Add element group to scene before animation
        self.add(element_b_group)

        # Animate pushing 'B' into stack
        self.play(
            element_b_group.animate.next_to(element_a_group, UP, aligned_edge=LEFT),
            run_time=2,  # Increased run_time
        )

        # Calculate new TOP arrow positions based on B's final position
        new_start = element_b_group.get_center() + UP * 0.5
        new_end = element_b_group.get_center() + UP * 1

        # Animate TOP pointer movement
        self.play(
            top_arrow.animate.put_start_and_end_on(start=new_start, end=new_end),
            run_time=1,
        )
        self.wait(2)  # Increased wait time

        # Pop element 'B'
        # Highlight 'B' briefly
        self.play(element_b_group.animate.scale(1.2).set_color("YELLOW"), run_time=0.5)

        # Slide out 'B' to the right and move TOP up
        self.play(
            element_b_group.animate.shift(RIGHT * 4),
            top_arrow.animate.put_start_and_end_on(
                start=element_a_group.get_center() + UP * 0.5,
                end=element_a_group.get_center() + UP * 1,
            ),
            run_time=2,  # Increased run_time
        )

        # Add wait after popping 'B'
        self.wait(1)

        # Pop element 'A'
        # Highlight 'A' briefly
        self.play(element_a_group.animate.scale(1.2).set_color("YELLOW"), run_time=0.5)

        # Slide out 'A' to the right and move TOP back to empty position
        self.play(
            element_a_group.animate.shift(RIGHT * 4),
            top_arrow.animate.put_start_and_end_on(
                start=empty_top_start, end=empty_top_end
            ),
            run_time=2,  # Increased run_time
        )

        # Add final text showing empty stack
        empty_text = Text("Empty Stack", font_size=28, color="RED")
        empty_text.next_to(stack_boundary, DOWN * 2)
        self.play(Write(empty_text), run_time=1.5)

        # Hold final frame for 2 seconds
        self.wait(2)


"""
import numpy as np
from manim import *


class Enginimate(ZoomedScene):
    def construct(self):
        number_plane = NumberPlane()
        dot = Dot(point=ORIGIN)
        original_text = Text("Point Coordinates: (0, 0)", font_size=24).to_corner(UL)
        self.add(self.camera.frame)
        self.add(number_plane, original_text)
        self.play(Create(dot), run_time=1)
        path = Line(ORIGIN, [3, 4, 0])
        self.play(MoveAlongPath(dot, path), run_time=2)

        # Apply linear transformation (scaling by 0.5 to stay within viewport)
        new_position = np.array([1.5, 2, 0])  # 0.5x scaling of [3, 4, 0]
        new_dot = Dot(point=new_position)
        self.play(Transform(dot, new_dot), run_time=1.5)

        # Update coordinates display
        new_text = Text("Point Coordinates: (1.5, 2)", font_size=24).to_corner(UL)
        self.play(FadeOut(original_text), run_time=0.5)
        self.play(Write(new_text), run_time=1)

        # Zoom out to show new location in context by scaling the zoomed camera frame
        self.activate_zooming()
        self.zoomed_camera.frame.scale(1.5)  # Adjust scale factor as needed
        self.play(self.zoomed_camera.frame.animate.scale(1.5), run_time=1.5)
"""

"""
from manim import *
import random
import numpy as np
import math


class Enginimate(Scene):
    def construct(self):
        # Dark background
        self.camera.background_color = "#0e0e0e"

        # Subtle grid lines to emphasize the unit square
        grid = NumberPlane(
            x_range=[-1.5, 1.5, 0.5],
            y_range=[-1.5, 1.5, 0.5],
            background_line_style={
                "stroke_color": GREY_D,
                "stroke_width": 1,
                "stroke_opacity": 0.4,
            },
            axis_config={"stroke_color": GREY_D, "stroke_width": 2},
        )
        self.add(grid)

        # Bounding square from (-1, -1) to (1, 1), slightly transparent
        bounding_square = Square(side_length=2, color=WHITE).move_to(ORIGIN)
        bounding_square.set_fill(opacity=0.1)
        self.play(Create(bounding_square), run_time=2)

        # Unit circle centered at the origin with radius 1
        unit_circle = Circle(radius=1, color=YELLOW).move_to(ORIGIN)
        self.play(Create(unit_circle), run_time=2)

        # Display the formula A = πr² with r = 1, simplifying to A = π
        formula = Text("A = πr²,  r = 1 → A = π", font_size=18, color=WHITE)
        formula.next_to(unit_circle, UP, buff=0.5)
        self.play(FadeIn(formula, shift=UP), run_time=1.5)

        # Counters for total points and points inside the circle
        total_text = Text("Total: 0", font_size=18, color=WHITE).next_to(
            formula, DOWN, buff=0.3
        )
        inside_text = Text("Inside: 0", font_size=18, color=WHITE).next_to(
            total_text, RIGHT, buff=0.6
        )
        self.play(FadeIn(VGroup(total_text, inside_text), shift=UP), run_time=1)

        # Monte Carlo point generation
        num_points = 200
        total = 0
        inside = 0

        for _ in range(num_points):
            # Random point inside the square [-1,1]×[-1,1]
            x = random.uniform(-1, 1)
            y = random.uniform(-1, 1)
            point = np.array([x, y, 0])

            # Check if inside the unit circle
            distance = np.linalg.norm(point[:2])
            point_color = BLUE if distance <= 1 else RED

            # Create dot and add instantly (no heavy animation)
            dot = Dot(point, radius=0.04, color=point_color)
            self.add(dot)

            # Update counters
            total += 1
            if distance <= 1:
                inside += 1

            # Refresh counter texts with a smooth replacement
            new_total = Text(f"Total: {total}", font_size=18, color=WHITE).move_to(
                total_text
            )
            new_inside = Text(f"Inside: {inside}", font_size=18, color=WHITE).move_to(
                inside_text
            )
            self.play(
                ReplacementTransform(total_text, new_total),
                ReplacementTransform(inside_text, new_inside),
                run_time=0.05,
                lag_ratio=0,
            )
            total_text, inside_text = new_total, new_inside

        # Compute π approximation
        pi_estimate = 4 * inside / total
        estimate_text = Text(f"π ≈ {pi_estimate:.5f}", font_size=18, color=GREEN)
        estimate_text.move_to(ORIGIN).shift(UP * 1.8)
        self.play(FadeIn(estimate_text), run_time=2)
        self.wait(1)

        # Show true value of π next to the approximation
        true_pi_text = Text(f"π = {math.pi:.5f}", font_size=18, color=YELLOW)
        true_pi_text.next_to(estimate_text, RIGHT, buff=0.8)
        self.play(FadeIn(true_pi_text), run_time=1.5)

        # Visualize error magnitude with a short horizontal bar
        error = abs(pi_estimate - math.pi)
        max_error_display = 0.5  # errors up to this will fill the bar
        target_length = min(error / max_error_display, 1) * 2  # up to 2 units total
        error_bar = Line(LEFT, RIGHT, color=RED, stroke_width=6)
        # Scale to the desired length (original length is 2)
        error_bar.scale(target_length / 2)
        error_bar.next_to(estimate_text, DOWN, buff=0.3)
        self.play(GrowFromCenter(error_bar), run_time=1.2)

        # Optional: show numeric error value
        error_text = Text(f"Error = {error:.5f}", font_size=18, color=RED)
        error_text.next_to(error_bar, DOWN, buff=0.2)
        self.play(FadeIn(error_text), run_time=1)

        self.wait(2)
"""

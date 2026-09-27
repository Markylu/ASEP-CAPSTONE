#!/usr/bin/env python3
"""Browse, replay and export recorded VLMnav runs.

    python3 eval/replay_tui.py

A front end over commands that already work — `godot --scripted-indices`,
`eval/replay.py`, and ffmpeg. Nothing here decides anything a run did; it makes
what a run recorded readable, and re-flies it on request.

The per-step reasons get the most space because they are the only part of a run
a rerun does not reproduce, which is why decisions.jsonl is the file that is
version-controlled.
"""
from __future__ import annotations

import asyncio
import sys
import tempfile
from pathlib import Path
from typing import List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))

from rich.text import Text
from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import (Button, DataTable, Footer, Header, Input, Label,
                             RichLog, Static, TabbedContent, TabPane)

from runlib import commands, procs, reel, render, stats
from runlib.model import Decision, Run, list_runs

SCRATCH = Path(tempfile.gettempdir())  # intermediate AVI only; finals go to eval/exports/


class ConfirmScreen(ModalScreen):
    """Used only where an action would destroy something on disk."""

    BINDINGS = [Binding("escape", "dismiss_false", "Cancel")]

    def __init__(self, title: str, detail: str, confirm_label: str = "Proceed") -> None:
        super().__init__()
        self._title = title
        self._detail = detail
        self._confirm_label = confirm_label

    def compose(self) -> ComposeResult:
        with Vertical(id="confirm-box"):
            yield Label(self._title, id="confirm-title")
            yield Static(self._detail, id="confirm-detail")
            with Horizontal(id="confirm-buttons"):
                yield Button(self._confirm_label, variant="warning", id="confirm-yes")
                yield Button("Cancel", variant="primary", id="confirm-no")

    @on(Button.Pressed, "#confirm-yes")
    def _yes(self) -> None:
        self.dismiss(True)

    @on(Button.Pressed, "#confirm-no")
    def _no(self) -> None:
        self.dismiss(False)

    def action_dismiss_false(self) -> None:
        self.dismiss(False)


class FramePane(Static):
    """Half-block preview; see runlib/render.py for why not a real image."""

    def show(self, path: Optional[Path], caption: str = "") -> None:
        if path is None:
            self.update(Text(caption or "no frame on disk for this step "
                                       "(frames/ is gitignored)", style="yellow"))
            return
        self.update(render.HalfBlockImage(path, max_height=40))


class ReplayTUI(App):
    CSS = """
    Screen { layout: vertical; }
    #body { height: 1fr; }
    #runs { width: 50; border-right: solid $panel; }
    #detail { width: 1fr; }
    #controls { height: auto; padding: 0 1; background: $panel; }
    #controls Label { padding: 1 1 0 0; }
    #speed { width: 10; }
    #log { height: 8; border-top: solid $panel; }
    /* The reason is the one thing a rerun does not reproduce, so it gets the
       slack: the step table shrinks to its rows and the prose takes the rest. */
    #steps { height: auto; max-height: 40%; }
    #reason-scroll { height: 1fr; }
    #reason { padding: 1 2; }
    #confirm-box {
        width: 80; height: auto; padding: 1 2;
        background: $surface; border: thick $warning;
    }
    #confirm-title { text-style: bold; color: $warning; }
    #confirm-detail { padding: 1 0; }
    #confirm-buttons { height: auto; align: right middle; }
    #confirm-buttons Button { margin-left: 1; }
    .warn { color: $warning; }
    """

    BINDINGS = [
        Binding("w", "watch", "Watch"),
        Binding("v", "verify", "Verify"),
        Binding("e", "export_flight", "Export video"),
        Binding("d", "export_reel", "Decision reel"),
        Binding("o", "open_frame", "Open frame"),
        Binding("c", "cancel", "Cancel job"),
        Binding("r", "reload", "Reload"),
        Binding("q", "quit", "Quit"),
    ]

    def __init__(self, runs_dir: Optional[Path] = None) -> None:
        super().__init__()
        self.runs_dir = runs_dir
        self.runs = []  # type: List[Run]
        self.runner = procs.Runner()

    # ---------------------------------------------------------------- layout

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="body"):
            yield DataTable(id="runs", cursor_type="row", zebra_stripes=True)
            with Vertical(id="detail"):
                with TabbedContent(id="tabs"):
                    with TabPane("Overview", id="tab-overview"):
                        yield VerticalScroll(Static(id="overview"))
                    with TabPane("Decisions", id="tab-decisions"):
                        yield DataTable(id="steps", cursor_type="row",
                                        zebra_stripes=True)
                        yield VerticalScroll(Static(id="reason"),
                                             id="reason-scroll")
                    with TabPane("Frame", id="tab-frame"):
                        yield VerticalScroll(FramePane(id="frame"))
        with Horizontal(id="controls"):
            yield Label("speed")
            yield Input(value="1.0", id="speed", type="number")
            yield Label("  [w]atch   [v]erify   [e]xport video   "
                        "[d]ecision reel   [o]pen frame   [c]ancel   [r]eload",
                        markup=False)
        yield RichLog(id="log", highlight=True, markup=False, wrap=True)
        yield Footer()

    def on_mount(self) -> None:
        self.title = "VLMnav replays"
        runs_table = self.query_one("#runs", DataTable)
        runs_table.add_columns("run", "steps", "col", "goal")
        steps_table = self.query_one("#steps", DataTable)
        steps_table.add_columns("step", "action", "rung", "latency", "tok", "!")
        self.action_reload()

    # ------------------------------------------------------------ run listing

    def action_reload(self) -> None:
        self.runs = list_runs(self.runs_dir)
        table = self.query_one("#runs", DataTable)
        table.clear()
        for run in self.runs:
            goal = "-" if run.goal_reached is None else ("yes" if run.goal_reached else "no")
            label = Text(run.run_id)
            if not run.replayable:
                label = Text(run.run_id, style="yellow")
            table.add_row(label, str(run.n_steps), str(run.collisions), goal,
                          key=str(run.path))
        self.log_line("{0} run(s) in {1}".format(
            len(self.runs), self.runs_dir or commands.REPO_ROOT / "eval" / "runs"))
        if self.runs:
            table.move_cursor(row=0)
            self.show_run(self.runs[0])

    @property
    def selected_run(self) -> Optional[Run]:
        table = self.query_one("#runs", DataTable)
        if table.cursor_row < 0 or table.cursor_row >= len(self.runs):
            return None
        return self.runs[table.cursor_row]

    @property
    def selected_decision(self) -> Optional[Decision]:
        run = self.selected_run
        if run is None or not run.decisions:
            return None
        table = self.query_one("#steps", DataTable)
        ordered = sorted(run.decisions, key=lambda d: d.step)
        if 0 <= table.cursor_row < len(ordered):
            return ordered[table.cursor_row]
        return None

    @on(DataTable.RowHighlighted, "#runs")
    def _run_highlighted(self, event: DataTable.RowHighlighted) -> None:
        if 0 <= event.cursor_row < len(self.runs):
            self.show_run(self.runs[event.cursor_row])

    @on(DataTable.RowHighlighted, "#steps")
    def _step_highlighted(self) -> None:
        self.show_decision()

    # ----------------------------------------------------------------- detail

    def show_run(self, run: Run) -> None:
        self.query_one("#overview", Static).update(self.overview_text(run))

        table = self.query_one("#steps", DataTable)
        table.clear()
        for decision in sorted(run.decisions, key=lambda d: d.step):
            action = "FAILED" if decision.failed else str(decision.index)
            flag = "{0} retries".format(len(decision.attempts)) if decision.attempts else ""
            style = "red" if decision.failed else ("yellow" if decision.attempts else "")
            table.add_row(
                Text(str(decision.step), style=style),
                Text(action, style=style),
                Text(decision.rung or "?", style=style),
                "{0:.1f}s".format(decision.latency_ms / 1000.0),
                str(decision.completion_tokens),
                Text(flag, style="yellow" if flag else ""))
        if run.decisions:
            table.move_cursor(row=0)
            self.show_decision()
        else:
            self.query_one("#reason", Static).update(
                Text(run.unreplayable_reason or "", style="yellow"))
            self.query_one("#frame", FramePane).show(None)

    def overview_text(self, run: Run) -> Text:
        text = Text()
        text.append(run.run_id + "\n", style="bold")
        if run.recorded_run_id:
            text.append("run.json says run_id={0} — this directory was copied "
                        "or renamed\n".format(run.recorded_run_id), style="yellow")
        if not run.replayable:
            text.append("UNREPLAYABLE: {0}\n".format(run.unreplayable_reason),
                        style="bold yellow")
        text.append("\n")

        def row(key: str, value) -> None:
            text.append("  {0:<22}".format(key), style="dim")
            text.append("{0}\n".format(value))

        row("started", run.started or "?")
        row("ended", run.meta.get("ended", "?"))
        row("model", run.model)
        row("prompt", "{0} ({1})".format(run.meta.get("prompt_version", "?"),
                                         run.meta.get("prompt_sha", "?")))
        row("git", "{0}{1}".format(run.meta.get("git_sha", "?"),
                                   " DIRTY" if run.meta.get("git_dirty") else ""))
        row("godot", run.meta.get("godot_version", "?"))
        row("scene", run.meta.get("scene", "?"))
        row("frame size", "{0}x{1}".format(*run.frame_size))
        row("temperature", run.meta.get("temperature", "?"))
        text.append("\n  results\n", style="bold")
        row("steps / max", "{0} / {1}".format(run.n_steps, run.meta.get("max_steps", "?")))
        row("collisions", run.collisions)
        row("goal reached", run.goal_reached)
        row("final distance", run.metrics.get("final_goal_distance_m", "?"))
        row("end reason", run.end_reason)

        latency = run.metrics.get("latency_ms") or {}
        if latency:
            text.append("\n  latency (ms)\n", style="bold")
            row("p50 / p95 / mean", "{0} / {1} / {2}".format(
                latency.get("p50"), latency.get("p95"), latency.get("mean")))
        tokens = run.metrics.get("tokens_total") or {}
        if tokens:
            row("tokens prompt/compl", "{0} / {1}".format(
                tokens.get("prompt"), tokens.get("completion")))
        counts = stats.rung_counts(run)
        if counts:
            text.append("\n  rungs used\n", style="bold")
            for name, count in sorted(counts.items()):
                row(name, count)

        text.append("\n  action space\n", style="bold")
        for key, value in sorted(run.config.items()):
            row(key, value)

        text.append("\n  on disk\n", style="bold")
        row("decisions.jsonl", len(run.decisions) or "absent")
        row("steps.jsonl", len(run.steps) or "absent")
        row("frames/", len(run.frames) or "absent")
        if run.replayable:
            row("indices", ",".join(str(i) for i in run.indices))
        return text

    def show_decision(self) -> None:
        run, decision = self.selected_run, self.selected_decision
        if run is None or decision is None:
            return
        text = Text()
        text.append("step {0}\n".format(decision.step), style="bold")
        if decision.failed:
            text.append("no index chosen — {0}\n".format(
                decision.error or "every rung failed"), style="bold red")
        if decision.attempts:
            text.append("\n{0} failed attempt(s) before this one:\n".format(
                len(decision.attempts)), style="yellow")
            for attempt in decision.attempts:
                text.append("  {0}: {1}\n".format(
                    attempt.get("rung", "?"), attempt.get("error", "")), style="yellow")
        goal = decision.goal
        if goal:
            result = run.result_step(decision)
            text.append("\nseen: goal {0:.2f} m at {1:+.1f}°{2}\n".format(
                float(goal.get("distance", 0.0)),
                float(goal.get("bearing_deg", 0.0)),
                "  COLLIDED" if (result and result.collided) else ""), style="cyan")
        text.append("\n")
        text.append(decision.reason or "(no reason recorded)")
        self.query_one("#reason", Static).update(text)
        self.query_one("#frame", FramePane).show(run.frame_for(decision))

    # ---------------------------------------------------------------- actions

    def log_line(self, line: str) -> None:
        self.query_one("#log", RichLog).write(line)

    @property
    def speed(self) -> float:
        try:
            return float(self.query_one("#speed", Input).value)
        except ValueError:
            return 1.0

    def require_replayable(self) -> Optional[Run]:
        run = self.selected_run
        if run is None:
            self.log_line("no run selected")
            return None
        if not run.replayable:
            self.log_line("cannot replay {0}: {1}".format(
                run.run_id, run.unreplayable_reason))
            self.notify(run.unreplayable_reason or "", severity="warning",
                        title="not replayable")
            return None
        return run

    def action_cancel(self) -> None:
        if self.runner.busy:
            self.runner.cancel()
            self.log_line("cancelled")
        else:
            self.log_line("nothing running")

    def action_open_frame(self) -> None:
        run, decision = self.selected_run, self.selected_decision
        path = run.frame_for(decision) if run and decision else None
        if path is None:
            self.log_line("no frame on disk to open")
            return
        problem = render.open_externally(path)
        self.log_line(problem or "opened {0}".format(path))

    def action_watch(self) -> None:
        run = self.require_replayable()
        if run is None:
            return
        try:
            command = commands.watch_command(run, speed=self.speed)
        except commands.ToolMissing as exc:
            self.log_line(str(exc))
            return
        self.log_line("Godot opens its own window; this pane shows its output.")
        self.run_job(command, "watch")

    def action_verify(self) -> None:
        run = self.require_replayable()
        if run is None:
            return
        problem = procs.decider_health()
        if problem:
            self.log_line(problem)
            self.notify(problem, severity="error", title="decider down")
            return
        if self.speed != 1.0:
            self.log_line("WARNING: verifying at {0}x. Drift is inside tolerance "
                          "but nonzero; cite runs flown at 1.0.".format(self.speed))

        replay_dir = commands.replay_dir_for(run)
        if replay_dir.exists():
            # The decider appends to steps.jsonl and /run/start does not clear
            # the directory, so a second verify would compare 9 steps against 18
            # and report a mismatch that is an artefact of the leftover file.
            self.push_screen(
                ConfirmScreen(
                    "Stale replay directory",
                    "{0}\nalready exists. The decider appends to steps.jsonl, so "
                    "verifying again without clearing it produces a spurious "
                    "STEP COUNT mismatch.\n\nDelete it and verify?".format(replay_dir),
                    confirm_label="Delete and verify"),
                lambda ok: self.start_verify(run, replay_dir) if ok
                else self.log_line("verify cancelled; {0} left alone".format(replay_dir)))
            return
        self.start_verify(run, None)

    def start_verify(self, run: Run, stale: Optional[Path]) -> None:
        if stale is not None:
            import shutil
            shutil.rmtree(stale, ignore_errors=True)
            self.log_line("removed {0}".format(stale))
        try:
            command = commands.verify_command(run, speed=self.speed)
        except commands.ToolMissing as exc:
            self.log_line(str(exc))
            return
        self.run_job(command, "verify")

    def action_export_flight(self) -> None:
        run = self.require_replayable()
        if run is None:
            return
        self.export_flight(run)

    def action_export_reel(self) -> None:
        run = self.selected_run
        if run is None:
            return
        self.export_reel(run)

    # ------------------------------------------------------------- background

    @work(exclusive=True)
    async def run_job(self, command: List[str], label: str) -> int:
        self.log_line("$ " + commands.shell_preview(command))
        try:
            code = await self.runner.run(command, self.log_line)
        except Exception as exc:  # noqa: BLE001 - surfaced, never swallowed
            self.log_line("{0} failed: {1}".format(label, exc))
            return 1
        self.log_line("{0} exited {1}".format(label, code))
        return code

    @work(exclusive=True)
    async def export_flight(self, run: Run) -> None:
        commands.EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
        avi = SCRATCH / "{0}_flight.avi".format(run.run_id)
        out = commands.EXPORTS_DIR / "{0}_flight.mp4".format(run.run_id)
        try:
            record = commands.record_command(run, avi, speed=self.speed)
            transcode = commands.transcode_command(avi, out)
        except commands.ToolMissing as exc:
            self.log_line(str(exc))
            return

        self.log_line("recording at {0}x{1} — Movie Maker ignores --frame-size, "
                      "and runs faster than wall clock".format(*commands.MOVIE_VIEWPORT))
        self.log_line("$ " + commands.shell_preview(record))
        code = await self.runner.run(record, self.log_line)
        if code != 0 or not avi.exists():
            self.log_line("recording failed (exit {0})".format(code))
            return
        self.log_line("$ " + commands.shell_preview(transcode))
        code = await self.runner.run(transcode, self.log_line)
        if code != 0:
            self.log_line("transcode failed (exit {0})".format(code))
            return
        avi.unlink(missing_ok=True)
        await self.report_video(out)

    @work(exclusive=True)
    async def export_reel(self, run: Run) -> None:
        commands.EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
        work_dir = SCRATCH / "{0}_reel".format(run.run_id)
        out = commands.EXPORTS_DIR / "{0}_reel.mp4".format(run.run_id)
        self.log_line("composing decision cards…")
        try:
            concat, count = await asyncio.get_event_loop().run_in_executor(
                None, reel.build_reel, run, work_dir)
        except ValueError as exc:
            self.log_line("cannot build reel: {0}".format(exc))
            self.notify(str(exc), severity="warning", title="no reel")
            return
        self.log_line("{0} card(s) in {1}".format(count, work_dir))
        try:
            command = commands.reel_command(concat, out)
        except commands.ToolMissing as exc:
            self.log_line(str(exc))
            return
        self.log_line("$ " + commands.shell_preview(command))
        code = await self.runner.run(command, self.log_line)
        if code != 0:
            self.log_line("reel encode failed (exit {0})".format(code))
            return
        await self.report_video(out)

    async def report_video(self, path: Path) -> None:
        try:
            probe = commands.ffprobe_command(path)
        except commands.ToolMissing as exc:
            self.log_line("wrote {0} ({1})".format(path, exc))
            return
        code, output = await procs.capture(probe)
        self.log_line("wrote {0}".format(path))
        for line in output.splitlines():
            self.log_line("  " + line)
        self.notify(str(path), title="export complete")


def main() -> int:
    runs_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    ReplayTUI(runs_dir).run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

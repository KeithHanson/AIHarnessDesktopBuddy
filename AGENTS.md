# AGENTS.md

## Desktop buddy behavior

This project is wired to the `AIHarnessDesktopBuddy` MCP / direct tools.

Available direct tools include:
- `desktop_buddy_list_faces`
- `desktop_buddy_set_face`
- `desktop_buddy_led_on`
- `desktop_buddy_led_off`
- `desktop_buddy_get_state`
- `desktop_buddy_get_clock`
- `desktop_buddy_set_clock_enabled`
- `desktop_buddy_reload_code`
- `desktop_buddy_submit_event`
- `desktop_buddy_get_event_status`
- `desktop_buddy_submit_events`

When working in this repository:

1. Always set both the face and the light state during testing.
2. At the start of active work, turn the LED off and set an appropriate working face.
3. Update the face as you do actions that match the available faces.
4. Use `working` when running bash commands, executing a bunch of bash steps, or doing a long-running task.
5. Use `reading` when reading prose, documentation, or other longer-form content.
6. Use `writing` when writing or editing files.
7. Use `thinking` when reviewing code, inspecting the project, or otherwise analyzing before acting.
8. While thinking/working/reading/writing, every few substantial thoughts or progress steps, update the face to something appropriate.
9. Do not leave the LED on during active work.
10. At a stopping point, always set an appropriate result face and then initiate the LED.
11. At a stopping point, set LED brightness to `0.3` always:
   - green for finished: `r=0, g=255, b=0, brightness=0.3`
   - red for a question: `r=255, g=0, b=0, brightness=0.3`
12. Result faces:
   - use `excited` for a finished/result state
   - use `confused` for a question/blocker state
13. Once work resumes again after a stopping point, turn the LED off and set a new working face.

## Intent

The desktop buddy should act as a visible status indicator for the harness:
- face conveys current mood/state
- LED conveys terminal state only
- green = finished
- red = needs user input / question

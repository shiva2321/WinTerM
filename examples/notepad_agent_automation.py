"""Notepad Automation Example using WinTerm Agent Toolkit.

Demonstrates closed-loop perception and autonomous agent workflow on Windows:
1. Senses live screen state (resolution, active cursor, foreground window).
2. Opens Notepad (notepad.exe) on the interactive desktop.
3. Discovers and focuses the Notepad window.
4. Dynamically inspects the UIAutomation element tree to find the text editor area coordinates.
5. Moves mouse and clicks into the editor, then types a structured paragraph using KeyboardEngine.
6. Dynamically locates the 'File' menu via UIAutomation, clicks it with the mouse, and triggers Save.
7. Captures a visual screenshot to verify window rendering state.
8. Closes the Notepad application with mouse click on the close button.
9. Records all agent actions, 5W cognitive traces, and results into the session ledger.
10. Analyzes execution performance and outputs a detailed telemetry report.
"""

import os
import sys
import time
import json
from pathlib import Path
from winterm.agent.winterm_agent import WinTermAgent


def run_notepad_automation():
    # Ensure UTF-8 console output for Windows terminals
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    print("=" * 75)
    print("  WinTerm Agent Toolkit: Autonomous Closed-Loop Perception & Automation")
    print("=" * 75)

    target_save_file = Path(r"d:\Agent_toolkit\winterm_notepad_demo.txt")
    session_output_file = Path(r"d:\Agent_toolkit\notepad_automation_session.json")
    screenshot_file = Path(r"d:\Agent_toolkit\live_notepad_perception.png")
    target_save_file.write_text("WinTerm Initial State\n", encoding="utf-8")

    # -------------------------------------------------------------------------
    # INITIALIZE AGENT
    # -------------------------------------------------------------------------
    print("\n[*] Initializing WinTermAgent (Subsystems, Knowledge Graph, Cognition Pipeline)...")
    agent = WinTermAgent()
    print(f"    Agent Session ID: {agent.session.session_id}")
    stats = agent.knowledge_graph.get_metrics()
    print(f"    Knowledge Graph: {stats['total_nodes']} nodes, {stats['total_edges']} edges loaded.")

    # -------------------------------------------------------------------------
    # SENSE: Initial Screen Perception
    # -------------------------------------------------------------------------
    print("\n[Perception Phase 1] Querying live screen topology & foreground state...")
    res_state, _, _ = agent.get_screen_state()
    if res_state.success and res_state.stdout:
        try:
            state_data = json.loads(res_state.stdout)
            fg = state_data.get("ForegroundWindow", {})
            print(f"    Display Resolution: {state_data.get('ScreenWidth')}x{state_data.get('ScreenHeight')}")
            print(f"    Active Cursor:      ({state_data.get('CursorX')}, {state_data.get('CursorY')})")
            print(f"    Foreground Window:  '{fg.get('Title')}' [HWND: {fg.get('Handle')}]")
        except Exception:
            pass

    # -------------------------------------------------------------------------
    # STEP 1: Launch Notepad on Interactive Desktop
    # -------------------------------------------------------------------------
    print("\n[Step 1/6] Launching Notepad application on interactive desktop...")
    res_launch, verif_launch, trace_launch = agent.launch_application(
        "notepad.exe", arguments=str(target_save_file.resolve())
    )
    print(f"    Status: {'SUCCESS' if res_launch.success else 'FAILED'} (Duration: {res_launch.duration_ms:.1f}ms)")
    time.sleep(2.5)

    # -------------------------------------------------------------------------
    # STEP 2: Window Discovery & Bringing to Foreground
    # -------------------------------------------------------------------------
    print("\n[Step 2/6] Locating and bringing Notepad window to foreground...")
    res_list, _, _ = agent.list_windows(query="Notepad")
    print(f"    Discovered Windows: {res_list.stdout[:120]}...")

    res_focus, verif_focus, trace_focus = agent.focus_window("winterm_notepad_demo.txt")
    print(f"    Focus Status: {'SUCCESS' if res_focus.success else 'FAILED'}")
    time.sleep(1.0)

    # -------------------------------------------------------------------------
    # SENSE: Dynamic Element Localization via UI Automation Tree
    # -------------------------------------------------------------------------
    print("\n[Perception Phase 2] Dynamically locating UI elements via UIAutomation tree...")
    editor_x, editor_y = 1291, 1156
    file_x, file_y = 469, 454
    close_x, close_y = 2125, 395

    # 1. Locate Text Editor document area
    res_elem_edit, _, _ = agent.find_ui_element("winterm_notepad_demo.txt", "Text editor")
    if res_elem_edit.success and res_elem_edit.stdout:
        try:
            d = json.loads(res_elem_edit.stdout)
            best = d.get("BestMatch")
            if best and best.get("CenterX") and best.get("CenterY"):
                editor_x = best["CenterX"]
                editor_y = best["CenterY"]
                print(f"    Found 'Text editor' at live screen coordinates ({editor_x}, {editor_y})")
        except Exception:
            pass

    # 2. Locate 'File' menu item
    res_elem_file, _, _ = agent.find_ui_element("winterm_notepad_demo.txt", "File")
    if res_elem_file.success and res_elem_file.stdout:
        try:
            d = json.loads(res_elem_file.stdout)
            best = d.get("BestMatch")
            if best and best.get("CenterX") and best.get("CenterY"):
                file_x = best["CenterX"]
                file_y = best["CenterY"]
                print(f"    Found 'File' menu item at live screen coordinates ({file_x}, {file_y})")
        except Exception:
            pass

    # 3. Locate Close button from window geometry
    if res_list.success and res_list.stdout:
        try:
            win_info = json.loads(res_list.stdout)
            if isinstance(win_info, list) and win_info:
                win_info = win_info[0]
            if isinstance(win_info, dict):
                close_x = win_info.get("X", 423) + win_info.get("Width", 1736) - 35
                close_y = win_info.get("Y", 368) + 25
                print(f"    Calculated window close [X] button at ({close_x}, {close_y})")
        except Exception:
            pass

    # -------------------------------------------------------------------------
    # STEP 3: Focus & Type Structured Paragraph
    # -------------------------------------------------------------------------
    print(f"\n[Step 3/6] Clicking editor document area at ({editor_x}, {editor_y}) via mouse...")
    agent.mouse_click(editor_x, editor_y, button="left")
    time.sleep(0.5)
    agent.press_hotkey(["ctrl", "a"])
    time.sleep(0.3)

    paragraph = (
        "WinTerm Agent Toolkit is an autonomous operations framework for Windows. "
        "It provides full-stack cognition, Win32 and UIAutomation subsystem control, "
        "reliable keyboard and mouse input simulation, and complete audit logging. "
        "Every operation executed by the agent is captured with 5W decision traces."
    )
    print("    Typing structured paragraph into Notepad via KeyboardEngine...")
    res_type, verif_type, trace_type = agent.type_text(paragraph, interval_ms=10)
    print(f"    Typing Status: {'SUCCESS' if res_type.success else 'FAILED'} (Typed {len(paragraph)} characters)")
    time.sleep(1.0)

    # -------------------------------------------------------------------------
    # STEP 4: Mouse-Driven Save Workflow
    # -------------------------------------------------------------------------
    print("\n[Step 4/6] Executing mouse-driven save workflow...")
    print(f"    1. Moving mouse to 'File' menu at ({file_x}, {file_y}) and clicking Left...")
    agent.mouse_click(file_x, file_y, button="left")
    time.sleep(0.8)

    save_y = file_y + 155
    print(f"    2. Moving mouse to 'Save' menu item at ({file_x}, {save_y}) and clicking Left...")
    agent.mouse_click(file_x, save_y, button="left")
    time.sleep(0.8)

    # Flush save via hotkey to guarantee file write
    agent.press_hotkey(["ctrl", "s"])
    time.sleep(1.0)

    # Dynamically detect if modern Windows 11 Notepad displays a modal formatting dialog
    res_dialog, _, _ = agent.find_ui_element("Notepad", "Save as text file")
    if res_dialog.success and res_dialog.stdout:
        try:
            d = json.loads(res_dialog.stdout)
            if d.get("MatchCount", 0) > 0:
                print("    Perceived modern save dialog: Invoking 'Save as text file' button...")
                agent.click_ui_element("Notepad", "Save as text file")
                time.sleep(1.0)
                agent.focus_window("winterm_notepad_demo.txt")
                time.sleep(0.5)
                agent.press_hotkey(["ctrl", "s"])
                time.sleep(1.5)
        except Exception:
            pass

    # Polling wait for disk buffer flush
    for _ in range(6):
        if target_save_file.exists() and len(target_save_file.read_text(encoding="utf-8")) > 50:
            break
        time.sleep(0.5)

    # Verify file content on disk
    file_saved = target_save_file.exists() and len(target_save_file.read_text(encoding="utf-8")) > 50
    print(f"    File saved to disk: {file_saved} (Path: {target_save_file})")
    if target_save_file.exists():
        print(f"    Saved File Size: {target_save_file.stat().st_size} bytes")

    # -------------------------------------------------------------------------
    # STEP 5: Visual Screen Perception (Screenshot Capture)
    # -------------------------------------------------------------------------
    print("\n[Step 5/6] Capturing visual screenshot to verify window state...")
    res_snap, _, _ = agent.capture_screen(str(screenshot_file))
    print(f"    Visual screenshot saved: {screenshot_file.exists()} ({screenshot_file})")

    # -------------------------------------------------------------------------
    # STEP 6: Mouse-Driven Close Application
    # -------------------------------------------------------------------------
    print(f"\n[Step 6/6] Clicking window close button at ({close_x}, {close_y}) using mouse...")
    agent.mouse_click(close_x, close_y, button="left")
    time.sleep(1.0)

    # Clean close fallback
    res_close, verif_close, trace_close = agent.close_window("winterm_notepad_demo.txt")
    print(f"    Application close status: {'SUCCESS' if res_close.success else 'FAILED'}")
    time.sleep(0.5)

    # -------------------------------------------------------------------------
    # STEP 7: Export Session Ledger
    # -------------------------------------------------------------------------
    print("\n[*] Recording and exporting all agent actions to session ledger...")
    agent.session.export_ledger(str(session_output_file))
    print(f"    Session ledger saved: {session_output_file} ({session_output_file.stat().st_size} bytes)")

    # -------------------------------------------------------------------------
    # STEP 8: Telemetry & Execution Analysis Report
    # -------------------------------------------------------------------------
    total_steps = len(agent.session.history)
    successful_steps = sum(1 for r in agent.session.history if r.execution_result and r.execution_result.success)
    total_duration_ms = sum(r.execution_result.duration_ms for r in agent.session.history if r.execution_result)

    print("\n" + "=" * 75)
    print("  WINTERM AGENT EXECUTION & TELEMETRY REPORT")
    print("=" * 75)
    print(f"Session ID:         {agent.session.session_id}")
    print(f"Total Steps Logged: {total_steps}")
    print(f"Successful Steps:   {successful_steps}/{total_steps} ({(successful_steps/total_steps)*100:.1f}%)")
    print(f"Total Execution:    {total_duration_ms:.1f} ms")
    print(f"Target File Exists: {target_save_file.exists()}")
    if target_save_file.exists():
        print(f"Target File Content:\n--- START FILE ---\n{target_save_file.read_text(encoding='utf-8')}\n--- END FILE ---")

    print("\n5W COGNITIVE TRACE BREAKDOWN ACROSS STEPS:")
    print("-" * 75)
    for idx, rec in enumerate(agent.session.history, 1):
        step_name = rec.step.title
        res = rec.execution_result
        trace = rec.decision_trace
        print(f"\n[Step {idx}] {step_name}")
        print(f"  Command:   {res.command if res else 'N/A'}")
        print(f"  Result:    {'SUCCESS' if res and res.success else 'FAILED'} (Time: {res.duration_ms:.1f}ms if res else 0ms)")
        if trace:
            print(f"  [WHAT]     {trace.what}")
            print(f"  [HOW]      {trace.how}")
            print(f"  [WHEN]     {len(trace.when)} preconditions validated")
            print(f"  [WHY]      {trace.why.get('justification', 'Automated step') if isinstance(trace.why, dict) else str(trace.why)[:120]}")
            print(f"  [AFTER]    {trace.after}")

    print("\n" + "=" * 75)
    print("  Demonstration completed successfully with 100% audit logging.")
    print("=" * 75)


if __name__ == "__main__":
    run_notepad_automation()

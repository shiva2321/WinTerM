"""Basic usage example of WinTermAgent: The 5W AI Agent Toolkit for Windows Terminal."""

from winterm.agent.winterm_agent import WinTermAgent
from winterm.tools.tool_definitions import (
    plan_terminal_task,
    explain_terminal_command,
    predict_command_impact,
    execute_terminal_command,
)


def main():
    print("=== WinTermAgent 5W Terminal Automation Quickstart ===\n")

    agent = WinTermAgent()

    # 1. WHAT TO DO (Planning)
    goal = "Query top 5 memory processes and list hardware specs"
    print(f"Goal: {goal}")
    plan = agent.plan(goal)
    print(f"Plan created with {len(plan.steps)} steps:\n")
    for s in plan.steps:
        print(f"  - [{s.step_id}] {s.title} ({s.category.value})")

    # 2. 5W EXPLANATION (What, How, When, Why, After)
    print("\n--- Deep 5W Explanation for Step 1 ---")
    step = plan.steps[0]
    trace = agent.explain(step)
    print(f"1. WHAT: {trace.what}")
    print(f"2. HOW:  {trace.how}")
    print(f"3. WHEN: {len(trace.when)} precondition guards attached")
    print(f"4. WHY:  {trace.why.command_justification}")
    print(f"5. AFTER: {trace.after}")

    # 3. DRY-RUN SIMULATION
    print("\n--- Dry Run Simulation ---")
    res, verif, trace = agent.execute_step(step, dry_run=True)
    print(f"Dry Run Result: {res.stdout}")

    # 4. LIVE EXECUTION
    print("\n--- Live Execution & Verification ---")
    res, verif, trace = agent.execute_step(step, dry_run=False)
    print(f"Success: {res.success} (Exit code: {res.exit_code}, Duration: {res.duration_ms}ms)")
    if res.stdout:
        print(f"Output snippet:\n{res.stdout[:250]}...")
    if verif:
        print(f"Post-Condition Verification: {verif.details}")


if __name__ == "__main__":
    main()

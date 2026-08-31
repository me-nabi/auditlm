# cli.py
# Three commands: init, dashboard, compare
# Uses Python's built-in argparse — no extra dependencies needed

import argparse
import subprocess
import sys
import os

from agentaudit.core.storage import init_db, DEFAULT_DB_PATH
from agentaudit.core.regression import compare_runs, get_latest_runs

# --------------------------------------------------------------------------- #
# Commands
# --------------------------------------------------------------------------- #

def cmd_init(args) -> None:
    """Create the SQLite database and run first-time setup wizard."""
    db_path = args.db or DEFAULT_DB_PATH

    print("🔍 AgentAudit Setup\n")

    # Check if .env already exists
    config_dir = os.path.expanduser("~/.agentaudit")
    os.makedirs(config_dir, exist_ok=True)
    env_path = os.path.join(config_dir, ".env")
    if os.path.exists(env_path):
        overwrite = input(".env already exists. Overwrite? (y/n): ").strip().lower()
        if overwrite != "y":
            print("Skipping API key setup.")
            init_db(db_path=db_path)
            print(f"✅ Database initialized at: {db_path}")
            return

    # Step 1 — provider
    print("Step 1: Which provider do you want to use for evaluation?")
    print("  1. gemini  (free tier available — recommended)")
    print("  2. openai  (GPT-4o-mini)")
    choice = input("\nEnter 1 or 2: ").strip()

    if choice == "1":
        provider = "gemini"
        models = [
            "gemini-flash-latest",
            "gemini-3.5-flash",
            "gemini-3-flash",
            "gemini-3.1-pro",
        ]
        env_key = "GEMINI_API_KEY"
        key_url = "https://aistudio.google.com/app/apikey"
    elif choice == "2":
        provider = "openai"
        models = [
            "gpt-4o-mini",
            "gpt-4o",
        ]
        env_key = "OPENAI_API_KEY"
        key_url = "https://platform.openai.com/api-keys"
    else:
        print("❌ Invalid choice. Run agentaudit init again.")
        sys.exit(1)

    # Step 2 — API key
    print(f"\nStep 2: Paste your {provider.upper()} API key.")
    print(f"  Get one free at: {key_url}")
    api_key = input("\nAPI key: ").strip()
    if not api_key:
        print("❌ API key cannot be empty.")
        sys.exit(1)

    # Validate the API key before saving
    print("\nValidating API key...")
    try:
        if provider == "gemini":
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            test_model = genai.GenerativeModel("gemini-flash-latest")
            test_model.generate_content("Say hello in one word.")
            print("✅ API key is valid.\n")
        elif provider == "openai":
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": "Say hello in one word."}],
                max_tokens=5,
            )
            print("✅ API key is valid.\n")
    except Exception as e:
        error_msg = str(e)
        if "401" in error_msg or "API_KEY_INVALID" in error_msg or "Incorrect API key" in error_msg:
            print(f"\n❌ Invalid API key. Please check and try again.")
            print(f"   Get a key at: {key_url}")
        elif "404" in error_msg:
            print(f"\n❌ Model not available. The test model may have been retired.")
            print(f"   Your key may still be valid — saving anyway.\n")
        elif "429" in error_msg or "quota" in error_msg.lower():
            print(f"\n⚠️  API key works but you've hit a rate limit.")
            print(f"   This is normal — saving the key.\n")
        else:
            print(f"\n❌ Could not validate API key: {error_msg}")
            print(f"   Check your key at: {key_url}")

        if "401" in error_msg or "API_KEY_INVALID" in error_msg or "Incorrect API key" in error_msg:
            sys.exit(1)

    # Step 3 — model
    print("\nStep 3: Which model should AgentAudit use as judge?")
    for i, m in enumerate(models, 1):
        tag = " (recommended)" if i == 1 else ""
        print(f"  {i}. {m}{tag}")
    model_choice = input("\nEnter number: ").strip()

    try:
        model = models[int(model_choice) - 1]
    except (ValueError, IndexError):
        model = models[0]
        print(f"Invalid choice — defaulting to {model}")

    # Write .env
    with open(env_path, "w") as f:
        f.write(f"{env_key}={api_key}\n")
        f.write(f"AGENTAUDIT_PROVIDER={provider}\n")
        f.write(f"AGENTAUDIT_MODEL={model}\n")

    # Initialize database
    init_db(db_path=db_path)

    print(f"""
✅ AgentAudit is ready.

   Provider : {provider}
   Model    : {model}
   Database : {db_path}
   Config   : {env_path}

Next steps:
   1. Create a starter file:   agentaudit example
   2. Edit the two TODO lines with your pipeline code
   3. Run it:                  python my_pipeline.py
   4. See your results:        agentaudit dashboard
""")


def cmd_dashboard(args) -> None:
    """Launch the Streamlit dashboard."""
    dashboard_path = os.path.join(
        os.path.dirname(__file__),
        "dashboard",
        "app.py",
    )

    if not os.path.exists(dashboard_path):
        print(f"❌ Dashboard not found at: {dashboard_path}")
        sys.exit(1)

    print("🚀 Launching AgentAudit dashboard at http://localhost:8501")
    subprocess.run([
        sys.executable, "-m", "streamlit", "run", dashboard_path
    ])


def cmd_compare(args) -> None:
    """Compare last two runs of a pipeline."""
    pipeline = args.pipeline
    db_path = args.db or DEFAULT_DB_PATH

    try:
        baseline_id, current_id = get_latest_runs(
            pipeline_name=pipeline,
            db_path=db_path,
        )
    except ValueError as e:
        print(f"❌ {e}")
        sys.exit(1)

    report = compare_runs(
        pipeline_name=pipeline,
        baseline_run_id=baseline_id,
        current_run_id=current_id,
        db_path=db_path,
    )

    print(f"\n📊 Regression Report — {pipeline}")
    print(f"Baseline Run: #{baseline_id}  |  Current Run: #{current_id}")
    print("-" * 60)

    for diff in report.diffs:
        status_icon = {
            "IMPROVED":  "✅",
            "REGRESSED": "❌",
            "STABLE":    "➡️",
            "NO_DATA":   "❓",
        }.get(diff.status, "❓")

        print(
            f"{status_icon} {diff.metric:<25}"
            f"baseline: {str(diff.baseline):<10}"
            f"current: {str(diff.current):<10}"
            f"{diff.status}"
        )

    print("-" * 60)
    print(report.summary)
    print()

    # Exit with error code if regression detected — useful for CI/CD
    if not report.passed:
        sys.exit(1)


def cmd_config(args) -> None:
    """Show or reset AgentAudit configuration."""
    config_dir = os.path.expanduser("~/.agentaudit")
    env_path = os.path.join(config_dir, ".env")

    if args.show:
        if not os.path.exists(env_path):
            print("❌ No config found. Run: agentaudit init")
            sys.exit(1)

        print("\n📋 Current AgentAudit config:\n")
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                # Mask the API key — show first 8 chars only
                if "API_KEY" in line:
                    key, value = line.split("=", 1)
                    masked = value[:8] + "..." if len(value) > 8 else "***"
                    print(f"   {key} = {masked}")
                else:
                    print(f"   {line}")
        print(f"\n   Config file: {env_path}\n")

    elif args.reset:
        print("Re-running setup wizard...\n")
        # Reuse init wizard by calling cmd_init with default args
        class _Args:
            db = None
        cmd_init(_Args())

    else:
        print("Usage:")
        print("  agentaudit config --show    show current config")
        print("  agentaudit config --reset   update API key or model")


def cmd_example(args) -> None:
    """Create a ready-to-edit starter pipeline file."""
    filename = "my_pipeline.py"
    filepath = os.path.join(os.getcwd(), filename)

    if os.path.exists(filepath):
        overwrite = input(f"{filename} already exists. Overwrite? (y/n): ").strip().lower()
        if overwrite != "y":
            print("Cancelled.")
            return

    starter_code = '''"""
my_pipeline.py — your AgentAudit starter file.

HOW TO USE THIS FILE:
---------------------
This file has ONE function that AgentAudit will watch.
You only need to change TWO things — they are marked TODO 1 and TODO 2 below.
Everything else should stay exactly as it is.

After editing, run this file:   python my_pipeline.py
Then see your results:          agentaudit dashboard
"""

# ---------------------------------------------------------------------------
# This line brings in AgentAudit. Do NOT change it.
# ---------------------------------------------------------------------------
from agentaudit import audit, set_context


# ---------------------------------------------------------------------------
# The @audit line below is what turns ON the auditing.
# "name" is just a label for this pipeline — you can rename it to anything,
# for example "insurance_bot" or "support_agent".
# ---------------------------------------------------------------------------
@audit(name="my_pipeline")
def my_pipeline(question: str) -> str:

    # =======================================================================
    # TODO 1 — YOUR RETRIEVAL STEP
    # -----------------------------------------------------------------------
    # This is where your code fetches the documents / data that your AI
    # uses to answer. It might be a database search, a PDF, a vector store,
    # or an API call.
    #
    # Replace the line below with YOUR real retrieval code.
    # Whatever documents you get, store them in the "context" variable.
    # =======================================================================
    context = "Replace this text with your retrieved documents."

    # -----------------------------------------------------------------------
    # This line hands your documents to AgentAudit so it can check whether
    # the AI stayed faithful to them. Do NOT change or remove this line.
    # -----------------------------------------------------------------------
    set_context(context)

    # =======================================================================
    # TODO 2 — YOUR AI CALL
    # -----------------------------------------------------------------------
    # This is where you call your AI model (OpenAI, Gemini, Claude, a local
    # model — anything). Pass it the question and the context above.
    #
    # Replace the line below with YOUR real AI call.
    # Store whatever the AI replies in the "answer" variable.
    # =======================================================================
    answer = "Replace this text with your AI model's answer."

    # -----------------------------------------------------------------------
    # This sends the AI's answer back. Do NOT change this line.
    # -----------------------------------------------------------------------
    return answer


# ---------------------------------------------------------------------------
# This part runs your pipeline once so you can test it.
# You can change the test question inside the quotes.
# Do NOT change anything else here.
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("Running your pipeline through AgentAudit...\\n")

    result = my_pipeline("Type a test question here")

    print("AI answer was:")
    print(result)
    print("\\n✅ Done! Now run this to see your scores:")
    print("   agentaudit dashboard")
'''

    with open(filepath, "w") as f:
        f.write(starter_code)

    print(f"""
✅ Created {filename} in this folder.

What to do now:
   1. Open {filename} in your editor
   2. Change the two lines marked TODO 1 and TODO 2
   3. Run it:            python {filename}
   4. See your scores:   agentaudit dashboard
""")


# --------------------------------------------------------------------------- #
# Main — wire commands to argparse
# --------------------------------------------------------------------------- #

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="auditlm",
        description="Open source evaluation toolkit for LLM pipelines and agents.",
    )

    subparsers = parser.add_subparsers(dest="command")

    # init
    init_parser = subparsers.add_parser("init", help="Initialize AgentAudit database")
    init_parser.add_argument("--db", help="Custom database path", default=None)

    # dashboard
    subparsers.add_parser("dashboard", help="Launch Streamlit dashboard")

    # compare
    compare_parser = subparsers.add_parser("compare", help="Compare last two pipeline runs")
    compare_parser.add_argument("--pipeline", required=True, help="Pipeline name to compare")
    compare_parser.add_argument("--db", help="Custom database path", default=None)

    # config
    config_parser = subparsers.add_parser(
        "config", help="Show or update AgentAudit configuration"
    )
    config_parser.add_argument(
        "--show", action="store_true", help="Show current config"
    )
    config_parser.add_argument(
        "--reset", action="store_true", help="Re-run setup wizard"
    )

    # example
    subparsers.add_parser(
        "example", help="Create a ready-to-edit starter pipeline file"
    )

    args = parser.parse_args()

    if args.command == "init":
        cmd_init(args)
    elif args.command == "dashboard":
        cmd_dashboard(args)
    elif args.command == "compare":
        cmd_compare(args)
    elif args.command == "config":
        cmd_config(args)
    elif args.command == "example":
        cmd_example(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
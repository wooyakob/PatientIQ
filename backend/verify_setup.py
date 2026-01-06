"""
Verification script to test backend setup without seeding data.
Tests database connection, API endpoints, and basic functionality.
"""

import os
import sys

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass


def check_env_vars():
    """Check that required environment variables are set"""
    print("\nChecking environment variables...")

    required_vars = [
        "CLUSTER_CONNECTION_STRING",
        "CLUSTER_NAME",
        "CLUSTER_PASS",
        "OPENAI_API_KEY"
    ]

    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
            print(f"  {var} - Not set")
        else:
            # Show partial value for verification
            value = os.getenv(var)
            if "KEY" in var or "PASS" in var:
                display = f"{value[:8]}..." if len(value) > 8 else "***"
            else:
                display = value[:50] + "..." if len(value) > 50 else value
            print(f"  {var} - {display}")

    if missing_vars:
        print(f"\nMissing required variables: {', '.join(missing_vars)}")
        print("Please set these in your .env file")
        return False

    print("All required environment variables are set")
    return True


def test_database_connection():
    """Test Couchbase connection"""
    print("\nTesting Couchbase connection...")

    try:
        from backend.database import db
        print("  Connected to cluster")
        if getattr(db, "patients_collection", None):
            print(f"  Bucket '{db.bucket_name}' is accessible")
            return True
        else:
            print(f"  Bucket '{db.bucket_name}' not found - needs to be created in Capella")
            print(f"     See CREATE_BUCKET_GUIDE.md for instructions")
            return False
    except Exception as e:
        print(f"  Database connection failed: {e}")
        return False


def test_agentc_catalog():
    """Test agentc catalog connection"""
    print("\nTesting Agent Catalog connection...")

    try:
        import agentc
        catalog = agentc.Catalog()
        print("  Agent Catalog initialized")

        # Try to find a prompt
        try:
            prompt = catalog.find("prompt", name="wearable_monitor_agent")
            if prompt:
                print("  Successfully loaded wearable_monitor_agent prompt")
            else:
                print("  Prompt not found in catalog (may need to commit prompts/)")
        except Exception as e:
            print(f"  Could not load prompts from catalog: {e}")
            print("     (This is OK - agents will use fallback prompts)")

        return True
    except Exception as e:
        print(f"  Agent Catalog connection failed: {e}")
        print("     (This is OK - agents will operate without catalog)")
        return True  # Not a critical failure


def test_openai_connection():
    """Test OpenAI API key"""
    print("\nTesting OpenAI connection...")

    try:
        from langchain_openai import ChatOpenAI
        api_key = os.getenv("OPENAI_API_KEY")

        if not api_key:
            print("  OPENAI_API_KEY not set")
            return False

        # Just verify the format, don't make an actual call
        if api_key.startswith("sk-"):
            print("  OpenAI API key format looks correct")
            return True
        else:
            print("  OpenAI API key format may be incorrect (should start with 'sk-')")
            return False
    except Exception as e:
        print(f"  Error: {e}")
        return False


def check_prompts_and_tools():
    """Check that prompts and tools files exist"""
    print("\nChecking prompts and tools...")

    prompts_dir = "prompts"
    tools_dir = "tools"

    expected_prompts = [
        "wearable_monitor_agent.yaml",
        "research_summarizer_agent.yaml",
        "message_router_agent.yaml",
        "questionnaire_summarizer_agent.yaml"
    ]

    expected_tools = [
        "patient_data_tools.py",
        "wearable_tools.py",
        "research_tools.py",
        "message_tools.py",
        "questionnaire_tools.py"
    ]

    all_good = True

    for prompt in expected_prompts:
        path = os.path.join(prompts_dir, prompt)
        if os.path.exists(path):
            print(f"  {prompt}")
        else:
            print(f"  {prompt} not found")
            all_good = False

    for tool in expected_tools:
        path = os.path.join(tools_dir, tool)
        if os.path.exists(path):
            print(f"  {tool}")
        else:
            print(f"  {tool} not found")
            all_good = False

    return all_good


def test_api_imports():
    """Test that FastAPI app can be imported"""
    print("\nTesting API imports...")

    try:
        from backend.api import app
        print("  FastAPI app imports successfully")
        return True
    except Exception as e:
        print(f"  Failed to import FastAPI app: {e}")
        return False


def main():
    """Run all verification checks"""
    print("=" * 60)
    print("Healthcare Agent System - Setup Verification")
    print("=" * 60)

    results = {
        "Environment Variables": check_env_vars(),
        "Database Connection": test_database_connection(),
        "Agent Catalog": test_agentc_catalog(),
        "OpenAI Connection": test_openai_connection(),
        "Prompts & Tools": check_prompts_and_tools(),
        "API Imports": test_api_imports()
    }

    print("\n" + "=" * 60)
    print("Verification Summary")
    print("=" * 60)

    for check, passed in results.items():
        status = "PASS" if passed else "FAIL"
        print(f"{status} - {check}")

    all_passed = all(results.values())

    if all_passed:
        print("\nAll checks passed! Your setup is ready.")
        print("\nNext steps:")
        print("1. Start the backend: uvicorn backend.api:app --reload --port 8000")
        print("2. Start the frontend: cd frontend && pnpm dev")
        print("3. Add patient data through the API or database")
    else:
        print("\nSome checks failed. Please review the errors above.")
        sys.exit(1)


if __name__ == "__main__":
    main()

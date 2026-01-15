#!/usr/bin/env python3
"""
Verification script for pulmonary research agent setup.

Checks that:
1. Catalog is indexed
2. All required tools are available
3. Prompt is available
4. Agent can be initialized
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import agentc


def check_catalog():
    """Check if catalog can be initialized"""
    print("1. Checking catalog initialization...")
    try:
        catalog = agentc.Catalog()
        print("   ✓ Catalog initialized successfully")
        return catalog
    except Exception as e:
        print(f"   ✗ Failed to initialize catalog: {e}")
        return None


def check_tools(catalog):
    """Check if required tools are available"""
    print("\n2. Checking required tools...")
    required_tools = [
        "find_patient_by_id",
        "find_conditions_by_patient_id",
        "paper_search",
    ]

    all_found = True
    for tool_name in required_tools:
        try:
            tool = catalog.find("tool", name=tool_name)
            if tool:
                print(f"   ✓ Found tool: {tool_name}")
            else:
                print(f"   ✗ Tool not found: {tool_name}")
                all_found = False
        except Exception as e:
            print(f"   ✗ Error finding tool {tool_name}: {e}")
            all_found = False

    return all_found


def check_prompt(catalog):
    """Check if pulmonary research agent prompt is available"""
    print("\n3. Checking prompt...")
    try:
        prompt = catalog.find("prompt", name="pulmonary_research_agent")
        if prompt:
            print(f"   ✓ Found prompt: pulmonary_research_agent")
            try:
                # Try to access tools list if available
                if hasattr(prompt, 'tools'):
                    print(f"   ✓ Prompt has {len(prompt.tools)} tools configured")
            except:
                pass
            return True
        else:
            print("   ✗ Prompt not found: pulmonary_research_agent")
            return False
    except Exception as e:
        print(f"   ✗ Error finding prompt: {e}")
        return False


def check_agent_init():
    """Check if agent can be initialized"""
    print("\n4. Checking agent initialization...")
    try:
        # Import here to avoid errors if catalog not set up
        sys.path.insert(0, str(Path(__file__).parent))
        from compat import run_pulmonary_research

        # Try running a quick test
        result = run_pulmonary_research("1", "What are treatment options?")
        if "error" in result:
            print(f"   ✗ Agent returned error: {result['error']}")
            return False
        else:
            print("   ✓ Agent initialized successfully")
            print(f"   ✓ Agent test run successful ({len(result.get('papers', []))} papers found)")
            return True
    except Exception as e:
        print(f"   ✗ Failed to run agent: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print("=" * 70)
    print("Pulmonary Research Agent - Setup Verification")
    print("=" * 70)
    print()

    # Step 1: Check catalog
    catalog = check_catalog()
    if not catalog:
        print("\n❌ Catalog check failed. Run: make index-catalog")
        return False

    # Step 2: Check tools
    tools_ok = check_tools(catalog)
    if not tools_ok:
        print("\n⚠️  Some tools missing. Run: make index-catalog")
        print("   Then check: agentc ls tools")

    # Step 3: Check prompt
    prompt_ok = check_prompt(catalog)
    if not prompt_ok:
        print("\n⚠️  Prompt missing. Run: make index-catalog")
        print("   Then check: agentc ls prompts")

    # Step 4: Check agent initialization
    agent_ok = check_agent_init()

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    if tools_ok and prompt_ok and agent_ok:
        print("✅ All checks passed! Agent is ready to use.")
        print("\nNext steps:")
        print("  1. Start the app: make dev")
        print("  2. Navigate to patient page")
        print("  3. Click 'Research' tab")
        print("  4. Verify research results load")
        return True
    else:
        print("❌ Some checks failed.")
        print("\nTo fix:")
        print("  1. Run: make index-catalog")
        print("  2. Run this script again")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

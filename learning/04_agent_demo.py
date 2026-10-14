import asyncio
from app.agents.reviewer import audit_agent_app

async def test_run_multi_agent_system():
    print("🎬 Initializing Sandbox Agent Run...")
    
    # 1. Prepare a mock piece of poorly written Python code to test our agents
    mock_bad_code = """
def process_user_data(user_input):
    # CRITICAL SECURITY RISK: SQL Injection vulnerability
    query = "SELECT * FROM users WHERE username = '" + user_input + "'"
    db.execute(query)
    
    # PERFORMANCE RISK: Highly inefficient nested loop (O(N^2))
    items = [i for i in range(10000)]
    for x in items:
        for y in items:
            pass # Simulating an accidental massive computational bottleneck
            
    return True
"""

    # Mock repository map to test context awareness
    mock_repo_map = (
        "Repository: sandbox_app\n"
        "Location: /home/suraj/sandbox\n\n"
        "Files List:\n"
        "- main.py | Importance: High | Role: Core entry point for user requests\n"
        "- database.py | Importance: High | Role: Direct database connector and driver\n"
        "- sandbox_test.py | Importance: Medium | Role: User data processing logic\n"
    )

    # 2. Define the initial input matching our updated AuditState dictionary schema
    initial_scorecard = {
        "file_path": "sandbox_test.py",
        "source_code": mock_bad_code,
        "repo_path": "/home/suraj/sandbox",
        "repo_map": mock_repo_map,
        "retrieved_context": [
            "Context: The application does not use parameterized queries in db.execute in database.py."
        ],
        "security_draft": "",
        "performance_draft": "",
        "security_report": "",
        "performance_report": ""
    }

    print("🚀 Invoking LangGraph engine (calling Gemini asynchronously with parallel agents)...")
    
    # 3. Fire off the workflow execution graph
    final_output_state = await audit_agent_app.ainvoke(initial_scorecard)
    
    print("\n🏁 Workflow execution complete! Inspecting the final reconciled reports:\n")
    print("==================================================================")
    print("🛡️ RECONCILED SECURITY REPORT:")
    print("==================================================================")
    print(final_output_state.get("security_report"))
    print("\n==================================================================")
    print("⚡ RECONCILED PERFORMANCE REPORT:")
    print("==================================================================")
    print(final_output_state.get("performance_report"))
    print("==================================================================")

if __name__ == "__main__":
    # Fire up the async loop runner
    asyncio.run(test_run_multi_agent_system())
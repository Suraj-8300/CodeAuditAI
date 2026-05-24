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

    # 2. Define the initial input matching our AuditState dictionary schema
    initial_scorecard = {
        "file_path": "sandbox_test.py",
        "source_code": mock_bad_code,
        "retrieved_context": [],
        "security_report": "",
        "performance_report": "",
        "final_compiled_review": ""
    }

    print("🚀 Invoking LangGraph engine (calling Gemini asynchronously)...")
    
    # 3. Fire off the workflow execution graph
    final_output_state = await audit_agent_app.ainvoke(initial_scorecard)
    
    print("\n🏁 Workflow execution complete! Inspecting the final scorecard:\n")
    print("==================================================================")
    print("🛡️ SECURITY AGENT REPORT:")
    print("==================================================================")
    print(final_output_state["security_report"])
    print("\n==================================================================")
    print("⚡ PERFORMANCE AGENT REPORT:")
    print("==================================================================")
    print(final_output_state["performance_report"])
    print("==================================================================")

if __name__ == "__main__":
    # Fire up the async loop runner
    asyncio.run(test_run_multi_agent_system())
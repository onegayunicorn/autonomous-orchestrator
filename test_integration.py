from orchestrator import AutonomousOrchestrator
import json

def test_stripe_integration():
    print("Initializing Orchestrator...")
    orc = AutonomousOrchestrator()
    orc.start()
    
    print("\nQueueing Stripe Payment Command...")
    cmd = orc.queue_command("stripe", "pay")
    
    print("Executing Command...")
    result = orc.execute_next()
    
    if result and result.status == "completed":
        print("\n✅ Integration Test Passed!")
        print(f"Result: {result.result}")
    else:
        print("\n❌ Integration Test Failed!")
        if result:
            print(f"Error: {result.error}")
            
    orc.stop()

if __name__ == "__main__":
    test_stripe_integration()

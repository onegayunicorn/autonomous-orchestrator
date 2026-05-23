import sys
import os
from typing import Dict, Any, Optional

# Add the nfc-escrow-bridge path to sys.path to import Stripe modules
sys.path.append(os.path.abspath("../nfc-escrow-bridge-v2"))

from stripe.simulate.processor import StripeSimulator
from stripe.evaluate.risk import RiskEvaluator
from stripe.frame.request_builder import StripeFrameBuilder

class StripeOrchestratorAgent:
    """Agent that integrates Stripe functionality into the Autonomous Orchestrator."""
    
    def __init__(self):
        self.simulator = StripeSimulator()
        self.evaluator = RiskEvaluator()
        self.builder = StripeFrameBuilder()
        
    def process_payment(self, amount: int, currency: str = "usd", escrow_id: Optional[str] = None) -> Dict[str, Any]:
        """Orchestrates a complete payment flow."""
        print(f"StripeAgent: Starting payment process for {amount} {currency}...")
        
        # 1. Build the request frame
        frame = self.builder.build_payment_intent_frame(amount, currency, metadata={"escrow_id": escrow_id} if escrow_id else None)
        
        # 2. Evaluate Risk
        risk_result = self.evaluator.evaluate_transaction(frame)
        if not risk_result["is_safe"]:
            return {"status": "failed", "reason": "high_risk", "risk_report": risk_result}
            
        # 3. Simulate/Process Payment
        payment_result = self.simulator.simulate_payment_intent(amount, currency)
        
        return {
            "status": "success",
            "transaction_id": payment_result["id"],
            "risk_report": risk_result,
            "details": payment_result
        }

if __name__ == "__main__":
    agent = StripeOrchestratorAgent()
    result = agent.process_payment(5000, "usd", "escrow_999")
    print(f"Final Orchestration Result: {result}")

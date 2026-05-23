#!/usr/bin/env python3
"""
Stripe Agent for Autonomous Orchestrator - SA-007
===================================================
Bridge between Stripe API and Autonomous Orchestrator
Integrates with nfc-escrow-bridge-v2 for complete payment processing

Agent ID: SA-007
Name: Stripe Processor
Role: stripe
Risk Score: 5

PURPOSE:
- Process Stripe payments via real API or simulation
- Handle Stripe webhooks
- Integrate with Orchestrator commands
- Connect with NFC Escrow Bridge
- Support both live and test modes
"""

import sys
import os
import json
import logging
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

# Add nfc-escrow-bridge-v2 to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "nfc-escrow-bridge-v2")))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [SA-007] [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(os.path.expanduser("~/logs/stripe_agent.log")),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


# ============================================================================
# ENUMS & CONSTANTS
# ============================================================================

class PaymentStatus(Enum):
    """Stripe payment intent status"""
    REQUIRES_PAYMENT_METHOD = "requires_payment_method"
    REQUIRES_CONFIRMATION = "requires_confirmation"
    REQUIRES_ACTION = "requires_action"
    PROCESSING = "processing"
    SUCCEEDED = "succeeded"
    CANCELED = "canceled"


class WebhookEvent(Enum):
    """Stripe webhook event types"""
    PAYMENT_INTENT_CREATED = "payment_intent.created"
    PAYMENT_INTENT_SUCCEEDED = "payment_intent.succeeded"
    PAYMENT_INTENT_FAILED = "payment_intent.payment_failed"
    PAYMENT_INTENT_CANCELED = "payment_intent.canceled"
    CHARGE_SUCCEEDED = "charge.succeeded"
    CHARGE_FAILED = "charge.failed"
    CUSTOMER_CREATED = "customer.created"
    CUSTOMER_UPDATED = "customer.updated"


# Constants
STRIPE_API_VERSION = "2024-06-20"
STRIPE_DEFAULT_CURRENCY = "usd"
STRIPE_DEFAULT_TIMEOUT = 30.0


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class PaymentIntentData:
    """Stripe PaymentIntent data"""
    id: str
    amount: int
    currency: str
    status: str
    customer: Optional[str] = None
    payment_method: Optional[str] = None
    description: Optional[str] = None
    metadata: Dict[str, str] = field(default_factory=dict)
    created: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "amount": self.amount,
            "currency": self.currency,
            "status": self.status,
            "customer": self.customer,
            "payment_method": self.payment_method,
            "description": self.description,
            "metadata": self.metadata,
            "created": self.created,
        }


@dataclass
class CustomerData:
    """Stripe Customer data"""
    id: str
    email: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    metadata: Dict[str, str] = field(default_factory=dict)
    created: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "email": self.email,
            "name": self.name,
            "description": self.description,
            "metadata": self.metadata,
            "created": self.created,
        }


# ============================================================================
# STRIPE AGENT - MAIN CLASS
# ============================================================================

class StripeAgent:
    """
    SA-007: Stripe Processor Agent
    
    Complete Stripe integration for Autonomous Orchestrator:
    - Real Stripe API integration
    - Simulation mode for testing
    - Webhook handling
    - Orchestrator command execution
    - NFC Escrow Bridge integration
    """
    
    def __init__(self, api_key: Optional[str] = None, test_mode: bool = False):
        """Initialize Stripe Agent"""
        self.id = "SA-007"
        self.name = "Stripe Processor"
        self.role = "stripe"
        self.risk_score = 5
        self.description = "Processes Stripe payments and integrates with Orchestrator"
        self.test_mode = test_mode
        
        # Stripe configuration
        self.api_key = api_key or self._get_api_key()
        self.api_version = STRIPE_API_VERSION
        self.timeout = STRIPE_DEFAULT_TIMEOUT
        
        # Webhook configuration
        self.webhook_secret = self._get_webhook_secret()
        self.webhook_endpoint = "/stripe/webhook"
        
        # Statistics
        self.total_payments = 0
        self.successful_payments = 0
        self.failed_payments = 0
        self.total_amount = 0
        self.last_payment_time = 0.0
        
        # Initialize modules
        self._initialize_modules()
        
        logger.info(f"Stripe Agent {self.name} initialized")
        logger.info(f"Mode: {'TEST' if self.test_mode else 'LIVE'}")
        logger.info(f"API Key: {'***' + self.api_key[-4:] if self.api_key else 'NOT SET'}")
    
    def _get_api_key(self) -> Optional[str]:
        """Get Stripe API key from environment"""
        import os
        return os.getenv("STRIPE_SECRET_KEY") or os.getenv("STRIPE_API_KEY")
    
    def _get_webhook_secret(self) -> Optional[str]:
        """Get Stripe webhook secret from environment"""
        import os
        return os.getenv("STRIPE_WEBHOOK_SECRET")
    
    def _initialize_modules(self):
        """Initialize Stripe modules from nfc-escrow-bridge-v2"""
        try:
            # Import from nfc-escrow-bridge-v2
            from stripe.simulate.processor import StripeSimulator
            from stripe.evaluate.risk import RiskEvaluator
            from stripe.frame.request_builder import StripeFrameBuilder
            from stripe.model.transaction_model import StripeTransaction
            from stripe.model.risk_model import RiskModel
            
            # Initialize modules
            self.simulator = StripeSimulator()
            self.evaluator = RiskEvaluator()
            self.builder = StripeFrameBuilder()
            self.risk_model = RiskModel()
            
            logger.info("Stripe modules initialized from nfc-escrow-bridge-v2")
            
        except ImportError as e:
            logger.warning(f"Could not import from nfc-escrow-bridge-v2: {e}")
            logger.info("Using fallback Stripe SDK")
            self.simulator = None
            self.evaluator = None
            self.builder = None
            self.risk_model = None
            
            # Try to initialize Stripe SDK
            self._initialize_stripe_sdk()
    
    def _initialize_stripe_sdk(self):
        """Initialize Stripe SDK"""
        try:
            import stripe
            if self.api_key:
                stripe.api_key = self.api_key
                stripe.api_version = self.api_version
                logger.info("Stripe SDK initialized")
            else:
                logger.warning("Stripe API key not set. Some features will be disabled.")
        except ImportError:
            logger.error("Stripe SDK not installed. Install with: pip install stripe")
    
    def create_payment_intent(
        self,
        amount: int,
        currency: str = STRIPE_DEFAULT_CURRENCY,
        customer: Optional[str] = None,
        payment_method: Optional[str] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
        **kwargs,
    ) -> PaymentIntentData:
        """
        Create a Stripe PaymentIntent
        Uses simulation if test_mode=True or no API key
        """
        if self.test_mode or not self.api_key:
            # Use simulator
            return self._create_simulated_payment_intent(
                amount, currency, customer, payment_method, 
                description, metadata, **kwargs
            )
        else:
            # Use real Stripe API
            return self._create_real_payment_intent(
                amount, currency, customer, payment_method,
                description, metadata, **kwargs
            )
    
    def _create_simulated_payment_intent(
        self,
        amount: int,
        currency: str,
        customer: Optional[str],
        payment_method: Optional[str],
        description: Optional[str],
        metadata: Optional[Dict[str, str]],
        **kwargs,
    ) -> PaymentIntentData:
        """Create a simulated PaymentIntent"""
        import secrets
        
        intent_id = f"pi_sim_{secrets.token_hex(12)}"
        status = kwargs.get("status", "succeeded")
        
        # Update statistics
        self.total_payments += 1
        self.total_amount += amount
        self.last_payment_time = time.time()
        
        if status == "succeeded":
            self.successful_payments += 1
        else:
            self.failed_payments += 1
        
        logger.info(f"Simulated PaymentIntent: {intent_id} (${amount / 100:.2f} {currency})")
        
        return PaymentIntentData(
            id=intent_id,
            amount=amount,
            currency=currency,
            status=status,
            customer=customer or f"cus_sim_{secrets.token_hex(12)}",
            payment_method=payment_method or f"pm_sim_{secrets.token_hex(12)}",
            description=description,
            metadata=metadata or {},
            created=time.time(),
        )
    
    def _create_real_payment_intent(
        self,
        amount: int,
        currency: str,
        customer: Optional[str],
        payment_method: Optional[str],
        description: Optional[str],
        metadata: Optional[Dict[str, str]],
        **kwargs,
    ) -> PaymentIntentData:
        """Create a real PaymentIntent using Stripe API"""
        try:
            import stripe
            
            if not self.api_key:
                raise ValueError("Stripe API key not configured")
            
            # Prepare parameters
            params = {
                "amount": amount,
                "currency": currency,
            }
            
            if customer:
                params["customer"] = customer
            if payment_method:
                params["payment_method"] = payment_method
            if description:
                params["description"] = description
            if metadata:
                params["metadata"] = metadata
            params.update(kwargs)
            
            # Create PaymentIntent
            intent = stripe.PaymentIntent.create(**params)
            
            # Update statistics
            self.total_payments += 1
            self.total_amount += amount
            self.last_payment_time = time.time()
            
            logger.info(f"Created PaymentIntent: {intent.id} (${amount / 100:.2f} {currency})")
            
            return PaymentIntentData(
                id=intent.id,
                amount=intent.amount,
                currency=intent.currency,
                status=intent.status,
                customer=intent.customer,
                payment_method=intent.payment_method,
                description=intent.description,
                metadata=intent.metadata or {},
                created=intent.created,
            )
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error: {str(e)}")
            raise
    
    def retrieve_payment_intent(self, intent_id: str) -> PaymentIntentData:
        """Retrieve a PaymentIntent by ID"""
        if self.test_mode or not self.api_key:
            # Return simulated data
            import secrets
            return PaymentIntentData(
                id=intent_id,
                amount=1000,
                currency="usd",
                status="succeeded",
                customer=f"cus_sim_{secrets.token_hex(12)}",
                payment_method=f"pm_sim_{secrets.token_hex(12)}",
                metadata={"simulated": True},
                created=time.time(),
            )
        else:
            # Use real Stripe API
            try:
                import stripe
                intent = stripe.PaymentIntent.retrieve(intent_id)
                return PaymentIntentData(
                    id=intent.id,
                    amount=intent.amount,
                    currency=intent.currency,
                    status=intent.status,
                    customer=intent.customer,
                    payment_method=intent.payment_method,
                    description=intent.description,
                    metadata=intent.metadata or {},
                    created=intent.created,
                )
            except stripe.error.StripeError as e:
                logger.error(f"Error retrieving PaymentIntent {intent_id}: {str(e)}")
                raise
    
    def confirm_payment_intent(
        self,
        intent_id: str,
        payment_method: Optional[str] = None,
        **kwargs,
    ) -> PaymentIntentData:
        """Confirm a PaymentIntent"""
        if self.test_mode or not self.api_key:
            # Simulate confirmation
            import secrets
            status = kwargs.get("status", "succeeded")
            return PaymentIntentData(
                id=intent_id,
                amount=1000,
                currency="usd",
                status=status,
                customer=f"cus_sim_{secrets.token_hex(12)}",
                payment_method=payment_method or f"pm_sim_{secrets.token_hex(12)}",
                metadata={"simulated": True, "confirmed": True},
                created=time.time(),
            )
        else:
            # Use real Stripe API
            try:
                import stripe
                params = {}
                if payment_method:
                    params["payment_method"] = payment_method
                params.update(kwargs)
                intent = stripe.PaymentIntent.confirm(intent_id, **params)
                return PaymentIntentData(
                    id=intent.id,
                    amount=intent.amount,
                    currency=intent.currency,
                    status=intent.status,
                    customer=intent.customer,
                    payment_method=intent.payment_method,
                    description=intent.description,
                    metadata=intent.metadata or {},
                    created=intent.created,
                )
            except stripe.error.StripeError as e:
                logger.error(f"Error confirming PaymentIntent {intent_id}: {str(e)}")
                raise
    
    def create_customer(
        self,
        email: Optional[str] = None,
        name: Optional[str] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
        **kwargs,
    ) -> CustomerData:
        """Create a Stripe Customer"""
        if self.test_mode or not self.api_key:
            # Simulate customer creation
            import secrets
            customer_id = f"cus_sim_{secrets.token_hex(12)}"
            return CustomerData(
                id=customer_id,
                email=email or f"test_{secrets.token_hex(8)}@example.com",
                name=name or "Test Customer",
                description=description,
                metadata=metadata or {},
                created=time.time(),
            )
        else:
            # Use real Stripe API
            try:
                import stripe
                params = {}
                if email:
                    params["email"] = email
                if name:
                    params["name"] = name
                if description:
                    params["description"] = description
                if metadata:
                    params["metadata"] = metadata
                params.update(kwargs)
                customer = stripe.Customer.create(**params)
                return CustomerData(
                    id=customer.id,
                    email=customer.email,
                    name=customer.name,
                    description=customer.description,
                    metadata=customer.metadata or {},
                    created=customer.created,
                )
            except stripe.error.StripeError as e:
                logger.error(f"Error creating Customer: {str(e)}")
                raise
    
    def handle_webhook(self, payload: bytes, signature: str) -> Optional[Dict[str, Any]]:
        """
        Handle Stripe webhook event
        Validates signature and processes the event
        """
        try:
            import stripe
            import hmac
            import hashlib
            
            # In test mode, skip signature verification
            if self.test_mode or not self.webhook_secret:
                logger.info("Skipping webhook signature verification (test mode or no secret)")
                event = json.loads(payload)
            else:
                # Verify webhook signature
                try:
                    event = stripe.Webhook.construct_event(
                        payload, signature, self.webhook_secret
                    )
                except stripe.error.SignatureVerificationError as e:
                    logger.error(f"Webhook signature verification failed: {str(e)}")
                    return None
            
            # Parse event
            event_type = event.get("type")
            event_data = event.get("data", {})
            
            logger.info(f"Webhook received: {event_type}")
            
            # Execute orchestrator command based on event
            self._execute_orchestrator_command(event_type, event_data)
            
            return {
                "status": "processed",
                "event_type": event_type,
                "event_data": event_data,
            }
            
        except json.JSONDecodeError:
            logger.error("Invalid webhook payload (not JSON)")
            return None
        except Exception as e:
            logger.error(f"Error handling webhook: {str(e)}")
            return None
    
    def _execute_orchestrator_command(
        self,
        event_type: str,
        event_data: Dict[str, Any],
    ) -> None:
        """
        Execute Orchestrator command based on webhook event
        Uses command mappings from nfc-escrow-bridge-v2
        """
        try:
            import subprocess
            
            # Map event types to commands
            command_map = {
                "payment_intent.succeeded": "queue orchestration start",
                "payment_intent.created": "queue orchestration start",
                "payment_intent.payment_failed": "queue orchestration stop",
                "payment_intent.canceled": "queue orchestration stop",
                "charge.succeeded": "queue quantum sync",
                "charge.failed": "queue system health",
                "customer.created": "queue system status",
                "customer.updated": "queue system metrics",
            }
            
            command = command_map.get(event_type, "status")
            
            # Extract payment intent data
            payment_intent = event_data.get("object", {})
            amount = payment_intent.get("amount", 0)
            currency = payment_intent.get("currency", "usd")
            intent_id = payment_intent.get("id", "unknown")
            
            logger.info(f"Executing: {command}")
            logger.info(f"Payment: {intent_id} (${amount / 100:.2f} {currency})")
            
            # Execute command
            result = subprocess.run(
                ["python3", "orchestrator.py", "--command", command],
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
            
            if result.returncode == 0:
                logger.info(f"Command executed: {result.stdout}")
            else:
                logger.error(f"Command failed: {result.stderr}")
                
        except subprocess.TimeoutExpired:
            logger.error(f"Command timed out after {self.timeout}s")
        except Exception as e:
            logger.error(f"Error executing command: {str(e)}")
    
    def process_payment(
        self,
        amount: int,
        currency: str = "usd",
        escrow_id: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Process a complete payment flow
        Combines simulation, risk evaluation, and command execution
        """
        print(f"StripeAgent: Processing payment for ${amount / 100:.2f} {currency}...")
        
        # Step 1: Build the request frame
        if self.builder:
            frame = self.builder.build_payment_intent_frame(
                amount, currency, 
                metadata={"escrow_id": escrow_id} if escrow_id else None
            )
        else:
            frame = {"amount": amount, "currency": currency}
            if escrow_id:
                frame["metadata"] = {"escrow_id": escrow_id}
        
        # Step 2: Evaluate Risk
        if self.evaluator:
            risk_result = self.evaluator.evaluate_transaction(frame)
            if not risk_result.get("is_safe", True):
                return {
                    "status": "failed",
                    "reason": "high_risk",
                    "risk_report": risk_result
                }
        else:
            risk_result = {"is_safe": True, "risk_score": 0.1}
        
        # Step 3: Create Payment Intent
        payment_result = self.create_payment_intent(
            amount, currency, 
            metadata={"escrow_id": escrow_id} if escrow_id else None
        )
        
        # Step 4: Execute Orchestrator command if payment succeeded
        if payment_result.status == "succeeded":
            self._execute_orchestrator_command(
                "payment_intent.succeeded",
                {"object": payment_result.to_dict()}
            )
        
        return {
            "status": "success",
            "transaction_id": payment_result.id,
            "amount": payment_result.amount,
            "currency": payment_result.currency,
            "risk_report": risk_result,
            "payment_intent": payment_result.to_dict(),
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get Stripe Agent statistics"""
        return {
            "id": self.id,
            "name": self.name,
            "role": self.role,
            "risk_score": self.risk_score,
            "mode": "TEST" if self.test_mode else "LIVE",
            "total_payments": self.total_payments,
            "successful_payments": self.successful_payments,
            "failed_payments": self.failed_payments,
            "total_amount": self.total_amount,
            "total_amount_usd": round(self.total_amount / 100, 2),
            "last_payment_time": self.last_payment_time,
            "api_key_configured": bool(self.api_key),
            "webhook_secret_configured": bool(self.webhook_secret),
        }
    
    def start(self) -> None:
        """Start Stripe Agent"""
        logger.info(f"Stripe Agent {self.name} started")
    
    def stop(self) -> None:
        """Stop Stripe Agent"""
        logger.info(f"Stripe Agent {self.name} stopped")


# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    import os
    
    # Determine mode from environment
    test_mode = os.getenv("STRIPE_TEST_MODE", "true").lower() == "true"
    
    # Create Stripe Agent
    stripe_agent = StripeAgent(test_mode=test_mode)
    stripe_agent.start()
    
    print("\n" + "=" * 60)
    print(f"STRIPE AGENT {stripe_agent.name}")
    print("=" * 60)
    print(f"ID: {stripe_agent.id}")
    print(f"Role: {stripe_agent.role}")
    print(f"Risk Score: {stripe_agent.risk_score}")
    print(f"Mode: {'TEST' if test_mode else 'LIVE'}")
    print(f"API Key: {'SET' if stripe_agent.api_key else 'NOT SET'}")
    print("=" * 60)
    
    # Test payment processing
    print("\nTesting payment processing...")
    result = stripe_agent.process_payment(
        amount=5000,  # $50.00
        currency="usd",
        escrow_id="escrow_999"
    )
    print(f"\nResult: {json.dumps(result, indent=2)}")
    
    # Test payment intent creation
    print("\nTesting PaymentIntent creation...")
    intent = stripe_agent.create_payment_intent(
        amount=1000,
        currency="usd",
        description="Test payment",
        metadata={"test": True, "orchestrator": True}
    )
    print(f"PaymentIntent: {intent.id} (${intent.amount / 100:.2f})")
    
    # Test customer creation
    print("\nTesting Customer creation...")
    customer = stripe_agent.create_customer(
        email="test@example.com",
        name="Test Customer",
        description="Test customer for orchestrator"
    )
    print(f"Customer: {customer.id} ({customer.email})")
    
    # Print stats
    print("\nStats:")
    stats = stripe_agent.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    print("\n" + "=" * 60)
    print("Stripe Agent ready!")
    print("Use in orchestrator: from stripe_agent import StripeAgent")
    print("=" * 60)

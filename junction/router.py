#!/usr/bin/env python3
"""
J09 Router Module
==================
Intelligent request routing for J09 Junction Agent

Provides:
- AI-powered request routing
- Dynamic target selection
- Load balancing across systems
- Priority-based routing
- Circuit breaker pattern
"""

import json
import logging
import time
import random
from typing import Dict, List, Optional, Any, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum, auto
from collections import defaultdict

logger = logging.getLogger(__name__)


# ============================================================================
# ENUMS & CONSTANTS
# ============================================================================

class RoutingStrategy(Enum):
    """Routing strategies"""
    RANDOM = auto()
    ROUND_ROBIN = auto()
    LEAST_CONNECTIONS = auto()
    LEAST_LATENCY = auto()
    WEIGHTED = auto()
    PRIORITY = auto()


class TargetHealth(Enum):
    """Health status of routing targets"""
    HEALTHY = auto()
    DEGRADED = auto()
    UNHEALTHY = auto()
    OFFLINE = auto()


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class RoutingRule:
    """Rule for routing requests"""
    name: str
    source_pattern: str
    target_system: str
    conditions: Dict[str, Any] = field(default_factory=dict)
    priority: int = 0
    weight: float = 1.0
    
    def matches(self, source: str, payload: Dict[str, Any]) -> bool:
        """Check if this rule matches the request"""
        # Check source pattern
        if "*" in self.source_pattern:
            # Wildcard matching
            if not source.startswith(self.source_pattern.replace("*", "")):
                return False
        elif source != self.source_pattern:
            return False
        
        # Check conditions
        for key, value in self.conditions.items():
            if payload.get(key) != value:
                return False
        
        return True


@dataclass
class RoutingTarget:
    """Target system for routing"""
    name: str
    system: str
    endpoint: str
    priority: int = 0
    weight: float = 1.0
    health: TargetHealth = TargetHealth.HEALTHY
    connections: int = 0
    last_latency: float = 0.0
    last_check: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "system": self.system,
            "endpoint": self.endpoint,
            "priority": self.priority,
            "weight": self.weight,
            "health": self.health.name,
            "connections": self.connections,
            "last_latency": self.last_latency,
        }


@dataclass
class RoutingDecision:
    """Decision made by the router"""
    request_id: str
    source: str
    target: RoutingTarget
    rule: Optional[RoutingRule]
    reason: str
    priority: int
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "source": self.source,
            "target": self.target.to_dict(),
            "rule": self.rule.name if self.rule else None,
            "reason": self.reason,
            "priority": self.priority,
        }


# ============================================================================
# ROUTER
# ============================================================================

class Router:
    """
    Intelligent request router for J09 Junction Agent
    
    Uses multiple strategies to determine the best target for a request:
    - Rule-based matching
    - Priority-based routing
    - Load balancing
    - Health-based selection
    - AI-powered decision making
    """
    
    def __init__(self, strategy: RoutingStrategy = RoutingStrategy.PRIORITY):
        self.strategy = strategy
        self.rules: List[RoutingRule] = []
        self.targets: Dict[str, RoutingTarget] = {}
        self.routing_history: List[RoutingDecision] = []
        self.circuit_breakers: Dict[str, Any] = {}
        
        # Initialize default rules
        self._initialize_default_rules()
        
        # Initialize default targets
        self._initialize_default_targets()
        
        logger.info(f"Router initialized with {len(self.rules)} rules and {len(self.targets)} targets")
    
    def _initialize_default_rules(self):
        """Initialize default routing rules"""
        # Stripe-related requests
        self.rules.append(RoutingRule(
            name="stripe_to_orchestrator",
            source_pattern="stripe",
            target_system="orchestrator",
            conditions={"type": "payment"},
            priority=10,
        ))
        
        self.rules.append(RoutingRule(
            name="stripe_to_nfc",
            source_pattern="stripe",
            target_system="nfc_escrow",
            conditions={"type": "nfc_payment"},
            priority=8,
        ))
        
        # NFC-related requests
        self.rules.append(RoutingRule(
            name="nfc_to_stripe",
            source_pattern="nfc*",
            target_system="stripe",
            conditions={"action": "payment"},
            priority=9,
        ))
        
        self.rules.append(RoutingRule(
            name="nfc_to_escrow",
            source_pattern="nfc*",
            target_system="nfc_escrow",
            conditions={"action": "escrow"},
            priority=10,
        ))
        
        # Orchestrator requests
        self.rules.append(RoutingRule(
            name="orchestrator_to_stripe",
            source_pattern="orchestrator",
            target_system="stripe",
            conditions={"category": "payment"},
            priority=7,
        ))
        
        # Quantum requests
        self.rules.append(RoutingRule(
            name="quantum_to_orchestrator",
            source_pattern="quantum*",
            target_system="orchestrator",
            priority=5,
        ))
        
        # Default rule
        self.rules.append(RoutingRule(
            name="default",
            source_pattern="*",
            target_system="orchestrator",
            priority=1,
        ))
        
        logger.info(f"Initialized {len(self.rules)} default routing rules")
    
    def _initialize_default_targets(self):
        """Initialize default routing targets"""
        # Stripe API
        self.add_target(RoutingTarget(
            name="stripe_api",
            system="stripe",
            endpoint="https://api.stripe.com/v1",
            priority=10,
            weight=1.0,
        ))
        
        # NFC Escrow Bridge
        self.add_target(RoutingTarget(
            name="nfc_escrow",
            system="nfc_escrow",
            endpoint="http://localhost:8000",
            priority=9,
            weight=1.0,
        ))
        
        # Autonomous Orchestrator
        self.add_target(RoutingTarget(
            name="orchestrator",
            system="orchestrator",
            endpoint="http://localhost:8081",
            priority=8,
            weight=1.0,
        ))
        
        # Quantum System
        self.add_target(RoutingTarget(
            name="quantum",
            system="quantum",
            endpoint="localhost:50051",
            priority=7,
            weight=1.0,
        ))
        
        logger.info(f"Initialized {len(self.targets)} default routing targets")
    
    def add_rule(self, rule: RoutingRule) -> None:
        """Add a new routing rule"""
        self.rules.append(rule)
        # Sort rules by priority (descending)
        self.rules.sort(key=lambda r: -r.priority)
        logger.info(f"Added routing rule: {rule.name}")
    
    def remove_rule(self, name: str) -> bool:
        """Remove a routing rule"""
        for i, rule in enumerate(self.rules):
            if rule.name == name:
                del self.rules[i]
                logger.info(f"Removed routing rule: {name}")
                return True
        return False
    
    def add_target(self, target: RoutingTarget) -> None:
        """Add a new routing target"""
        self.targets[target.name] = target
        logger.info(f"Added routing target: {target.name}")
    
    def remove_target(self, name: str) -> bool:
        """Remove a routing target"""
        if name in self.targets:
            del self.targets[name]
            logger.info(f"Removed routing target: {name}")
            return True
        return False
    
    def get_target(self, name: str) -> Optional[RoutingTarget]:
        """Get a routing target by name"""
        return self.targets.get(name)
    
    def list_targets(self) -> List[RoutingTarget]:
        """List all routing targets"""
        return list(self.targets.values())
    
    def list_rules(self) -> List[RoutingRule]:
        """List all routing rules"""
        return self.rules
    
    def route(
        self,
        source: str,
        payload: Dict[str, Any],
        priority: int = 0,
    ) -> RoutingDecision:
        """
        Route a request to the appropriate target
        
        Args:
            source: Source system name
            payload: Request payload
            priority: Request priority override
            
        Returns:
            RoutingDecision with selected target
        """
        # Find matching rules
        matching_rules = []
        for rule in self.rules:
            if rule.matches(source, payload):
                matching_rules.append(rule)
        
        # Select best rule
        best_rule = None
        if matching_rules:
            # Use highest priority rule
            best_rule = matching_rules[0]
        else:
            # Use default rule
            best_rule = next((r for r in self.rules if r.name == "default"), None)
        
        # Get target system
        if not best_rule:
            raise ValueError(f"No routing rule found for source: {source}")
        
        target_system = best_rule.target_system
        
        # Get all targets for this system
        system_targets = [
            t for t in self.targets.values() 
            if t.system == target_system and t.health != TargetHealth.OFFLINE
        ]
        
        if not system_targets:
            raise ValueError(f"No healthy targets found for system: {target_system}")
        
        # Select target based on strategy
        target = self._select_target(system_targets, priority)
        
        # Record decision
        decision = RoutingDecision(
            request_id=f"route_{int(time.time())}",
            source=source,
            target=target,
            rule=best_rule,
            reason=f"Matched rule: {best_rule.name}" if best_rule else "Default",
            priority=priority or best_rule.priority,
        )
        
        self.routing_history.append(decision)
        
        # Update target connections
        target.connections += 1
        
        return decision
    
    def _select_target(
        self,
        targets: List[RoutingTarget],
        priority: int = 0,
    ) -> RoutingTarget:
        """Select the best target based on routing strategy"""
        if not targets:
            raise ValueError("No targets available")
        
        if self.strategy == RoutingStrategy.RANDOM:
            return random.choice(targets)
        
        elif self.strategy == RoutingStrategy.ROUND_ROBIN:
            # Simple round-robin (would need state in production)
            return targets[0]
        
        elif self.strategy == RoutingStrategy.LEAST_CONNECTIONS:
            return min(targets, key=lambda t: t.connections)
        
        elif self.strategy == RoutingStrategy.LEAST_LATENCY:
            return min(targets, key=lambda t: t.last_latency)
        
        elif self.strategy == RoutingStrategy.WEIGHTED:
            weights = [t.weight for t in targets]
            return random.choices(targets, weights=weights, k=1)[0]
        
        elif self.strategy == RoutingStrategy.PRIORITY:
            # Sort by priority (descending), then by connections (ascending)
            return sorted(
                targets,
                key=lambda t: (-t.priority, t.connections),
            )[0]
        
        else:
            return targets[0]
    
    def update_target_health(
        self,
        name: str,
        health: TargetHealth,
        latency: Optional[float] = None,
    ) -> bool:
        """Update the health status of a target"""
        target = self.get_target(name)
        if not target:
            return False
        
        target.health = health
        if latency is not None:
            target.last_latency = latency
        target.last_check = time.time()
        
        logger.info(f"Updated target {name} health: {health.name}")
        return True
    
    def check_target_health(self, name: str) -> bool:
        """Check the health of a target"""
        target = self.get_target(name)
        if not target:
            return False
        
        # Simulate health check
        try:
            # In production, this would make a real health check request
            start_time = time.time()
            time.sleep(0.1)  # Simulate network latency
            latency = time.time() - start_time
            
            # Random health status for demo
            statuses = [TargetHealth.HEALTHY, TargetHealth.HEALTHY, TargetHealth.DEGRADED]
            health = random.choice(statuses)
            
            self.update_target_health(name, health, latency)
            return True
            
        except Exception as e:
            self.update_target_health(name, TargetHealth.OFFLINE)
            logger.error(f"Health check failed for {name}: {e}")
            return False
    
    def check_all_targets(self) -> Dict[str, TargetHealth]:
        """Check health of all targets"""
        results = {}
        for name in self.targets:
            results[name] = self.check_target_health(name)
        return results
    
    def set_strategy(self, strategy: RoutingStrategy) -> None:
        """Set the routing strategy"""
        self.strategy = strategy
        logger.info(f"Routing strategy set to: {strategy.name}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get router status"""
        return {
            "strategy": self.strategy.name,
            "rules_count": len(self.rules),
            "targets_count": len(self.targets),
            "routing_history_count": len(self.routing_history),
            "targets": {k: v.to_dict() for k, v in self.targets.items()},
        }
    
    def reset_statistics(self) -> None:
        """Reset routing statistics"""
        for target in self.targets.values():
            target.connections = 0
            target.last_latency = 0.0
        self.routing_history.clear()
        logger.info("Routing statistics reset")


# ============================================================================
# AI ROUTER (Advanced)
# ============================================================================

class AIRouter:
    """
    AI-powered router with machine learning capabilities
    
    Uses historical data to make intelligent routing decisions.
    """
    
    def __init__(self):
        self.router = Router()
        self.learning_data: List[Dict[str, Any]] = []
        
        logger.info("AI Router initialized")
    
    def route(self, source: str, payload: Dict[str, Any]) -> RoutingDecision:
        """Route with AI enhancement"""
        decision = self.router.route(source, payload)
        
        # Record for learning
        self.learning_data.append({
            "source": source,
            "payload": payload,
            "target": decision.target.name,
            "success": True,  # Would track actual success in production
            "timestamp": time.time(),
        })
        
        # In production, would use ML model to predict best target
        # For now, just use standard routing
        
        return decision
    
    def train(self) -> None:
        """Train the AI model (placeholder)"""
        # In production, would train a model on historical data
        logger.info(f"Training AI router on {len(self.learning_data)} samples")
    
    def predict_best_target(self, source: str, payload: Dict[str, Any]) -> str:
        """Predict the best target using AI (placeholder)"""
        # In production, would use trained model
        # For now, use standard routing
        decision = self.router.route(source, payload)
        return decision.target.name


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    # Test Router
    router = Router()
    
    print("\n" + "=" * 60)
    print("J09 Router Test")
    print("=" * 60)
    
    # Test routing
    print("\nRouting requests...")
    
    # Route Stripe payment
    decision = router.route(
        source="stripe",
        payload={"type": "payment", "amount": 1000},
    )
    print(f"Stripe payment -> {decision.target.system} ({decision.reason})")
    
    # Route NFC tag
    decision = router.route(
        source="nfc_reader",
        payload={"action": "payment", "tag_id": "tag_123"},
    )
    print(f"NFC payment -> {decision.target.system} ({decision.reason})")
    
    # Route Orchestrator command
    decision = router.route(
        source="orchestrator",
        payload={"category": "system", "command": "status"},
    )
    print(f"Orchestrator command -> {decision.target.system} ({decision.reason})")
    
    # Print router status
    print("\nRouter Status:")
    print(json.dumps(router.get_status(), indent=2))
    
    print("\n" + "=" * 60)
    print("Router test complete!")
    print("=" * 60)

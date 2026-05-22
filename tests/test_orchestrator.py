#!/usr/bin/env python3
"""
Tests for Autonomous Orchestrator
Run with: pytest tests/test_orchestrator.py -v
"""

import pytest
import time
from orchestrator import AutonomousOrchestrator, Agent, Command, SystemStatus
from agents import AgentRegistry, AgentRole, AgentStatus


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def orchestrator():
    """Create a fresh orchestrator instance for each test."""
    orch = AutonomousOrchestrator()
    orch.start()
    yield orch
    orch.stop()


@pytest.fixture
def registry():
    """Create a fresh agent registry for each test."""
    return AgentRegistry()


# ============================================================================
# ORCHESTRATOR TESTS
# ============================================================================

class TestAutonomousOrchestrator:
    """Tests for the AutonomousOrchestrator class."""
    
    def test_initialization(self, orchestrator):
        """Test orchestrator initializes correctly."""
        assert orchestrator.agents is not None
        assert len(orchestrator.agents) == 42
        assert orchestrator.system_status is not None
        assert orchestrator.command_queue == []
        assert orchestrator.running is True
        assert orchestrator.start_time > 0
        assert len(orchestrator.sovereign_key) == 64  # 256-bit hex = 64 chars
    
    def test_get_status(self, orchestrator):
        """Test get_status returns correct structure."""
        status = orchestrator.get_status()
        
        assert status["version"] == "7.0.0"
        assert status["fold_entry"] == "FE-OGUF-P1"
        assert status["coherence"] == 0.99997
        assert status["entanglement_pairs"] == 288
        assert status["agents_active"] == 42
        assert status["commands_queued"] == 0
        assert status["commands_completed"] == 0
        assert status["risk_score"] == 27
        assert status["sovereign_architect"] == "Tyrone J Power Ω"
        assert "agents" in status
        assert len(status["agents"]) == 42
    
    def test_queue_command(self, orchestrator):
        """Test queuing a command."""
        cmd = orchestrator.queue_command("system", "status")
        
        assert cmd is not None
        assert cmd.name == "status"
        assert cmd.category == "system"
        assert cmd.status == "pending"
        assert len(orchestrator.command_queue) == 1
        assert cmd.id in orchestrator.commands
    
    def test_queue_multiple_commands(self, orchestrator):
        """Test queuing multiple commands."""
        orchestrator.queue_command("system", "status")
        orchestrator.queue_command("system", "health")
        orchestrator.queue_command("quantum", "coherence")
        
        assert len(orchestrator.command_queue) == 3
        assert len(orchestrator.commands) == 3
    
    def test_execute_next(self, orchestrator):
        """Test executing the next command."""
        orchestrator.queue_command("system", "health")
        
        result = orchestrator.execute_next()
        
        assert result is not None
        assert result.name == "health"
        assert result.status == "completed"
        assert len(orchestrator.command_queue) == 0
        assert orchestrator.system_status.commands_completed == 1
    
    def test_execute_all(self, orchestrator):
        """Test executing all queued commands."""
        orchestrator.queue_command("system", "status")
        orchestrator.queue_command("system", "health")
        orchestrator.queue_command("quantum", "coherence")
        
        results = orchestrator.execute_all()
        
        assert len(results) == 3
        assert len(orchestrator.command_queue) == 0
        assert orchestrator.system_status.commands_completed == 3
    
    def test_command_whitelist(self, orchestrator):
        """Test that only whitelisted commands work."""
        # This should work
        cmd = orchestrator.queue_command("system", "status")
        assert cmd is not None
        
        # This should also work (it's in the config)
        cmd = orchestrator.queue_command("quantum", "calibrate")
        assert cmd is not None
    
    def test_risk_scoring(self, orchestrator):
        """Test risk scoring for commands."""
        # Low risk command
        cmd = orchestrator.queue_command("system", "status")
        assert cmd.risk_level.value <= 30
        
        # High risk command
        cmd = orchestrator.queue_command("orchestration", "start")
        assert cmd.risk_level.value > 60
        
        # Critical risk command
        cmd = orchestrator.queue_command("temporal", "anchor")
        assert cmd.risk_level.value > 80


# ============================================================================
# AGENT REGISTRY TESTS
# ============================================================================

class TestAgentRegistry:
    """Tests for the AgentRegistry class."""
    
    def test_initialization(self, registry):
        """Test registry initializes with 42 agents."""
        assert len(registry.agents) == 42
    
    def test_get_agent(self, registry):
        """Test getting an agent by ID."""
        agent = registry.get_agent("QA-001")
        assert agent is not None
        assert agent.name == "Quantum Nexus"
        assert agent.role == AgentRole.QUANTUM
    
    def test_get_agent_not_found(self, registry):
        """Test getting a non-existent agent."""
        agent = registry.get_agent("NONEXISTENT")
        assert agent is None
    
    def test_get_agents_by_role(self, registry):
        """Test getting agents by role."""
        quantum_agents = registry.get_agents_by_role(AgentRole.QUANTUM)
        assert len(quantum_agents) == 6
        
        orchestration_agents = registry.get_agents_by_role(AgentRole.ORCHESTRATION)
        assert len(orchestration_agents) == 6
        
        execution_agents = registry.get_agents_by_role(AgentRole.EXECUTION)
        assert len(execution_agents) == 6
        
        security_agents = registry.get_agents_by_role(AgentRole.SECURITY)
        assert len(security_agents) == 6
        
        monitoring_agents = registry.get_agents_by_role(AgentRole.MONITORING)
        assert len(monitoring_agents) == 5
    
    def test_get_available_agents(self, registry):
        """Test getting available agents."""
        available = registry.get_available_agents()
        assert len(available) == 42  # All should be IDLE initially
    
    def test_to_dict(self, registry):
        """Test converting registry to dictionary."""
        data = registry.to_dict()
        assert data["total_agents"] == 42
        assert "agents" in data
        assert "by_role" in data
    
    def test_to_json(self, registry):
        """Test converting registry to JSON."""
        json_str = registry.to_json()
        assert "Quantum Nexus" in json_str
        assert "42" in json_str


# ============================================================================
# AGENT TESTS
# ============================================================================

class TestAgent:
    """Tests for the Agent class."""
    
    def test_agent_creation(self):
        """Test creating an agent."""
        agent = Agent(
            id="TEST-001",
            name="Test Agent",
            role=AgentRole.QUANTUM,
            description="Test description"
        )
        
        assert agent.id == "TEST-001"
        assert agent.name == "Test Agent"
        assert agent.role == AgentRole.QUANTUM
        assert agent.status == AgentStatus.IDLE
        assert agent.commands_executed == 0
        assert agent.success_rate == 1.0
    
    def test_agent_to_dict(self):
        """Test converting agent to dictionary."""
        agent = Agent(
            id="TEST-001",
            name="Test Agent",
            role=AgentRole.QUANTUM,
            description="Test description"
        )
        
        data = agent.to_dict()
        assert data["id"] == "TEST-001"
        assert data["name"] == "Test Agent"
        assert data["role"] == "quantum"
        assert data["status"] == "IDLE"
    
    def test_agent_execute(self):
        """Test agent command execution."""
        agent = Agent(
            id="TEST-001",
            name="Test Agent",
            role=AgentRole.QUANTUM,
            description="Test description"
        )
        
        result = agent.execute("calibrate")
        assert result is not None
        assert agent.status == AgentStatus.IDLE
        assert agent.commands_executed == 1


# ============================================================================
# SYSTEM STATUS TESTS
# ============================================================================

class TestSystemStatus:
    """Tests for SystemStatus."""
    
    def test_default_values(self):
        """Test default system status values."""
        status = SystemStatus()
        
        assert status.coherence == 0.99997
        assert status.entanglement_pairs == 288
        assert status.agents_active == 0
        assert status.commands_queued == 0
        assert status.commands_completed == 0
        assert status.risk_score == 27
        assert status.uptime == 0.0


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestIntegration:
    """Integration tests for the full system."""
    
    def test_full_workflow(self, orchestrator):
        """Test a complete workflow: queue -> execute -> verify."""
        # Queue commands
        orchestrator.queue_command("system", "status")
        orchestrator.queue_command("system", "health")
        orchestrator.queue_command("quantum", "coherence")
        
        # Execute all
        results = orchestrator.execute_all()
        
        # Verify
        assert len(results) == 3
        assert all(r.status == "completed" for r in results)
        assert orchestrator.system_status.commands_completed == 3
        
        # Check status
        status = orchestrator.get_status()
        assert status["commands_completed"] == 3
        assert status["commands_queued"] == 0
    
    def test_quantum_commands(self, orchestrator):
        """Test quantum-specific commands."""
        orchestrator.queue_command("quantum", "coherence")
        orchestrator.queue_command("quantum", "entanglement")
        
        results = orchestrator.execute_all()
        
        assert len(results) == 2
        assert all(r.status == "completed" for r in results)
        
        # Check that coherence is maintained
        status = orchestrator.get_status()
        assert status["coherence"] >= 0.99997
    
    def test_orchestration_commands(self, orchestrator):
        """Test orchestration commands."""
        # Note: These commands may not actually start/stop services in test mode
        # but they should still execute without errors
        orchestrator.queue_command("orchestration", "status")
        
        result = orchestrator.execute_next()
        
        assert result is not None
        assert result.status == "completed"


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])

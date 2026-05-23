#!/usr/bin/env python3
"""
J09 Bridge Module
===================
Cross-system bridging capabilities for J09 Junction Agent

Provides:
- Direct bridges between integrated systems
- Protocol-aware communication
- Error handling and retries
- Load balancing across connections
"""

import json
import logging
import time
import threading
import queue
from typing import Dict, List, Optional, Any, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum, auto
import requests
import websockets
import asyncio

logger = logging.getLogger(__name__)


# ============================================================================
# ENUMS & CONSTANTS
# ============================================================================

class BridgeStatus(Enum):
    """Status of a bridge connection"""
    IDLE = auto()
    CONNECTING = auto()
    CONNECTED = auto()
    DISCONNECTED = auto()
    ERROR = auto()


class BridgeProtocol(Enum):
    """Supported bridge protocols"""
    HTTP = auto()
    HTTPS = auto()
    WEBSOCKET = auto()
    GRPC = auto()
    MQTT = auto()


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class BridgeConfig:
    """Configuration for a bridge connection"""
    name: str
    protocol: BridgeProtocol
    endpoint: str
    api_key: Optional[str] = None
    timeout: float = 30.0
    retry_count: int = 3
    retry_delay: float = 1.0
    ssl_verify: bool = True
    headers: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "protocol": self.protocol.name,
            "endpoint": self.endpoint,
            "timeout": self.timeout,
            "retry_count": self.retry_count,
            "retry_delay": self.retry_delay,
            "ssl_verify": self.ssl_verify,
        }


@dataclass
class BridgeRequest:
    """Request to send over a bridge"""
    request_id: str
    method: str
    path: str
    data: Optional[Dict[str, Any]] = None
    headers: Optional[Dict[str, str]] = None
    timeout: float = 30.0
    retries: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "method": self.method,
            "path": self.path,
            "data": self.data,
            "headers": self.headers,
            "timeout": self.timeout,
            "retries": self.retries,
        }


@dataclass
class BridgeResponse:
    """Response from a bridge request"""
    request_id: str
    success: bool
    status_code: int
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    execution_time: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "success": self.success,
            "status_code": self.status_code,
            "data": self.data,
            "error": self.error,
            "execution_time": self.execution_time,
        }


# ============================================================================
# BRIDGE MANAGER
# ============================================================================

class BridgeManager:
    """
    Manages multiple bridge connections to external systems.
    
    Supports:
    - HTTP/HTTPS REST APIs
    - WebSocket connections
    - gRPC services (future)
    - MQTT brokers (future)
    """
    
    def __init__(self):
        self.bridges: Dict[str, Any] = {}
        self.configs: Dict[str, BridgeConfig] = {}
        self.request_queue = queue.Queue()
        self.worker_threads: List[threading.Thread] = []
        self.running = False
        self.lock = threading.Lock()
        
        logger.info("Bridge Manager initialized")
    
    def add_bridge(
        self,
        name: str,
        protocol: BridgeProtocol,
        endpoint: str,
        api_key: Optional[str] = None,
        **kwargs,
    ) -> None:
        """Add a new bridge configuration"""
        config = BridgeConfig(
            name=name,
            protocol=protocol,
            endpoint=endpoint,
            api_key=api_key,
            **kwargs,
        )
        
        with self.lock:
            self.configs[name] = config
        
        logger.info(f"Added bridge: {name} ({protocol.name})")
    
    def remove_bridge(self, name: str) -> bool:
        """Remove a bridge"""
        with self.lock:
            if name in self.configs:
                del self.configs[name]
                logger.info(f"Removed bridge: {name}")
                return True
        return False
    
    def get_bridge(self, name: str) -> Optional[BridgeConfig]:
        """Get a bridge configuration"""
        with self.lock:
            return self.configs.get(name)
    
    def list_bridges(self) -> List[str]:
        """List all bridge names"""
        with self.lock:
            return list(self.configs.keys())
    
    def send_http_request(
        self,
        bridge_name: str,
        method: str,
        path: str,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
    ) -> BridgeResponse:
        """Send an HTTP request over a bridge"""
        config = self.get_bridge(bridge_name)
        if not config:
            raise ValueError(f"Bridge {bridge_name} not found")
        
        if config.protocol not in [BridgeProtocol.HTTP, BridgeProtocol.HTTPS]:
            raise ValueError(f"Bridge {bridge_name} is not an HTTP bridge")
        
        # Build URL
        url = f"{'https' if config.protocol == BridgeProtocol.HTTPS else 'http'}://{config.endpoint}{path}"
        
        # Build headers
        request_headers = {
            "Content-Type": "application/json",
            "User-Agent": "J09-Junction-Agent/1.0",
        }
        
        if config.api_key:
            request_headers["Authorization"] = f"Bearer {config.api_key}"
        
        if headers:
            request_headers.update(headers)
        
        # Determine timeout
        request_timeout = timeout or config.timeout
        
        # Send request with retries
        start_time = time.time()
        last_error = None
        
        for attempt in range(config.retry_count + 1):
            try:
                if method.upper() == "GET":
                    response = requests.get(
                        url,
                        headers=request_headers,
                        timeout=request_timeout,
                        verify=config.ssl_verify,
                    )
                elif method.upper() == "POST":
                    response = requests.post(
                        url,
                        json=data,
                        headers=request_headers,
                        timeout=request_timeout,
                        verify=config.ssl_verify,
                    )
                elif method.upper() == "PUT":
                    response = requests.put(
                        url,
                        json=data,
                        headers=request_headers,
                        timeout=request_timeout,
                        verify=config.ssl_verify,
                    )
                elif method.upper() == "DELETE":
                    response = requests.delete(
                        url,
                        headers=request_headers,
                        timeout=request_timeout,
                        verify=config.ssl_verify,
                    )
                else:
                    raise ValueError(f"Unsupported method: {method}")
                
                execution_time = time.time() - start_time
                
                # Check for success
                if 200 <= response.status_code < 300:
                    try:
                        response_data = response.json()
                    except:
                        response_data = None
                    
                    return BridgeResponse(
                        request_id=f"http_{int(time.time())}",
                        success=True,
                        status_code=response.status_code,
                        data=response_data,
                        execution_time=execution_time,
                    )
                else:
                    last_error = f"HTTP {response.status_code}: {response.text}"
                    
            except requests.exceptions.RequestException as e:
                last_error = str(e)
                
            # Retry delay
            if attempt < config.retry_count:
                time.sleep(config.retry_delay)
        
        # All retries failed
        return BridgeResponse(
            request_id=f"http_{int(time.time())}",
            success=False,
            status_code=0,
            error=last_error,
            execution_time=time.time() - start_time,
        )
    
    async def send_websocket_request(
        self,
        bridge_name: str,
        message: Dict[str, Any],
        timeout: Optional[float] = None,
    ) -> BridgeResponse:
        """Send a WebSocket message over a bridge"""
        config = self.get_bridge(bridge_name)
        if not config:
            raise ValueError(f"Bridge {bridge_name} not found")
        
        if config.protocol != BridgeProtocol.WEBSOCKET:
            raise ValueError(f"Bridge {bridge_name} is not a WebSocket bridge")
        
        start_time = time.time()
        
        try:
            async with websockets.connect(
                f"ws://{config.endpoint}",
                extra_headers={"Authorization": f"Bearer {config.api_key}"} if config.api_key else None,
                ping_timeout=timeout or config.timeout,
            ) as websocket:
                # Send message
                await websocket.send(json.dumps(message))
                
                # Wait for response
                response = await asyncio.wait_for(
                    websocket.recv(),
                    timeout=timeout or config.timeout,
                )
                
                execution_time = time.time() - start_time
                
                try:
                    response_data = json.loads(response)
                except:
                    response_data = response
                
                return BridgeResponse(
                    request_id=f"ws_{int(time.time())}",
                    success=True,
                    status_code=200,
                    data=response_data,
                    execution_time=execution_time,
                )
                
        except asyncio.TimeoutError:
            return BridgeResponse(
                request_id=f"ws_{int(time.time())}",
                success=False,
                status_code=0,
                error="WebSocket timeout",
                execution_time=time.time() - start_time,
            )
        except Exception as e:
            return BridgeResponse(
                request_id=f"ws_{int(time.time())}",
                success=False,
                status_code=0,
                error=str(e),
                execution_time=time.time() - start_time,
            )
    
    def start_workers(self, num_workers: int = 5) -> None:
        """Start worker threads for async processing"""
        if self.running:
            return
        
        self.running = True
        
        for i in range(num_workers):
            thread = threading.Thread(
                target=self._worker,
                args=(i,),
                daemon=True,
            )
            thread.start()
            self.worker_threads.append(thread)
        
        logger.info(f"Started {num_workers} bridge workers")
    
    def stop_workers(self) -> None:
        """Stop all worker threads"""
        self.running = False
        for thread in self.worker_threads:
            thread.join(timeout=5)
        self.worker_threads.clear()
        logger.info("Stopped all bridge workers")
    
    def _worker(self, worker_id: int) -> None:
        """Worker thread for processing bridge requests"""
        logger.info(f"Bridge worker {worker_id} started")
        
        while self.running:
            try:
                # Get request from queue
                request = self.request_queue.get(timeout=1)
                
                # Process request
                config = self.get_bridge(request.request_id.split("_")[0])
                if config:
                    if config.protocol in [BridgeProtocol.HTTP, BridgeProtocol.HTTPS]:
                        # This would need to be async or in a thread pool
                        pass
                
                self.request_queue.task_done()
                
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Bridge worker {worker_id} error: {e}")
        
        logger.info(f"Bridge worker {worker_id} stopped")
    
    def enqueue_request(self, request: BridgeRequest) -> None:
        """Add a request to the processing queue"""
        self.request_queue.put(request)
        logger.info(f"Enqueued bridge request: {request.request_id}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get bridge manager status"""
        return {
            "bridges": {k: v.to_dict() for k, v in self.configs.items()},
            "queue_size": self.request_queue.qsize(),
            "worker_count": len(self.worker_threads),
            "running": self.running,
        }


# ============================================================================
# SPECIALIZED BRIDGES
# ============================================================================

class StripeBridge:
    """Specialized bridge for Stripe API"""
    
    def __init__(self, api_key: str, endpoint: str = "https://api.stripe.com/v1"):
        self.api_key = api_key
        self.endpoint = endpoint
        self.session = requests.Session()
        self.session.auth = (api_key, "")
        
        logger.info(f"StripeBridge initialized (endpoint: {endpoint})")
    
    def create_payment_intent(
        self,
        amount: int,
        currency: str = "usd",
        customer: Optional[str] = None,
        payment_method: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Create a Stripe PaymentIntent"""
        data = {
            "amount": amount,
            "currency": currency,
        }
        
        if customer:
            data["customer"] = customer
        if payment_method:
            data["payment_method"] = payment_method
        if metadata:
            data["metadata"] = metadata
        
        data.update(kwargs)
        
        response = self.session.post(
            f"{self.endpoint}/payment_intents",
            data=data,
        )
        
        response.raise_for_status()
        return response.json()
    
    def retrieve_payment_intent(self, intent_id: str) -> Dict[str, Any]:
        """Retrieve a PaymentIntent"""
        response = self.session.get(
            f"{self.endpoint}/payment_intents/{intent_id}",
        )
        response.raise_for_status()
        return response.json()
    
    def confirm_payment_intent(self, intent_id: str, **kwargs) -> Dict[str, Any]:
        """Confirm a PaymentIntent"""
        response = self.session.post(
            f"{self.endpoint}/payment_intents/{intent_id}/confirm",
            data=kwargs,
        )
        response.raise_for_status()
        return response.json()
    
    def create_customer(
        self,
        email: Optional[str] = None,
        name: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Create a Stripe Customer"""
        data = {}
        if email:
            data["email"] = email
        if name:
            data["name"] = name
        data.update(kwargs)
        
        response = self.session.post(
            f"{self.endpoint}/customers",
            data=data,
        )
        response.raise_for_status()
        return response.json()
    
    def list_customers(self, limit: int = 10, **kwargs) -> Dict[str, Any]:
        """List Stripe Customers"""
        params = {"limit": limit}
        params.update(kwargs)
        
        response = self.session.get(
            f"{self.endpoint}/customers",
            params=params,
        )
        response.raise_for_status()
        return response.json()
    
    def handle_webhook(self, payload: bytes, signature: str, secret: str) -> Dict[str, Any]:
        """Handle Stripe webhook"""
        import hmac
        import hashlib
        
        # Verify signature
        try:
            signed_payload = signature.split(",v1=")[1]
            expected_sig = hmac.new(
                secret.encode("utf-8"),
                payload,
                hashlib.sha256,
            ).hexdigest()
            
            if not hmac.compare_digest(signed_payload, expected_sig):
                raise ValueError("Invalid webhook signature")
        except Exception as e:
            logger.error(f"Webhook signature verification failed: {e}")
            raise
        
        # Parse payload
        try:
            event = json.loads(payload)
        except:
            raise ValueError("Invalid webhook payload")
        
        return event


class NFCEscrowBridge:
    """Specialized bridge for NFC Escrow Bridge"""
    
    def __init__(self, endpoint: str = "http://localhost:8000", api_key: Optional[str] = None):
        self.endpoint = endpoint
        self.api_key = api_key
        self.session = requests.Session()
        
        if api_key:
            self.session.headers.update({"X-API-Key": api_key})
        
        logger.info(f"NFCEscrowBridge initialized (endpoint: {endpoint})")
    
    def create_escrow(
        self,
        amount: int,
        currency: str = "usd",
        buyer: Optional[str] = None,
        seller: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Create an escrow transaction"""
        data = {
            "amount": amount,
            "currency": currency,
        }
        
        if buyer:
            data["buyer"] = buyer
        if seller:
            data["seller"] = seller
        data.update(kwargs)
        
        response = self.session.post(
            f"{self.endpoint}/escrow/create",
            json=data,
        )
        response.raise_for_status()
        return response.json()
    
    def release_escrow(self, escrow_id: str, **kwargs) -> Dict[str, Any]:
        """Release an escrow transaction"""
        response = self.session.post(
            f"{self.endpoint}/escrow/{escrow_id}/release",
            json=kwargs,
        )
        response.raise_for_status()
        return response.json()
    
    def read_nfc_tag(self, tag_id: str) -> Dict[str, Any]:
        """Read an NFC tag"""
        response = self.session.get(
            f"{self.endpoint}/nfc/read/{tag_id}",
        )
        response.raise_for_status()
        return response.json()
    
    def write_nfc_tag(self, tag_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Write to an NFC tag"""
        response = self.session.post(
            f"{self.endpoint}/nfc/write/{tag_id}",
            json=data,
        )
        response.raise_for_status()
        return response.json()


class OrchestratorBridge:
    """Specialized bridge for Autonomous Orchestrator"""
    
    def __init__(self, endpoint: str = "http://localhost:8081", api_key: Optional[str] = None):
        self.endpoint = endpoint
        self.api_key = api_key
        self.session = requests.Session()
        
        if api_key:
            self.session.headers.update({"X-API-Key": api_key})
        
        logger.info(f"OrchestratorBridge initialized (endpoint: {endpoint})")
    
    def execute_command(self, command: str, category: Optional[str] = None) -> Dict[str, Any]:
        """Execute an orchestrator command"""
        data = {"command": command}
        if category:
            data["category"] = category
        
        response = self.session.post(
            f"{self.endpoint}/execute",
            json=data,
        )
        response.raise_for_status()
        return response.json()
    
    def get_status(self) -> Dict[str, Any]:
        """Get orchestrator status"""
        response = self.session.get(
            f"{self.endpoint}/status",
        )
        response.raise_for_status()
        return response.json()
    
    def get_agents(self) -> Dict[str, Any]:
        """Get all agents"""
        response = self.session.get(
            f"{self.endpoint}/agents",
        )
        response.raise_for_status()
        return response.json()


# ============================================================================
# BRIDGE FACTORY
# ============================================================================

class BridgeFactory:
    """Factory for creating specialized bridges"""
    
    @staticmethod
    def create_bridge(bridge_type: str, **kwargs) -> Any:
        """Create a specialized bridge based on type"""
        bridge_classes = {
            "stripe": StripeBridge,
            "nfc_escrow": NFCEscrowBridge,
            "orchestrator": OrchestratorBridge,
        }
        
        bridge_class = bridge_classes.get(bridge_type)
        if not bridge_class:
            raise ValueError(f"Unknown bridge type: {bridge_type}")
        
        return bridge_class(**kwargs)


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    # Test Bridge Manager
    manager = BridgeManager()
    
    # Add bridges
    manager.add_bridge(
        name="stripe",
        protocol=BridgeProtocol.HTTPS,
        endpoint="api.stripe.com/v1",
    )
    
    manager.add_bridge(
        name="nfc_escrow",
        protocol=BridgeProtocol.HTTP,
        endpoint="localhost:8000",
    )
    
    manager.add_bridge(
        name="orchestrator",
        protocol=BridgeProtocol.HTTP,
        endpoint="localhost:8081",
    )
    
    # Test HTTP request
    print("\nTesting Bridge Manager...")
    print(f"Bridges: {manager.list_bridges()}")
    
    # Note: Actual requests would fail without proper setup
    # This is just to show the structure
    
    print("\nBridge Manager ready!")
    print("Use: manager.send_http_request('bridge_name', 'POST', '/path', data)")

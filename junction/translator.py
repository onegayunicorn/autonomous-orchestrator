#!/usr/bin/env python3
"""
J09 Translator Module
======================
Protocol translation engine for J09 Junction Agent

Provides:
- Cross-protocol data translation
- Format conversion (JSON, XML, Protocol Buffers, etc.)
- Data transformation pipelines
- Schema mapping
- Type coercion
"""

import json
import logging
import time
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Any, Callable, Type, Union
from dataclasses import dataclass, field
from enum import Enum, auto
from functools import lru_cache

logger = logging.getLogger(__name__)


# ============================================================================
# ENUMS & CONSTANTS
# ============================================================================

class DataFormat(Enum):
    """Supported data formats"""
    JSON = auto()
    XML = auto()
    PROTOBUF = auto()
    MSGPACK = auto()
    YAML = auto()
    CSV = auto()
    FORM = auto()
    CUSTOM = auto()


class TranslationType(Enum):
    """Types of translations"""
    DIRECT = auto()  # Direct field mapping
    TRANSFORM = auto()  # Custom transformation
    PIPELINE = auto()  # Multi-step pipeline
    CONDITIONAL = auto()  # Conditional translation


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class FieldMapping:
    """Mapping between fields in different formats"""
    source_field: str
    target_field: str
    transformer: Optional[Callable[[Any], Any]] = None
    default: Optional[Any] = None
    
    def apply(self, source_data: Dict[str, Any]) -> Tuple[str, Any]:
        """Apply this mapping to source data"""
        value = source_data.get(self.source_field, self.default)
        if self.transformer and value is not None:
            value = self.transformer(value)
        return self.target_field, value


@dataclass
class TranslationSchema:
    """Schema for translating between two formats"""
    name: str
    source_format: DataFormat
    target_format: DataFormat
    mappings: List[FieldMapping] = field(default_factory=list)
    type: TranslationType = TranslationType.DIRECT
    transformer: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None
    
    def apply(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply this schema to data"""
        if self.type == TranslationType.DIRECT:
            return self._apply_direct(data)
        elif self.type == TranslationType.TRANSFORM and self.transformer:
            return self.transformer(data)
        else:
            return data
    
    def _apply_direct(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply direct field mappings"""
        result = {}
        for mapping in self.mappings:
            target_field, value = mapping.apply(data)
            if value is not None:
                result[target_field] = value
        return result


@dataclass
class TranslationPipeline:
    """Pipeline of multiple translation steps"""
    name: str
    steps: List[TranslationSchema]
    
    def apply(self, data: Dict[str, Any], source_format: DataFormat) -> Dict[str, Any]:
        """Apply the pipeline to data"""
        current_data = data
        current_format = source_format
        
        for step in self.steps:
            if step.source_format == current_format:
                current_data = step.apply(current_data)
                current_format = step.target_format
        
        return current_data


# ============================================================================
# TRANSLATOR
# ============================================================================

class Translator:
    """
    Universal protocol translator for J09 Junction Agent
    
    Supports translation between multiple data formats and schemas.
    """
    
    def __init__(self):
        self.schemas: Dict[str, TranslationSchema] = {}
        self.pipelines: Dict[str, TranslationPipeline] = {}
        self.format_handlers: Dict[DataFormat, Any] = {}
        
        # Register format handlers
        self._register_format_handlers()
        
        # Initialize default schemas
        self._initialize_default_schemas()
        
        logger.info(f"Translator initialized with {len(self.schemas)} schemas")
    
    def _register_format_handlers(self):
        """Register handlers for different data formats"""
        # JSON handler (native)
        self.format_handlers[DataFormat.JSON] = {
            "parse": lambda data: json.loads(data) if isinstance(data, str) else data,
            "serialize": lambda data: json.dumps(data),
        }
        
        # XML handler
        def xml_to_dict(xml_string: str) -> Dict[str, Any]:
            """Convert XML string to dictionary"""
            root = ET.fromstring(xml_string)
            return self._xml_element_to_dict(root)
        
        def dict_to_xml(data: Dict[str, Any], root_tag: str = "root") -> str:
            """Convert dictionary to XML string"""
            root = ET.Element(root_tag)
            self._dict_to_xml_element(data, root)
            return ET.tostring(root, encoding="unicode")
        
        self.format_handlers[DataFormat.XML] = {
            "parse": xml_to_dict,
            "serialize": dict_to_xml,
        }
        
        # YAML handler
        try:
            import yaml
            self.format_handlers[DataFormat.YAML] = {
                "parse": yaml.safe_load,
                "serialize": yaml.dump,
            }
        except ImportError:
            logger.warning("PyYAML not installed. YAML support disabled.")
        
        # MessagePack handler
        try:
            import msgpack
            self.format_handlers[DataFormat.MSGPACK] = {
                "parse": msgpack.unpackb,
                "serialize": msgpack.packb,
            }
        except ImportError:
            logger.warning("msgpack not installed. MessagePack support disabled.")
    
    def _xml_element_to_dict(self, element: ET.Element) -> Dict[str, Any]:
        """Convert XML element to dictionary recursively"""
        result = {}
        
        # Handle attributes
        if element.attrib:
            result["@attributes"] = element.attrib
        
        # Handle child elements
        for child in element:
            child_data = self._xml_element_to_dict(child)
            
            if child.tag in result:
                # If tag already exists, convert to list
                if isinstance(result[child.tag], list):
                    result[child.tag].append(child_data)
                else:
                    result[child.tag] = [result[child.tag], child_data]
            else:
                result[child.tag] = child_data
        
        # Handle text content
        if element.text and element.text.strip():
            if result:
                result["#text"] = element.text.strip()
            else:
                result = element.text.strip()
        
        return result
    
    def _dict_to_xml_element(self, data: Dict[str, Any], parent: ET.Element):
        """Convert dictionary to XML element recursively"""
        if isinstance(data, dict):
            for key, value in data.items():
                if key == "@attributes":
                    parent.attrib.update(value)
                elif key == "#text":
                    parent.text = str(value)
                else:
                    child = ET.SubElement(parent, key)
                    self._dict_to_xml_element(value, child)
        elif isinstance(data, list):
            for item in data:
                child = ET.SubElement(parent, parent.tag)
                self._dict_to_xml_element(item, child)
        else:
            parent.text = str(data)
    
    def _initialize_default_schemas(self):
        """Initialize default translation schemas"""
        # Stripe PaymentIntent to Orchestrator Command
        stripe_to_orchestrator = TranslationSchema(
            name="stripe_to_orchestrator",
            source_format=DataFormat.JSON,
            target_format=DataFormat.JSON,
            type=TranslationType.DIRECT,
            mappings=[
                FieldMapping(
                    source_field="amount",
                    target_field="amount",
                    transformer=lambda x: x / 100 if isinstance(x, int) else x,  # Convert cents to dollars
                ),
                FieldMapping(
                    source_field="currency",
                    target_field="currency",
                ),
                FieldMapping(
                    source_field="status",
                    target_field="status",
                ),
                FieldMapping(
                    source_field="id",
                    target_field="payment_id",
                ),
                FieldMapping(
                    source_field="metadata",
                    target_field="metadata",
                ),
            ],
        )
        self.schemas["stripe_to_orchestrator"] = stripe_to_orchestrator
        
        # Orchestrator Command to Stripe PaymentIntent
        orchestrator_to_stripe = TranslationSchema(
            name="orchestrator_to_stripe",
            source_format=DataFormat.JSON,
            target_format=DataFormat.JSON,
            type=TranslationType.DIRECT,
            mappings=[
                FieldMapping(
                    source_field="amount",
                    target_field="amount",
                    transformer=lambda x: int(x * 100) if isinstance(x, (int, float)) else x,  # Convert dollars to cents
                ),
                FieldMapping(
                    source_field="currency",
                    target_field="currency",
                    default="usd",
                ),
                FieldMapping(
                    source_field="command",
                    target_field="description",
                ),
                FieldMapping(
                    source_field="category",
                    target_field="metadata.category",
                ),
            ],
        )
        self.schemas["orchestrator_to_stripe"] = orchestrator_to_stripe
        
        # NFC Tag Data to Escrow Transaction
        nfc_to_escrow = TranslationSchema(
            name="nfc_to_escrow",
            source_format=DataFormat.JSON,
            target_format=DataFormat.JSON,
            type=TranslationType.DIRECT,
            mappings=[
                FieldMapping(
                    source_field="tag_id",
                    target_field="reference_id",
                ),
                FieldMapping(
                    source_field="data.amount",
                    target_field="amount",
                ),
                FieldMapping(
                    source_field="data.currency",
                    target_field="currency",
                    default="usd",
                ),
                FieldMapping(
                    source_field="type",
                    target_field="type",
                    default="nfc_payment",
                ),
            ],
        )
        self.schemas["nfc_to_escrow"] = nfc_to_escrow
        
        # Escrow Transaction to Stripe PaymentIntent
        escrow_to_stripe = TranslationSchema(
            name="escrow_to_stripe",
            source_format=DataFormat.JSON,
            target_format=DataFormat.JSON,
            type=TranslationType.DIRECT,
            mappings=[
                FieldMapping(
                    source_field="amount",
                    target_field="amount",
                    transformer=lambda x: int(x * 100) if isinstance(x, (int, float)) else x,
                ),
                FieldMapping(
                    source_field="currency",
                    target_field="currency",
                ),
                FieldMapping(
                    source_field="reference_id",
                    target_field="metadata.escrow_id",
                ),
                FieldMapping(
                    source_field="type",
                    target_field="description",
                ),
            ],
        )
        self.schemas["escrow_to_stripe"] = escrow_to_stripe
        
        logger.info(f"Initialized {len(self.schemas)} default translation schemas")
    
    def add_schema(self, schema: TranslationSchema) -> None:
        """Add a new translation schema"""
        self.schemas[schema.name] = schema
        logger.info(f"Added translation schema: {schema.name}")
    
    def remove_schema(self, name: str) -> bool:
        """Remove a translation schema"""
        if name in self.schemas:
            del self.schemas[name]
            logger.info(f"Removed translation schema: {name}")
            return True
        return False
    
    def get_schema(self, name: str) -> Optional[TranslationSchema]:
        """Get a translation schema by name"""
        return self.schemas.get(name)
    
    def add_pipeline(self, pipeline: TranslationPipeline) -> None:
        """Add a new translation pipeline"""
        self.pipelines[pipeline.name] = pipeline
        logger.info(f"Added translation pipeline: {pipeline.name}")
    
    def translate(
        self,
        data: Any,
        source_format: DataFormat,
        target_format: DataFormat,
        schema_name: Optional[str] = None,
    ) -> Any:
        """
        Translate data from source format to target format
        
        Args:
            data: Data to translate
            source_format: Format of input data
            target_format: Desired output format
            schema_name: Optional schema name for structured translation
            
        Returns:
            Translated data in target format
        """
        # Parse input data if it's a string
        if isinstance(data, str):
            data = self._parse_data(data, source_format)
        
        # Apply schema if provided
        if schema_name and schema_name in self.schemas:
            schema = self.schemas[schema_name]
            
            # Check if schema matches our formats
            if (
                schema.source_format == source_format and
                schema.target_format == target_format
            ):
                data = schema.apply(data)
        
        # Serialize to target format
        return self._serialize_data(data, target_format)
    
    def _parse_data(self, data: str, data_format: DataFormat) -> Any:
        """Parse data string to Python object"""
        handler = self.format_handlers.get(data_format)
        if handler and "parse" in handler:
            try:
                return handler["parse"](data)
            except Exception as e:
                logger.error(f"Failed to parse {data_format.name} data: {e}")
                raise ValueError(f"Invalid {data_format.name} data: {e}")
        else:
            raise ValueError(f"Unsupported data format: {data_format.name}")
    
    def _serialize_data(self, data: Any, data_format: DataFormat) -> Any:
        """Serialize Python object to data format"""
        handler = self.format_handlers.get(data_format)
        if handler and "serialize" in handler:
            try:
                return handler["serialize"](data)
            except Exception as e:
                logger.error(f"Failed to serialize to {data_format.name}: {e}")
                raise ValueError(f"Serialization error: {e}")
        else:
            raise ValueError(f"Unsupported data format: {data_format.name}")
    
    def translate_json_to_xml(self, json_data: Dict[str, Any], root_tag: str = "root") -> str:
        """Translate JSON to XML"""
        return self.translate(
            data=json_data,
            source_format=DataFormat.JSON,
            target_format=DataFormat.XML,
        )
    
    def translate_xml_to_json(self, xml_data: str) -> Dict[str, Any]:
        """Translate XML to JSON"""
        return self.translate(
            data=xml_data,
            source_format=DataFormat.XML,
            target_format=DataFormat.JSON,
        )
    
    def translate_with_schema(
        self,
        data: Dict[str, Any],
        schema_name: str,
    ) -> Dict[str, Any]:
        """Translate data using a specific schema"""
        schema = self.get_schema(schema_name)
        if not schema:
            raise ValueError(f"Schema not found: {schema_name}")
        
        return schema.apply(data)
    
    def create_pipeline(
        self,
        name: str,
        steps: List[Dict[str, Any]],
    ) -> TranslationPipeline:
        """Create a new translation pipeline"""
        schema_steps = []
        for step_def in steps:
            schema = TranslationSchema(
                name=step_def.get("name", f"{name}_step_{len(schema_steps)}"),
                source_format=step_def.get("source_format"),
                target_format=step_def.get("target_format"),
                type=step_def.get("type", TranslationType.DIRECT),
                mappings=step_def.get("mappings", []),
            )
            schema_steps.append(schema)
        
        pipeline = TranslationPipeline(
            name=name,
            steps=schema_steps,
        )
        
        self.add_pipeline(pipeline)
        return pipeline
    
    def apply_pipeline(
        self,
        data: Any,
        pipeline_name: str,
        source_format: DataFormat,
    ) -> Any:
        """Apply a translation pipeline to data"""
        pipeline = self.pipelines.get(pipeline_name)
        if not pipeline:
            raise ValueError(f"Pipeline not found: {pipeline_name}")
        
        return pipeline.apply(data, source_format)
    
    def list_schemas(self) -> List[str]:
        """List all available schemas"""
        return list(self.schemas.keys())
    
    def list_pipelines(self) -> List[str]:
        """List all available pipelines"""
        return list(self.pipelines.keys())
    
    def list_formats(self) -> List[str]:
        """List all supported formats"""
        return [f.name for f in self.format_handlers.keys()]
    
    def get_status(self) -> Dict[str, Any]:
        """Get translator status"""
        return {
            "schemas": list(self.schemas.keys()),
            "pipelines": list(self.pipelines.keys()),
            "formats": self.list_formats(),
        }


# ============================================================================
# SPECIALIZED TRANSLATORS
# ============================================================================

class StripeTranslator:
    """Specialized translator for Stripe data"""
    
    def __init__(self):
        self.translator = Translator()
    
    def payment_intent_to_orchestrator(self, pi_data: Dict[str, Any]) -> Dict[str, Any]:
        """Translate Stripe PaymentIntent to Orchestrator command"""
        return self.translator.translate_with_schema(
            data=pi_data,
            schema_name="stripe_to_orchestrator",
        )
    
    def orchestrator_to_payment_intent(
        self,
        command_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Translate Orchestrator command to Stripe PaymentIntent"""
        return self.translator.translate_with_schema(
            data=command_data,
            schema_name="orchestrator_to_stripe",
        )
    
    def customer_to_user(self, customer_data: Dict[str, Any]) -> Dict[str, Any]:
        """Translate Stripe Customer to internal User format"""
        return {
            "user_id": customer_data.get("id"),
            "email": customer_data.get("email"),
            "name": customer_data.get("name"),
            "metadata": customer_data.get("metadata", {}),
            "created": customer_data.get("created"),
        }


class NFCTranslator:
    """Specialized translator for NFC data"""
    
    def __init__(self):
        self.translator = Translator()
    
    def tag_to_escrow(self, tag_data: Dict[str, Any]) -> Dict[str, Any]:
        """Translate NFC tag data to Escrow transaction"""
        return self.translator.translate_with_schema(
            data=tag_data,
            schema_name="nfc_to_escrow",
        )
    
    def escrow_to_tag(self, escrow_data: Dict[str, Any]) -> Dict[str, Any]:
        """Translate Escrow transaction to NFC tag data"""
        return {
            "tag_id": escrow_data.get("reference_id"),
            "data": {
                "escrow_id": escrow_data.get("id"),
                "amount": escrow_data.get("amount"),
                "currency": escrow_data.get("currency"),
                "status": escrow_data.get("status"),
            },
        }


class OrchestratorTranslator:
    """Specialized translator for Orchestrator data"""
    
    def __init__(self):
        self.translator = Translator()
    
    def command_to_stripe(self, command_data: Dict[str, Any]) -> Dict[str, Any]:
        """Translate Orchestrator command to Stripe format"""
        return self.translator.translate_with_schema(
            data=command_data,
            schema_name="orchestrator_to_stripe",
        )
    
    def status_to_metrics(self, status_data: Dict[str, Any]) -> Dict[str, Any]:
        """Translate Orchestrator status to Prometheus metrics"""
        return {
            "coherence": status_data.get("coherence", 0),
            "entanglement_pairs": status_data.get("entanglement_pairs", 0),
            "agents_active": status_data.get("agents_active", 0),
            "commands_queued": status_data.get("commands_queued", 0),
            "risk_score": status_data.get("risk_score", 0),
        }


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    # Test Translator
    translator = Translator()
    
    print("\n" + "=" * 60)
    print("J09 Translator Test")
    print("=" * 60)
    
    # Test JSON to XML
    json_data = {
        "payment": {
            "id": "pi_123",
            "amount": 1000,
            "currency": "usd",
        }
    }
    
    xml_data = translator.translate_json_to_xml(json_data)
    print("\nJSON to XML:")
    print(xml_data)
    
    # Test XML to JSON
    json_result = translator.translate_xml_to_json(xml_data)
    print("\nXML to JSON:")
    print(json.dumps(json_result, indent=2))
    
    # Test schema translation
    stripe_data = {
        "id": "pi_test_123",
        "amount": 1000,
        "currency": "usd",
        "status": "succeeded",
        "metadata": {"test": True},
    }
    
    orchestrator_data = translator.translate_with_schema(
        data=stripe_data,
        schema_name="stripe_to_orchestrator",
    )
    print("\nStripe to Orchestrator:")
    print(json.dumps(orchestrator_data, indent=2))
    
    # Test specialized translators
    stripe_translator = StripeTranslator()
    result = stripe_translator.payment_intent_to_orchestrator(stripe_data)
    print("\nStripe Translator:")
    print(json.dumps(result, indent=2))
    
    # Print status
    print("\nTranslator Status:")
    print(json.dumps(translator.get_status(), indent=2))
    
    print("\n" + "=" * 60)
    print("Translator test complete!")
    print("=" * 60)

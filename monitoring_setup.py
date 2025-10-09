"""
Monitoring and Observability Setup for Enhanced Guardrails Service

This module provides comprehensive monitoring, logging, and observability features
including Prometheus metrics, structured logging, and health checks.
"""

import time
import logging
import asyncio
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
import json
import psutil
import structlog
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from prometheus_client.core import CollectorRegistry
import redis
import aioredis

# Custom metrics for guardrails service
class GuardrailsMetrics:
    """Custom metrics collector for guardrails service."""
    
    def __init__(self):
        self.registry = CollectorRegistry()
        self._setup_metrics()
    
    def _setup_metrics(self):
        """Setup all custom metrics."""
        # Request metrics
        self.requests_total = Counter(
            'guardrails_requests_total',
            'Total number of requests',
            ['method', 'endpoint', 'status_code', 'guardrail_name'],
            registry=self.registry
        )
        
        self.request_duration = Histogram(
            'guardrails_request_duration_seconds',
            'Request duration in seconds',
            ['method', 'endpoint', 'guardrail_name'],
            buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0],
            registry=self.registry
        )
        
        # Validation metrics
        self.validations_total = Counter(
            'guardrails_validations_total',
            'Total number of validations',
            ['validator_name', 'status', 'guardrail_name'],
            registry=self.registry
        )
        
        self.validation_duration = Histogram(
            'guardrails_validation_duration_seconds',
            'Validation duration in seconds',
            ['validator_name', 'model_name'],
            buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.5, 5.0],
            registry=self.registry
        )
        
        # Model metrics
        self.model_inference_duration = Histogram(
            'guardrails_model_inference_seconds',
            'Model inference duration in seconds',
            ['model_name', 'model_type', 'validator_name'],
            buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.5, 5.0, 10.0],
            registry=self.registry
        )
        
        self.model_load_duration = Histogram(
            'guardrails_model_load_seconds',
            'Model loading duration in seconds',
            ['model_name', 'model_type'],
            buckets=[1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0],
            registry=self.registry
        )
        
        # Cache metrics
        self.cache_operations = Counter(
            'guardrails_cache_operations_total',
            'Total cache operations',
            ['operation', 'result'],
            registry=self.registry
        )
        
        self.cache_hit_ratio = Gauge(
            'guardrails_cache_hit_ratio',
            'Cache hit ratio',
            registry=self.registry
        )
        
        # System metrics
        self.active_connections = Gauge(
            'guardrails_active_connections',
            'Number of active connections',
            registry=self.registry
        )
        
        self.memory_usage = Gauge(
            'guardrails_memory_usage_bytes',
            'Memory usage in bytes',
            ['type'],
            registry=self.registry
        )
        
        self.cpu_usage = Gauge(
            'guardrails_cpu_usage_percent',
            'CPU usage percentage',
            registry=self.registry
        )
        
        # Business metrics
        self.texts_processed = Counter(
            'guardrails_texts_processed_total',
            'Total texts processed',
            ['guardrail_name', 'result'],
            registry=self.registry
        )
        
        self.toxicity_detected = Counter(
            'guardrails_toxicity_detected_total',
            'Total toxicity detections',
            ['confidence_level'],
            registry=self.registry
        )
        
        self.pii_detected = Counter(
            'guardrails_pii_detected_total',
            'Total PII detections',
            ['entity_type'],
            registry=self.registry
        )
    
    def record_request(self, method: str, endpoint: str, status_code: int, 
                      guardrail_name: str, duration: float):
        """Record request metrics."""
        self.requests_total.labels(
            method=method,
            endpoint=endpoint,
            status_code=status_code,
            guardrail_name=guardrail_name
        ).inc()
        
        self.request_duration.labels(
            method=method,
            endpoint=endpoint,
            guardrail_name=guardrail_name
        ).observe(duration)
    
    def record_validation(self, validator_name: str, status: str, 
                         guardrail_name: str, duration: float):
        """Record validation metrics."""
        self.validations_total.labels(
            validator_name=validator_name,
            status=status,
            guardrail_name=guardrail_name
        ).inc()
        
        self.validation_duration.labels(
            validator_name=validator_name,
            model_name="unknown"
        ).observe(duration)
    
    def record_model_inference(self, model_name: str, model_type: str, 
                              validator_name: str, duration: float):
        """Record model inference metrics."""
        self.model_inference_duration.labels(
            model_name=model_name,
            model_type=model_type,
            validator_name=validator_name
        ).observe(duration)
    
    def record_model_load(self, model_name: str, model_type: str, duration: float):
        """Record model loading metrics."""
        self.model_load_duration.labels(
            model_name=model_name,
            model_type=model_type
        ).observe(duration)
    
    def record_cache_operation(self, operation: str, result: str):
        """Record cache operation metrics."""
        self.cache_operations.labels(
            operation=operation,
            result=result
        ).inc()
    
    def update_cache_hit_ratio(self, hits: int, misses: int):
        """Update cache hit ratio."""
        total = hits + misses
        if total > 0:
            ratio = hits / total
            self.cache_hit_ratio.set(ratio)
    
    def update_system_metrics(self):
        """Update system metrics."""
        process = psutil.Process()
        memory_info = process.memory_info()
        
        self.memory_usage.labels(type='rss').set(memory_info.rss)
        self.memory_usage.labels(type='vms').set(memory_info.vms)
        self.cpu_usage.set(process.cpu_percent())
    
    def record_business_metric(self, metric_name: str, labels: Dict[str, str], value: float = 1.0):
        """Record business-specific metrics."""
        if metric_name == "texts_processed":
            self.texts_processed.labels(**labels).inc(value)
        elif metric_name == "toxicity_detected":
            self.toxicity_detected.labels(**labels).inc(value)
        elif metric_name == "pii_detected":
            self.pii_detected.labels(**labels).inc(value)

# Global metrics instance
metrics = GuardrailsMetrics()

# Structured logging setup
def setup_structured_logging():
    """Setup structured logging with JSON output."""
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

# Health check system
@dataclass
class HealthStatus:
    """Health status information."""
    status: str
    timestamp: datetime
    uptime_seconds: float
    memory_usage: Dict[str, float]
    cpu_usage: float
    models_loaded: Dict[str, bool]
    cache_status: Dict[str, Any]
    active_connections: int
    errors: List[str]

class HealthChecker:
    """Comprehensive health checking system."""
    
    def __init__(self, redis_client: Optional[aioredis.Redis] = None):
        self.redis_client = redis_client
        self.start_time = time.time()
        self.errors = []
    
    async def check_health(self) -> HealthStatus:
        """Perform comprehensive health check."""
        self.errors = []
        
        # Basic system health
        uptime = time.time() - self.start_time
        
        # Memory and CPU usage
        process = psutil.Process()
        memory_info = process.memory_info()
        memory_usage = {
            "rss_mb": memory_info.rss / 1024 / 1024,
            "vms_mb": memory_info.vms / 1024 / 1024,
            "percent": process.memory_percent()
        }
        cpu_usage = process.cpu_percent()
        
        # Check memory usage
        if memory_usage["percent"] > 90:
            self.errors.append("High memory usage detected")
        
        if cpu_usage > 90:
            self.errors.append("High CPU usage detected")
        
        # Check models (this would be implemented based on your model manager)
        models_loaded = {
            "spacy": True,  # This would check actual model status
            "stanza": True,
            "toxicity": True,
            "sentiment": True
        }
        
        # Check cache status
        cache_status = await self._check_cache()
        
        # Determine overall status
        status = "healthy"
        if self.errors:
            status = "degraded" if len(self.errors) < 3 else "unhealthy"
        
        return HealthStatus(
            status=status,
            timestamp=datetime.utcnow(),
            uptime_seconds=uptime,
            memory_usage=memory_usage,
            cpu_usage=cpu_usage,
            models_loaded=models_loaded,
            cache_status=cache_status,
            active_connections=0,  # This would be tracked by the app
            errors=self.errors
        )
    
    async def _check_cache(self) -> Dict[str, Any]:
        """Check cache system health."""
        if not self.redis_client:
            return {"status": "not_configured"}
        
        try:
            await self.redis_client.ping()
            info = await self.redis_client.info()
            return {
                "status": "healthy",
                "connected_clients": info.get("connected_clients", 0),
                "used_memory": info.get("used_memory", 0),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0)
            }
        except Exception as e:
            self.errors.append(f"Cache connection failed: {str(e)}")
            return {"status": "unhealthy", "error": str(e)}

# Performance monitoring
class PerformanceMonitor:
    """Performance monitoring and alerting."""
    
    def __init__(self, metrics: GuardrailsMetrics):
        self.metrics = metrics
        self.alert_thresholds = {
            "response_time_p95": 5.0,  # seconds
            "error_rate": 0.05,  # 5%
            "memory_usage": 0.9,  # 90%
            "cpu_usage": 0.9,  # 90%
            "cache_hit_ratio": 0.7  # 70%
        }
        self.alerts = []
    
    def check_performance(self, current_metrics: Dict[str, float]) -> List[str]:
        """Check performance against thresholds."""
        alerts = []
        
        for metric, threshold in self.alert_thresholds.items():
            if metric in current_metrics:
                if current_metrics[metric] > threshold:
                    alerts.append(f"{metric} exceeded threshold: {current_metrics[metric]:.3f} > {threshold}")
        
        return alerts
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary."""
        return {
            "alerts": self.alerts,
            "thresholds": self.alert_thresholds,
            "timestamp": datetime.utcnow().isoformat()
        }

# Distributed tracing (simplified implementation)
class TraceContext:
    """Simple trace context for request tracking."""
    
    def __init__(self, trace_id: str, span_id: str, parent_id: Optional[str] = None):
        self.trace_id = trace_id
        self.span_id = span_id
        self.parent_id = parent_id
        self.start_time = time.time()
        self.tags = {}
        self.logs = []
    
    def add_tag(self, key: str, value: str):
        """Add a tag to the span."""
        self.tags[key] = value
    
    def add_log(self, message: str, level: str = "info"):
        """Add a log entry to the span."""
        self.logs.append({
            "timestamp": time.time(),
            "level": level,
            "message": message
        })
    
    def finish(self) -> Dict[str, Any]:
        """Finish the span and return trace data."""
        duration = time.time() - self.start_time
        return {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_id": self.parent_id,
            "duration_ms": duration * 1000,
            "tags": self.tags,
            "logs": self.logs,
            "start_time": self.start_time,
            "end_time": time.time()
        }

def create_trace_context(request_id: str) -> TraceContext:
    """Create a new trace context."""
    import uuid
    trace_id = str(uuid.uuid4())
    span_id = str(uuid.uuid4())
    return TraceContext(trace_id, span_id)

# Metrics collection task
async def collect_metrics_periodically(metrics: GuardrailsMetrics, interval: int = 60):
    """Periodically collect and update metrics."""
    while True:
        try:
            metrics.update_system_metrics()
            await asyncio.sleep(interval)
        except Exception as e:
            logging.error(f"Error collecting metrics: {e}")
            await asyncio.sleep(interval)

# Export functions for use in the main application
def get_metrics_registry():
    """Get the Prometheus metrics registry."""
    return metrics.registry

def get_metrics_instance():
    """Get the metrics instance."""
    return metrics

def setup_monitoring():
    """Setup all monitoring components."""
    setup_structured_logging()
    return metrics, HealthChecker()

# Example usage in FastAPI app
def add_monitoring_middleware(app):
    """Add monitoring middleware to FastAPI app."""
    
    @app.middleware("http")
    async def monitoring_middleware(request, call_next):
        start_time = time.time()
        
        # Create trace context
        trace_context = create_trace_context(f"req_{int(start_time * 1000)}")
        trace_context.add_tag("method", request.method)
        trace_context.add_tag("url", str(request.url))
        
        try:
            response = await call_next(request)
            
            # Record metrics
            duration = time.time() - start_time
            metrics.record_request(
                method=request.method,
                endpoint=request.url.path,
                status_code=response.status_code,
                guardrail_name="unknown",  # This would be extracted from request
                duration=duration
            )
            
            # Add trace headers
            response.headers["X-Trace-ID"] = trace_context.trace_id
            response.headers["X-Request-ID"] = trace_context.span_id
            
            return response
            
        except Exception as e:
            trace_context.add_log(f"Request failed: {str(e)}", "error")
            raise
        finally:
            # Finish trace
            trace_data = trace_context.finish()
            # In a real implementation, you would send this to a tracing system
            logging.info("Trace completed", **trace_data)

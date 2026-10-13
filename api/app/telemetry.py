import logging
from azure.monitor.opentelemetry import configure_azure_monitor
from .config import settings

def setup_telemetry() -> None:
    """Initialize Azure Monitor OpenTelemetry."""
    if not settings.applicationinsights_enabled and settings.applicationinsights_connection_string:
        return
    if not settings.applicationinsights_connection_string:
        logging.warning("Application Insights enabled but no connection string provided")
        return
    if settings.applicationinsights_enabled and settings.applicationinsights_connection_string:
        configure_azure_monitor(
            connection_string=settings.applicationinsights_connection_string.get_secret_value(),
            logger_name="fastapi-crud-ha",  # custom logger name to avoid duplicates
            disable_offline_storage=True,   # optional: prevents local file storage issues in containers
        )

    # Reduce noise: disable uvicorn access logs from being duplicated
    logging.getLogger("uvicorn.access").propagate = False
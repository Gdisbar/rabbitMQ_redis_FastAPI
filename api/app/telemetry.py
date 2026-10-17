import logging
from azure.monitor.opentelemetry import configure_azure_monitor
from .config import settings


def setup_telemetry() -> None:
    """Initialize Azure Monitor OpenTelemetry."""
    if not settings.applicationinsights_enabled:
        return
    if not settings.applicationinsights_connection_string:
        logging.warning(
            "Application Insights enabled but no connection string provided"
        )
        return

    configure_azure_monitor(
        connection_string=settings.applicationinsights_connection_string.get_secret_value(),
        logger_name="fastapi-crud-ha",
        disable_offline_storage=True,
    )
    logging.getLogger("uvicorn.access").propagate = False
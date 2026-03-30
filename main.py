from infrastructure.runtime_warnings import apply_runtime_warning_filters
from interface.api.entrypoint import get_app
from infrastructure.config.logging import LOGGING_CONFIG

apply_runtime_warning_filters()

app = get_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        log_config=LOGGING_CONFIG,
        reload=True,
    )

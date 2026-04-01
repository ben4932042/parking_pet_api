import warnings


def apply_runtime_warning_filters() -> None:
    warnings.filterwarnings(
        "ignore",
        message="'_UnionGenericAlias' is deprecated and slated for removal in Python 3.17",
        category=DeprecationWarning,
        module=r"google\.genai\.types",
    )
    warnings.filterwarnings(
        "ignore",
        message="Core Pydantic V1 functionality isn't compatible with Python 3.14 or greater.",
        category=UserWarning,
        module=r"langchain_core\._api\.deprecation",
    )
    warnings.filterwarnings(
        "ignore",
        message="This feature is deprecated as of June 24, 2025 and will be removed on June 24, 2026.*",
        category=UserWarning,
        module=r"vertexai\.generative_models\._generative_models",
    )
    warnings.filterwarnings(
        "ignore",
        message="This feature is deprecated as of June 24, 2025 and will be removed on June 24, 2026.*",
        category=UserWarning,
        module=r"vertexai\._model_garden\._model_garden_models",
    )
    warnings.filterwarnings(
        "ignore",
        category=DeprecationWarning,
        module=r"langchain_google_vertexai",
    )


apply_runtime_warning_filters()

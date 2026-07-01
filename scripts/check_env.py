"""Environment variables checks validation script."""

import os
import sys

# Append project root directory to path for app imports resolution
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.configs.settings import get_settings


def check_env_variables() -> None:
    """Audits environment configuration variables parameters.

    Exits with code 0 on success, or code 1 on verification failures.
    """
    print("Auditing environment configurations variables parameters...")
    try:
        settings = get_settings()
        
        print("\nParsed Configurations:")
        print(f"  MODEL_NAME:           {settings.model_name}")
        print(f"  EMBEDDING_MODEL:      {settings.embedding_model}")
        print(f"  TOP_K:                {settings.top_k}")
        print(f"  SIMILARITY_THRESHOLD: {settings.similarity_threshold}")
        print(f"  API_TIMEOUT:          {settings.api_timeout}")
        print(f"  LOG_LEVEL:            {settings.log_level}")
        print(f"  CATALOG_PATH:         {settings.catalog_path}")
        print(f"  VECTOR_DB_PATH:       {settings.vector_db_path}")

        # Check OpenAI key presence warning
        if not settings.openai_api_key:
            print("\nWARNING: 'OPENAI_API_KEY' variable is not set in environment.")
        else:
            masked_key = f"{settings.openai_api_key[:8]}...{settings.openai_api_key[-4:]}" if len(settings.openai_api_key) > 12 else "***"
            print(f"  OPENAI_API_KEY:       Parsed ({masked_key})")

        print("\nVerification checks completed successfully.")
        sys.exit(0)
    except Exception as e:
        print(f"\nERROR: Environment variables configuration validation checks failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    check_env_variables()

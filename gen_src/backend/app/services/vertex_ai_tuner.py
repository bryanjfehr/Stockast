import os
import tempfile
import logging
from typing import Dict, Any, Optional, Type

import pandas as pd
from fastapi import HTTPException, status

# Attempt to import Google Cloud libraries. Handle ImportError if not installed.
try:
    from google.cloud import aiplatform
    from google.api_core import exceptions as google_exceptions
except ImportError:
    # Create dummy classes if google-cloud-aiplatform is not installed.
    # This allows the application to start but will fail at runtime if these services are called.
    class DummyAiplatform:
        def init(self, *args, **kwargs):
            raise ImportError("google-cloud-aiplatform is not installed. Please install it to use Vertex AI features.")
        def HyperparameterTuningJob(self, *args, **kwargs):
            raise ImportError("google-cloud-aiplatform is not installed. Please install it to use Vertex AI features.")
        def Model(self, *args, **kwargs):
            raise ImportError("google-cloud-aiplatform is not installed. Please install it to use Vertex AI features.")
        class hyperparameter_tuning:
            class DoubleParameterSpec:
                def __init__(self, *args, **kwargs): pass
            class IntegerParameterSpec:
                def __init__(self, *args, **kwargs): pass

    aiplatform = DummyAiplatform()
    google_exceptions = None # type: ignore

# Since dependency context is not available, we assume the structure of these modules.
# In a real project, these would be imported from other files.
from app.core.config import settings
from app.models.user import User

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_vertex_ai_client(api_key_content: str) -> Type[aiplatform]:
    """
    Initializes the Vertex AI client using a user's API key content.

    This function securely handles the API key by writing it to a temporary
    file and setting the GOOGLE_APPLICATION_CREDENTIALS environment variable
    for the scope of the operation.

    Args:
        api_key_content: The JSON content of the Google Cloud service account key.

    Returns:
        The initialized google.cloud.aiplatform module.

    Raises:
        HTTPException: If project ID or location are not configured.
    """
    temp_key_file_path = None
    original_creds = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")

    if not settings.VERTEX_AI_PROJECT_ID or not settings.VERTEX_AI_LOCATION:
        logger.error("Vertex AI project ID or location is not configured in settings.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Vertex AI service is not configured on the server."
        )

    try:
        if api_key_content:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.json', mode='w', encoding='utf-8') as temp_file:
                temp_key_file_path = temp_file.name
                temp_file.write(api_key_content)
            
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = temp_key_file_path
            logger.info("Using temporary credentials file for Vertex AI authentication.")

        aiplatform.init(
            project=settings.VERTEX_AI_PROJECT_ID,
            location=settings.VERTEX_AI_LOCATION,
        )
        logger.info(f"Vertex AI initialized for project '{settings.VERTEX_AI_PROJECT_ID}' in location '{settings.VERTEX_AI_LOCATION}'.")
        
        return aiplatform

    finally:
        if temp_key_file_path:
            try:
                os.remove(temp_key_file_path)
                logger.info("Temporary credentials file removed.")
            except OSError as e:
                logger.error(f"Error removing temporary credentials file {temp_key_file_path}: {e}")

        if "GOOGLE_APPLICATION_CREDENTIALS" in os.environ:
            if original_creds:
                os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = original_creds
            else:
                del os.environ["GOOGLE_APPLICATION_CREDENTIALS"]
            logger.info("GOOGLE_APPLICATION_CREDENTIALS environment variable restored.")


def tune_signal_parameters(historical_data: pd.DataFrame, user: User) -> Dict[str, Any]:
    """
    Uses Vertex AI hyperparameter tuning to find optimal parameters for a signal generator.

    NOTE: This is a placeholder implementation. The actual parameter spec, metric,
    and training container must be configured based on the specific model.

    Args:
        historical_data: A DataFrame containing historical stock data.
        user: The user object containing the Vertex AI API key.

    Returns:
        A dictionary of the optimal parameters found by the tuning job.

    Raises:
        HTTPException: If the user's API key is missing or if the tuning job fails.
    """
    if not user.vertex_ai_api_key:
        logger.error("Attempted to tune parameters without a Vertex AI API key.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vertex AI API key is required for hyperparameter tuning."
        )

    try:
        client = get_vertex_ai_client(user.vertex_ai_api_key)

        logger.info("Preparing data for Vertex AI tuning job (placeholder). In a real implementation, data would be uploaded to GCS.")

        worker_pool_specs = [
            {
                "machine_spec": {"machine_type": "n1-standard-4"},
                "replica_count": 1,
                "container_spec": {
                    "image_uri": settings.VERTEX_AI_TRAINING_CONTAINER_URI,
                    "args": ["--data-format=csv", f"--data-uri=gs://your-bucket/data.csv"],
                },
            }
        ]

        parameter_spec = {
            "learning_rate": client.hyperparameter_tuning.DoubleParameterSpec(min=0.001, max=0.1, scale="log"),
            "lookback_period": client.hyperparameter_tuning.IntegerParameterSpec(min=10, max=50, scale="linear"),
        }

        metric_spec = {"sharpe_ratio": "maximize"}

        tuning_job = client.HyperparameterTuningJob(
            display_name="stockast-signal-tuning",
            custom_job_spec=worker_pool_specs,
            metric_spec=metric_spec,
            parameter_spec=parameter_spec,
            max_trial_count=10,
            parallel_trial_count=2,
            search_algorithm=None,  # Defaults to Bayesian optimization
        )

        logger.info("Starting Vertex AI HyperparameterTuningJob.")
        tuning_job.run(sync=True)

        if not tuning_job.best_trial:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not determine optimal parameters.")
            
        logger.info(f"Hyperparameter tuning job completed. Best trial: {tuning_job.best_trial.id}")
        optimal_parameters = {param.parameter_id: param.value for param in tuning_job.best_trial.parameters}
        
        return optimal_parameters

    except (google_exceptions.PermissionDenied, google_exceptions.Unauthenticated) as e:
        logger.error(f"Vertex AI Authentication/Permission Error: {e}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid or expired Vertex AI credentials.")
    except google_exceptions.GoogleAPICallError as e:
        logger.error(f"Vertex AI API call failed: {e}")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"Vertex AI service error: {e}")
    except Exception as e:
        logger.error(f"An unexpected error occurred during parameter tuning: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


def get_ai_generated_forecast(historical_data: pd.DataFrame, user: User) -> Dict[str, Any]:
    """
    Uses a deployed Vertex AI model to generate a stock price forecast.

    Args:
        historical_data: A DataFrame of recent stock data for prediction input.
        user: The user object containing the Vertex AI API key.

    Returns:
        A dictionary containing the forecast data.

    Raises:
        HTTPException: If the API key is missing, the model is not found, or prediction fails.
    """
    if not user.vertex_ai_api_key:
        logger.error("Attempted to get forecast without a Vertex AI API key.")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Vertex AI API key is required for forecasting.")
    
    if not settings.VERTEX_AI_FORECASTING_MODEL_ID:
        logger.error("Vertex AI forecasting model ID is not configured.")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="AI forecasting service is not configured.")

    try:
        client = get_vertex_ai_client(user.vertex_ai_api_key)

        model = client.Model(model_name=settings.VERTEX_AI_FORECASTING_MODEL_ID)
        
        instances = historical_data.to_dict(orient="records")
        
        logger.info(f"Sending {len(instances)} instances to model '{settings.VERTEX_AI_FORECASTING_MODEL_ID}' for prediction.")
        
        prediction_result = model.predict(instances=instances)
        
        forecast = prediction_result.predictions
        
        logger.info("Successfully received forecast from Vertex AI.")
        
        return {"forecast": forecast}

    except google_exceptions.NotFound:
        logger.error(f"Vertex AI model not found: {settings.VERTEX_AI_FORECASTING_MODEL_ID}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="The specified AI forecasting model could not be found.")
    except (google_exceptions.PermissionDenied, google_exceptions.Unauthenticated) as e:
        logger.error(f"Vertex AI Authentication/Permission Error: {e}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid or expired Vertex AI credentials.")
    except google_exceptions.GoogleAPICallError as e:
        logger.error(f"Vertex AI prediction API call failed: {e}")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"Vertex AI service error: {e}")
    except Exception as e:
        logger.error(f"An unexpected error occurred during AI forecasting: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

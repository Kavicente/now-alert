import joblib
import os
import logging

logger = logging.getLogger(__name__)


  
    
# Load road accident model
road_accident_predictor = None
try:
    road_accident_predictor = joblib.load(os.path.join(os.path.dirname(__file__), 'training', 'Road Models', 'road_predictor_svm.pkl'))
    logger.info("road_accident_predictor_lr.pkl loaded successfully.")
except FileNotFoundError:
    logger.error("road_accident_predictor_lr.pkl not found.")
except Exception as e:
    logger.error(f"Error loading road_accident_predictor_lr.pkl: {e}")
    
    
fire_accident_predictor = None
try:
    fire_accident_predictor = joblib.load(os.path.join(os.path.dirname(__file__), 'training', 'Fire Models', 'fire_predictor_svm.pkl'))
    logger.info("fire_predictor_lr.pkl loaded successfully.")
except FileNotFoundError:
    logger.error("fire_predictor_lr.pkl not found.")
except Exception as e:
    logger.error(f"Error loading fire_predictor_lr.pkl: {e}")

crime_predictor = None
try:
    crime_predictor = joblib.load(os.path.join(os.path.dirname(__file__), 'training', 'Crime Models', 'crime_predictor_lr.pkl'))
    logger.info("crime_predictor_lr.pkl loaded successfully.")
except FileNotFoundError:
    logger.error("crime_predictor_lr.pkl not found.")
except Exception as e:
    logger.error(f"Error loading crime_predictor_lr.pkl: {e}")


health_predictor = None
try:
    health_predictor = joblib.load(os.path.join(os.path.dirname(__file__), 'training', 'Health Models', 'health_predictor_svm.pkl'))
    logger.info("health_predictor_lr.pkl loaded successfully.")
except FileNotFoundError:
    logger.error("health_predictor_lr.pkl not found.")
except Exception as e:
    logger.error(f"Error loading health_predictor_lr.pkl: {e}")


birth_predictor = None
try:
    birth_predictor = joblib.load(os.path.join(os.path.dirname(__file__), 'training', 'Birth Models', 'birth_predictor_lr.pkl'))
    logger.info("birth_predictor_lr.pkl loaded successfully.")
except FileNotFoundError:
    logger.error("birth_predictor_lr.pkl not found.")
except Exception as e:
    logger.error(f"Error loading birth_predictor_lr.pkl: {e}")
import joblib
import os
import logging
import pandas as pd

logger = logging.getLogger(__name__)

road_accident_df = pd.DataFrame()

csv_path = os.path.join(os.path.dirname(__file__), 'dataset', 'road_accident.csv')

try:
    # Try modern way first (pandas ≥1.3.0)
    road_accident_df = pd.read_csv(csv_path, encoding='utf-8', errors='replace')
    logger.info("Successfully loaded road_accident.csv with utf-8 + errors=replace")
except TypeError:  # Means 'errors' parameter not supported
    # Old pandas version — fall back to safe encodings
    for encoding in ['utf-8', 'windows-1252', 'latin1', 'iso-8859-1']:
        try:
            road_accident_df = pd.read_csv(csv_path, encoding=encoding)
            logger.info(f"Successfully loaded road_accident.csv with encoding: {encoding}")
            break
        except Exception as e:
            continue
    else:
        logger.error("Failed to load road_accident.csv with any encoding")
        road_accident_df = pd.DataFrame()  # empty fallback
except FileNotFoundError:
    logger.error("road_accident.csv not found in dataset directory")
    road_accident_df = pd.DataFrame()
except Exception as e:
    logger.error(f"Unexpected error loading road_accident.csv: {e}")
    road_accident_df = pd.DataFrame()
    
fire_incident_df = pd.DataFrame()
try:
    fire_incident_df = pd.read_csv(os.path.join(os.path.dirname(__file__), 'dataset', 'fire_incidents.csv'))
    logger.info("Successfully loaded fire_incident.csv")
except FileNotFoundError:
    logger.error("fire_incident.csv not found in dataset directory")
except Exception as e:
    logger.error(f"Error loading fire_incident.csv: {e}")
    
health_emergencies_df = pd.DataFrame()
try:
    health_emergencies_df = pd.read_csv(os.path.join(os.path.dirname(__file__), 'dataset', 'health_emergencies.csv'))
    logger.info("Successfully loaded fire_incident.csv")
except FileNotFoundError:
    logger.error("fire_incident.csv not found in dataset directory")
except Exception as e:
    logger.error(f"Error loading fire_incident.csv: {e}")
    
crime_df = pd.DataFrame()
try:
    health_emergencies_df = pd.read_csv(os.path.join(os.path.dirname(__file__), 'dataset', 'crime_emergencies.csv'))
    logger.info("Successfully loaded crime_emergencies.csv")
except FileNotFoundError:
    logger.error("crime_emergencies.csv not found in dataset directory")
except Exception as e:
    logger.error(f"Error loading crime_emergencies.csv: {e}")
import joblib
import os
import logging

logger = logging.getLogger(__name__)

f_arima_m = None
try:
    f_arima_m = joblib.load(os.path.join(os.path.dirname(__file__), 'training', 'Fire Models', 'ARIMA FIRE', 'fire_arima_monthly', 'fire_monthly_70_15_15.pkl'))
    logger.info("fire_monthly_70_15_15.pkl loaded successfully.")
except FileNotFoundError:
    logger.error("fire_monthly_70_15_15.pkl not found.")
except Exception as e:
    logger.error(f"Error loading fire_monthly_70_15_15.pkl: {e}")

f_arima_22 = None
try:
    f_arima_22 = joblib.load(os.path.join(os.path.dirname(__file__), 'training', 'Fire Models', 'ARIMA FIRE',  'fire_arima_forecast', 'fire_forecast_70_15_15.pkl'))
    logger.info("fire_forecast_70_15_15.pkl loaded successfully.")
except FileNotFoundError:
    logger.error("fire_forecast_70_15_15.pkl not found.")
except Exception as e:
    logger.error(f"Error loading fire_forecast_70_15_15.pkl: {e}")

f_arima_pred = None
try:
    f_arima_pred = joblib.load(os.path.join(os.path.dirname(__file__), 'training', 'Fire Models', 'ARIMA FIRE', 'fire_arima_pred',  'fire_arima_70_15_15.pkl'))
    logger.info("fire_arima_70_15_15.pkl loaded successfully.")
except FileNotFoundError:
    logger.error("fire_arima_70_15_15.pkl not found.")
except Exception as e:
    logger.error(f"Error loading fire_arima_70_15_15.pkl: {e}")  
    

f_arimax_m = None
try:
    f_arimax_m = joblib.load(os.path.join(os.path.dirname(__file__), 'training', 'Fire Models', 'ARIMAX FIRE', 'fire_arimax_monthly', 'fire_monthly_arimax_70_15_15.pkl'))
    logger.info("fire_monthly_arimax_70_15_15.pkl loaded successfully.")
except FileNotFoundError:
    logger.error("fire_monthly_arimax_70_15_15.pkl not found.")
except Exception as e:
    logger.error(f"Error loading fire_monthly_arimax_70_15_15.pkl: {e}")

f_arimax_22 = None
try:
    f_arimax_22 = joblib.load(os.path.join(os.path.dirname(__file__), 'training', 'Fire Models', 'ARIMAX FIRE',  'fire_arimax_forecast', 'fire_forecast_arimax_70_15_15.pkl'))
    logger.info("fire_forecast_arimax_70_15_15.pkl loaded successfully.")
except FileNotFoundError:
    logger.error("fire_forecast_arimax_70_15_15.pkl not found.")
except Exception as e:
    logger.error(f"Error loading fire_forecast_arimax_70_15_15.pkl: {e}")

f_arimax_pred = None
try:
    f_arimax_pred = joblib.load(os.path.join(os.path.dirname(__file__), 'training', 'Fire Models', 'ARIMAX FIRE', 'fire_arimax_pred',  'fire_arimax_70_15_15.pkl'))
    logger.info("fire_arimax_70_15_15.pkl loaded successfully.")
except FileNotFoundError:
    logger.error("fire_arimax_70_15_15.pkl not found.")
except Exception as e:
    logger.error(f"Error loading fire_arimax_70_15_15.pkl: {e}")
    

f_sarima_m = None
try:
    f_sarima_m = joblib.load(os.path.join(os.path.dirname(__file__), 'training', 'Fire Models', 'SARIMA FIRE', 'fire_sarima_monthly', 'fire_monthly_sarima_70_15_15.pkl'))
    logger.info("fire_monthly_sarima_70_15_15.pkl loaded successfully.")
except FileNotFoundError:
    logger.error("fire_monthly_sarima_70_15_15.pkl not found.")
except Exception as e:
    logger.error(f"Error loading fire_monthly_sarima_70_15_15.pkl: {e}")

f_sarima_22 = None
try:
    f_sarima_22 = joblib.load(os.path.join(os.path.dirname(__file__), 'training', 'Fire Models', 'SARIMA FIRE',  'fire_sarima_forecast', 'fire_forecast_sarima_70_15_15.pkl'))
    logger.info("fire_forecast_sarima_70_15_15.pkl loaded successfully.")
except FileNotFoundError:
    logger.error("fire_forecast_sarima_70_15_15.pkl not found.")
except Exception as e:
    logger.error(f"Error loading fire_forecast_sarima_70_15_15.pkl: {e}")

f_sarima_pred = None
try:
    f_sarima_pred = joblib.load(os.path.join(os.path.dirname(__file__), 'training', 'Fire Models', 'SARIMA FIRE', 'fire_sarima_pred',  'fire_sarima_70_15_15.pkl'))
    logger.info("fire_sarima_70_15_15.pkl loaded successfully.")
except FileNotFoundError:
    logger.error("fire_sarima_70_15_15.pkl not found.")
except Exception as e:
    logger.error(f"Error loading fire_sarima_70_15_15.pkl: {e}")
    
    

f_sarimax_m = None
try:
    f_sarimax_m = joblib.load(os.path.join(os.path.dirname(__file__), 'training', 'Fire Models', 'SARIMAX FIRE', 'fire_sarimax_monthly', 'fire_monthly_sarimax_70_15_15.pkl'))
    logger.info("fire_monthly_sarimax_70_15_15.pkl loaded successfully.")
except FileNotFoundError:
    logger.error("fire_monthly_sarimax_70_15_15.pkl not found.")
except Exception as e:
    logger.error(f"Error loading fire_monthly_sarimax_70_15_15.pkl: {e}")

f_sarimax_22 = None
try:
    f_sarimax_22 = joblib.load(os.path.join(os.path.dirname(__file__), 'training', 'Fire Models', 'SARIMAX FIRE',  'fire_sarimax_forecast', 'fire_forecast_sarimax_70_15_15.pkl'))
    logger.info("fire_forecast_sarimax_70_15_15.pkl loaded successfully.")
except FileNotFoundError:
    logger.error("fire_forecast_sarimax_70_15_15.pkl not found.")
except Exception as e:
    logger.error(f"Error loading fire_forecast_sarimax_70_15_15.pkl: {e}")

f_sarimax_pred = None
try:
    f_sarimax_pred = joblib.load(os.path.join(os.path.dirname(__file__), 'training', 'Fire Models', 'SARIMAX FIRE', 'fire_sarimax_pred',  'fire_sarimax_70_15_15.pkl'))
    logger.info("fire_sarimax_70_15_15.pkl loaded successfully.")
except FileNotFoundError:
    logger.error("fire_sarimax_70_15_15.pkl not found.")
except Exception as e:
    logger.error(f"Error loading fire_sarimax_70_15_15.pkl: {e}")
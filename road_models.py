import joblib
import os
import logging

logger = logging.getLogger(__name__)


#ARIMA MODEL

arima_m = None
try:
    arima_m = joblib.load(os.path.join(os.path.dirname(__file__), 'training', 'Road Models', 
                                       'ARIMA_ROAD', 'arima_monthly', 'monthly_arima80_20.pkl'))
    logger.info("monthly_arima80_20.pkl loaded successfully.")
except FileNotFoundError:
    logger.error("monthly_arima80_20.pkl not found.")
except Exception as e:
    logger.error(f"Error loading monthly_arima80_20.pkl: {e}")

arima_22 = None
try:
    arima_22 = joblib.load(os.path.join(os.path.dirname(__file__), 'training', 'Road Models', 
                                        'ARIMA_ROAD', 'arima_forecast', 'forecast_80_20.pkl'))
    logger.info("forecast_80_20.pkl loaded successfully.")
except FileNotFoundError:
    logger.error("forecast_80_20.pkl not found.")
except Exception as e:
    logger.error(f"Error loading forecast_80_20.pkl: {e}")

arima_pred = None
try:
    arima_pred = joblib.load(os.path.join(os.path.dirname(__file__), 'training', 'Road Models', 
                                          'ARIMA_ROAD', 'arima_pred', 'arima80_20.pkl'))
    logger.info("arima80_20.pkl loaded successfully.")
except FileNotFoundError:
    logger.error("arima80_20.pkl not found.")
except Exception as e:
    logger.error(f"Error loading arima80_20.pkl: {e}")
    
#ARIMAX MODEL  
    
arimax_m = None
try:
    arimax_m = joblib.load(os.path.join(os.path.dirname(__file__), 'training', 'Road Models', 
                                       'ARIMAX ROAD', 'arimax_monthly', 'monthly_arimax80_20.pkl'))
    logger.info("monthly_arimax80_20.pkl loaded successfully.")
except FileNotFoundError:
    logger.error("monthly_arimax80_20.pkl not found.")
except Exception as e:
    logger.error(f"Error loading monthly_arimax80_20.pkl: {e}")

arimax_22 = None
try:
    arimax_22 = joblib.load(os.path.join(os.path.dirname(__file__), 'training', 'Road Models', 
                                        'ARIMAX ROAD', 'arimax_forecast', 'arimax_forecast_80_20.pkl'))
    logger.info("arimax_forecast_80_20.pkl loaded successfully.")
except FileNotFoundError:
    logger.error("arimax_forecast_80_20.pkl not found.")
except Exception as e:
    logger.error(f"Error loading arimax_forecast_80_20.pkl: {e}")

arimax_pred = None
try:
    arimax_pred = joblib.load(os.path.join(os.path.dirname(__file__), 'training', 'Road Models', 
                                          'ARIMAX ROAD', 'arimax_pred', 'arimax80_20.pkl'))
    logger.info("arimax80_20.pkl loaded successfully.")
except FileNotFoundError:
    logger.error("arimax80_20.pkl not found.")
except Exception as e:
    logger.error(f"Error loading arimax80_20.pkl: {e}")
    

#SARIMA MODEL

sarima_m = None
try:
    sarima_m = joblib.load(os.path.join(os.path.dirname(__file__), 'training', 'Road Models', 
                                       'SARIMA ROAD', 'sarima_monthly', 'monthly_sarima80_20.pkl'))
    logger.info("monthly_sarima80_20.pkl loaded successfully.")
except FileNotFoundError:
    logger.error("monthly_sarima80_20.pkl not found.")
except Exception as e:
    logger.error(f"Error loading monthly_sarima80_20.pkl: {e}")

sarima_22 = None
try:
    sarima_22 = joblib.load(os.path.join(os.path.dirname(__file__), 'training', 'Road Models', 
                                        'SARIMA ROAD', 'sarima_forecast', 'SARIMA_forecast_80_20.pkl'))
    logger.info("SARIMA_forecast_80_20.pkl loaded successfully.")
except FileNotFoundError:
    logger.error("SARIMA_forecast_80_20.pkl not found.")
except Exception as e:
    logger.error(f"Error loading SARIMA_forecast_80_20.pkl: {e}")

sarima_pred = None
try:
    sarima_pred = joblib.load(os.path.join(os.path.dirname(__file__), 'training', 'Road Models', 
                                          'SARIMA ROAD', 'sarima_pred', 'sarima80_20.pkl'))
    logger.info("sarima80_20.pkl loaded successfully.")
except FileNotFoundError:
    logger.error("sarima80_20.pkl not found.")
except Exception as e:
    logger.error(f"Error loading sarima80_20.pkl: {e}")
    
#SARIMAX MODEL

sarimax_m = None
try:
    sarimax_m = joblib.load(os.path.join(os.path.dirname(__file__), 'training', 'Road Models', 
                                       'SARIMAX ROAD', 'sarimax_monthly', 'monthly_sarimax80_20.pkl'))
    logger.info("monthly_sarimax80_20.pkl loaded successfully.")
except FileNotFoundError:
    logger.error("monthly_sarimax80_20.pkl not found.")
except Exception as e:
    logger.error(f"Error loading monthly_sarimax80_20.pkl: {e}")

sarimax_22 = None
try:
    sarimax_22 = joblib.load(os.path.join(os.path.dirname(__file__), 'training', 'Road Models', 
                                        'SARIMAX ROAD', 'sarimax_forecast', 'SARIMAX_forecast_80_20.pkl'))
    logger.info("SARIMAX_forecast_80_20.pkl loaded successfully.")
except FileNotFoundError:
    logger.error("SARIMAX_forecast_80_20.pkl not found.")
except Exception as e:
    logger.error(f"Error loading SARIMAX_forecast_80_20.pkl: {e}")

sarimax_pred = None
try:
    sarimax_pred = joblib.load(os.path.join(os.path.dirname(__file__), 'training', 'Road Models', 
                                          'SARIMAX ROAD', 'sarimax_pred', 'sarimax80_20.pkl'))
    logger.info("sarimax80_20.pkl loaded successfully.")
except FileNotFoundError:
    logger.error("sarimax80_20.pkl not found.")
except Exception as e:
    logger.error(f"Error loading sarimax80_20.pkl: {e}")
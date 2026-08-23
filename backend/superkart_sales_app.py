# Import data manipulation libraries
import numpy as np
import pandas as pd

# For serialization
import joblib

# For reading uploaded file stream
import io

# Flask API
from flask import Flask, request, jsonify

# Import logging
import logging
import sys

# Initialize the Flask app with a name
superkart_api = Flask("superkart_sales_app")

# Debug info
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

logger.info(f"Module name: {__name__}")
logger.info(f"Flask app name: {superkart_api.name}")
logger.info(f"Root path: {superkart_api.root_path}")

# Load the trained sales prediction model
model = joblib.load("superkart_sales_forecast_model_v1.0.joblib")

# Required feature columns expected by the model
REQUIRED_COLUMNS = [
    'Product_Weight', 'Product_Sugar_Content', 'Product_Allocated_Area',
    'Product_MRP', 'Store_Size', 'Store_Location_City_Type',
    'Store_Type', 'Store_Age_Years', 'Product_Type_Category', 'Product_Id_char'
]


# Define a route for the home page
@superkart_api.route('/', methods=['GET'])
def home():
    """
    Handles GET requests to the root URL ('/').
    Returns a welcome message and endpoint help.
    """
    logger.info("Home endpoint accessed")

    html = """
      <!DOCTYPE html>
      <html>
      <head>
        <title>SuperKart Sales API</title>
        <style>
          body { font-family: Arial, sans-serif; text-align: center; padding: 50px; background-color: #f4f4f4; }
          h1 { color: #333; font-size: 3em; }
          p  { color: #666; font-size: 1.5em; margin-top: 20px; }
        </style>
      </head>
      <body>
        <h1>Welcome to SuperKart Sales Prediction API.</h1>
        <p>Single prediction: POST request to `/v1/predict`.</p>
        <p>Batch prediction: POST CSV file to `/v1/predictbatch`.</p>
      </body>
      </html>
    """
    return html


# Define an endpoint to predict a single product sale
@superkart_api.route('/v1/predict', methods=['POST'])
def predict_sales():
    """
    Handles POST requests to /v1/predict.
    Gets JSON data from the request and returns predicted sale.
    """
    try:
        data = request.get_json()

        sample = {
            'Product_Weight': data['Product_Weight'],
            'Product_Sugar_Content': data['Product_Sugar_Content'],
            'Product_Allocated_Area': data['Product_Allocated_Area'],
            'Product_MRP': data['Product_MRP'],
            'Store_Size': data['Store_Size'],
            'Store_Location_City_Type': data['Store_Location_City_Type'],
            'Store_Type': data['Store_Type'],
            'Store_Age_Years': data['Store_Age_Years'],
            'Product_Type_Category': data['Product_Type_Category'],
            'Product_Id_char': data['Product_Id_char']
        }

        input_data = pd.DataFrame([sample])
        logger.debug(f"Input DataFrame:\n{input_data}")

        prediction = model.predict(input_data).tolist()[0]
        return jsonify({'Sales': prediction})

    except KeyError as e:
        return jsonify({'error': f'Missing key: {str(e)}'}), 400
    except Exception as e:
        return jsonify({'error': f'Prediction failed: {str(e)}'}), 500


# Define an endpoint for batch prediction via CSV upload
@superkart_api.route('/v1/predictbatch', methods=['POST'])
def predict_sales_batch():
    """
    Handles POST requests to /v1/predictbatch.
    Accepts a CSV file upload, validates it, runs batch predictions,
    and returns the results as JSON.
    """
    try:
        # CHECK 1: file must be present under form key 'file'
        if 'file' not in request.files:
            return jsonify({'error': "No file part in request. Use form key 'file'."}), 400

        file = request.files['file']

        # CHECK 2: a file must actually be selected
        if file.filename == '':
            return jsonify({'error': 'No file selected.'}), 400

        # CHECK 3: file must be a CSV
        if not file.filename.lower().endswith('.csv'):
            return jsonify({'error': 'Invalid file type. Only .csv files are accepted.'}), 400

        # CHECK 4: file must parse as CSV
        try:
            stream = io.StringIO(file.stream.read().decode('utf-8'))
            input_df = pd.read_csv(stream)
        except Exception as e:
            return jsonify({'error': f'Could not parse CSV: {str(e)}'}), 400

        logger.info(f"Batch file '{file.filename}' loaded with shape {input_df.shape}")

        # CHECK 5: file must not be empty
        if input_df.empty:
            return jsonify({'error': 'Uploaded CSV is empty.'}), 400

        # CHECK 6: all required columns must be present
        missing_cols = [c for c in REQUIRED_COLUMNS if c not in input_df.columns]
        if missing_cols:
            return jsonify({'error': f'Missing required columns: {missing_cols}'}), 400

        # Keep only required columns in the correct order
        input_features = input_df[REQUIRED_COLUMNS]

        # Run batch predictions
        predictions = model.predict(input_features)

        # Attach predictions to the original data
        output_df = input_df.copy()
        output_df['Predicted_Sales'] = np.round(predictions, 2)

        logger.info(f"Batch prediction completed for {len(output_df)} rows")

        # Return results as JSON (records + count) for the UI to render
        return jsonify({
            'n_records': len(output_df),
            'predictions': output_df.to_dict(orient='records')
        })

    except Exception as e:
        return jsonify({'error': f'Batch prediction failed: {str(e)}'}), 500


# Run the Flask app in debug mode
if __name__ == '__main__':
    superkart_api.run(debug=True)

FROM python:3.9-slim

# Working directory
WORKDIR /app

# Install dependencies (requirements copied first for layer caching)
COPY requirements.txt .

RUN pip install --upgrade pip
RUN pip install --no-cache-dir --upgrade -r requirements.txt

# Copy the Streamlit app code
COPY . .

# Streamlit default port (Codespaces will auto-forward it)
EXPOSE 8501

# Run the Streamlit app
# --server.address 0.0.0.0 : required so Codespaces can forward the port
# --server.port 8501       : fixed port for forwarding
CMD ["streamlit", "run", "superkart_sales_app_ui.py", \
     "--server.port", "8501", \
     "--server.address", "0.0.0.0"]

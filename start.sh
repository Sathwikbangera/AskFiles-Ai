#!/bin/bash
set -e

uvicorn app.main:app --host 0.0.0.0 --port 8000 &

streamlit run streamlit_app/app.py --server.port "${PORT:-7860}" --server.address 0.0.0.0

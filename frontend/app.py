import httpx
import streamlit as st

from frontend.config import settings

st.title("Strava Goal Visualizer")

try:
    response = httpx.get(f"{settings.api_base_url}/health", timeout=5)
    if response.status_code == 200:
        st.success("Backend: connected ✓")
    else:
        st.error("Backend: unreachable ✗")
except httpx.HTTPError:
    st.error("Backend: unreachable ✗")

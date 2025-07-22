import requests
import streamlit as st  # optional for error reporting

def send_to_webhook(data: dict, webhook_url: str = "http://localhost:5678/webhook/2037dafb-3a78-4ece-9f03-3db50f6dda2f") -> dict:
    try:
        response = requests.post(
            webhook_url,
            json=data,
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
        return response.json()  # return the full response content
    except Exception as e:
        st.error("Webhook error: " + str(e))
        return {}  # return empty dict on error

import os
from page import Page

DEFAULT_API_BASE_URL: str = "https://api.simplyprint.io"

def _get_env_int(name: str, default: int) -> int:
    value = os.getenv(name, str(default))
    try:
        return int(value)
    except ValueError:
        return default

api_base_url = os.getenv("SIMPLYPRINT_API_BASE_URL", DEFAULT_API_BASE_URL)
api_token = os.getenv("SIMPLYPRINT_API_TOKEN")
api_company_id = os.getenv("SIMPLYPRINT_API_COMPANY_ID")
refresh_seconds = _get_env_int("REFRESH_SECONDS", 3600)

page = Page(api_base_url=api_base_url,
            api_token=api_token,
            api_company_id=api_company_id,
            refresh_seconds=refresh_seconds)
page.render()

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Dict
from urllib.parse import urljoin

import requests

@dataclass
class SimplyPrintError(Exception):
    message: str

    def __str__(self) -> str:
        return self.message

@dataclass(frozen=True)
class SimplyPrintFilament:
    id: int
    uid: str
    brand: str
    material_id: int
    color_name: str
    color_hex: str
    length_total: int
    length_left: int
    diameter: float

    @staticmethod
    def parse(payload: dict) -> SimplyPrintFilament:
        type_payload = payload.get("type")
        material_id = type_payload.get("id") if type_payload is not None else 0

        return SimplyPrintFilament(
            id=payload.get("id"),
            uid=payload.get("uid"),
            brand=payload.get("brand"),
            material_id=material_id,
            color_name=payload.get("colorName"),
            color_hex=payload.get("colorHex"),
            length_total=payload.get("total"),
            length_left=payload.get("left"),
            diameter=payload.get("dia"))

@dataclass(frozen=True)
class SimplyPrintMaterial:
    id: int
    brand: str
    material_type: str
    filament_type_name: str
    density: float

    @staticmethod
    def parse(payload: dict) -> SimplyPrintMaterial:
        brand_payload = payload.get("brand")
        brand = brand_payload.get("name") if brand_payload is not None else ""

        return SimplyPrintMaterial(
            id=payload.get("id"),
            brand=brand,
            material_type=payload.get("material_type_name"),
            filament_type_name=payload.get("filament_type_name"),
            density=payload.get("density"))


class SimplyPrintClient:
    def __init__(self, api_base_url: str, api_token: str, api_company_id: str, timeout: float = 10.0) -> None:
        self.api_base_url = api_base_url.rstrip("/")
        self.api_token = api_token
        self.api_company_id = api_company_id
        self.timeout = timeout

    @staticmethod
    def _join_url(base: str, parts: list[str], trailing_slash: bool = False) -> str:
        url = base.rstrip("/") + "/"

        for p in parts:
            url = urljoin(url, p.strip("/") + "/")

        if not trailing_slash:
            url = url.rstrip("/")

        return url

    def _get(self, endpoint: str) -> dict:
        url = self._join_url(self.api_base_url, [self.api_company_id, endpoint])
        headers = {
            "Accept": "application/json",
            "X-API-KEY": self.api_token
        }

        try:
            response = requests.get(url, headers=headers, timeout=self.timeout)
        except requests.Timeout as exception:
            raise SimplyPrintError("SimplyPrint API request timed out.") from exception
        except requests.RequestException as exception:
            raise SimplyPrintError("Failed to connect to SimplyPrint API.") from exception

        if response.status_code != 200:
            raise SimplyPrintError(f"Failed to retrieve data from SimplyPrint API. Status code: {response.status_code}")

        try:
            payload = response.json()
        except json.JSONDecodeError as exception:
            raise SimplyPrintError("Invalid JSON response from SimplyPrint API.") from exception

        if isinstance(payload, dict):
            status = payload.get("status")
            if status is False:
                message = payload.get("message") or "SimplyPrint API returned an error."
                raise SimplyPrintError(str(message))

        return payload

    def get_filaments(self) -> Dict[int, SimplyPrintFilament]:
        payload = self._get("/filament/GetFilament")

        filament_payload = payload.get("filament")
        if filament_payload is None:
            raise SimplyPrintError("Unexpected response format from SimplyPrint API.")

        filaments: Dict[int, SimplyPrintFilament] = {}

        for item in filament_payload.values():
            filament = SimplyPrintFilament.parse(item)
            if filament.id is None:
                raise SimplyPrintError("Unexpected filament payload from SimplyPrint API.")
            filaments[filament.id] = filament

        return filaments

    def get_materials(self) -> Dict[int, SimplyPrintMaterial]:
        payload = self._get("/filament/type/Get")

        material_payload = payload.get("data")
        if material_payload is None:
            raise SimplyPrintError("Unexpected response format from SimplyPrint API.")

        materials: Dict[int, SimplyPrintMaterial] = {}

        for item in material_payload:
            material = SimplyPrintMaterial.parse(item)
            if material.id is None:
                raise SimplyPrintError("Unexpected material payload from SimplyPrint API.")
            materials[material.id] = material

        return materials

from __future__ import annotations

import math
from typing import Dict
from datetime import datetime, timezone

import streamlit as st

from simplyprint import SimplyPrintFilament, SimplyPrintMaterial, SimplyPrintClient, SimplyPrintError

class Page:
    def __init__(self, api_base_url: str, api_token: str, api_company_id: str, refresh_seconds: int):
        self.api_base_url: str = api_base_url
        self.api_token: str = api_token
        self.api_company_id: str = api_company_id
        self.refresh_seconds: int = refresh_seconds

    COLS_PER_ROW: int = 3
    SELECTED_BRANDS_KEY: str = "selected_brands"
    SELECTED_MATERIAL_TYPES_KEY: str = "selected_material_types"
    SELECTED_FILAMENT_TYPE_NAMES_KEY: str = "selected_filament_type_names"

    SVG_SIZE: int = 140
    SVG_VIEWBOX_SIZE: int = 100
    SVG_SPOOL_OUTER_RADIUS: int = 45
    SVG_SPOOL_INNER_HOLE_RADIUS: int = 15
    SVG_SPOOL_FILAMENT_MIN_RADIUS: int = 18
    SVG_SPOOL_STROKE_COLOR: str = "#7d7d7d"
    SVG_SPOOL_STROKE_COLOR_WIDTH: int = 3
    SVG_SPOOL_FILL_COLOR: str = "#c9c9c9"
    SVG_SPOOL_INNER_COLOR: str = "#f6f6f6"

    def _render_materials(self, materials: Dict[int, SimplyPrintMaterial]) -> tuple[list[SimplyPrintMaterial], bool]:
        material_list = list(materials.values())

        with st.container(border=True):
            st.subheader("Filter")
            selected_brands = st.session_state.get(self.SELECTED_BRANDS_KEY, [])
            selected_material_types = st.session_state.get(self.SELECTED_MATERIAL_TYPES_KEY, [])
            selected_filament_type_names = st.session_state.get(self.SELECTED_FILAMENT_TYPE_NAMES_KEY, [])

            available_brands = sorted({
                material.brand for material in material_list
                if material.brand and (not selected_material_types or material.material_type in selected_material_types)
                and (not selected_filament_type_names or material.filament_type_name in selected_filament_type_names)
            })
            available_material_types = sorted({
                material.material_type for material in material_list
                if material.material_type and (not selected_brands or material.brand in selected_brands)
                and (not selected_filament_type_names or material.filament_type_name in selected_filament_type_names)
            })
            available_filament_type_names = sorted({
                material.filament_type_name for material in material_list
                if material.filament_type_name and (not selected_brands or material.brand in selected_brands)
                and (not selected_material_types or material.material_type in selected_material_types)
            })

            st.session_state[self.SELECTED_BRANDS_KEY] = [
                brand for brand in selected_brands if brand in available_brands
            ]
            st.session_state[self.SELECTED_MATERIAL_TYPES_KEY] = [
                material_type for material_type in selected_material_types if material_type in available_material_types
            ]
            st.session_state[self.SELECTED_FILAMENT_TYPE_NAMES_KEY] = [
                filament_type_name for filament_type_name in selected_filament_type_names
                if filament_type_name in available_filament_type_names
            ]

            selected_brands = st.multiselect(
                "Brands",
                available_brands,
                key=self.SELECTED_BRANDS_KEY
            )
            selected_material_types = st.multiselect(
                "Material types",
                available_material_types,
                key=self.SELECTED_MATERIAL_TYPES_KEY
            )
            selected_filament_type_names = st.multiselect(
                "Filament type names",
                available_filament_type_names,
                key=self.SELECTED_FILAMENT_TYPE_NAMES_KEY
            )

        filtered_materials = [
            material for material in material_list
            if (not selected_brands or material.brand in selected_brands)
            and (not selected_material_types or material.material_type in selected_material_types)
            and (not selected_filament_type_names or material.filament_type_name in selected_filament_type_names)
        ]
        filters_active = bool(selected_brands or selected_material_types or selected_filament_type_names)
        return filtered_materials, filters_active

    def _render_filaments(self, filaments: Dict[int, SimplyPrintFilament], materials: Dict[int, SimplyPrintMaterial]) -> None:
        filament_list = list(filaments.values())
        for i in range(0, len(filament_list), self.COLS_PER_ROW):
            cols = st.columns(self.COLS_PER_ROW)
            for col, filament in zip(cols, filament_list[i : i + self.COLS_PER_ROW]):
                with col:
                    material = materials.get(filament.material_id)
                    if material is None:
                        st.warning(f"Material {filament.material_id} not found.")
                        continue
                    with st.container(border=True):
                        col1, col2 = st.columns([2, 1])
                        with col1:
                            st.subheader(f"{filament.color_name} - {material.material_type}")
                            st.write(f"*{filament.brand} - {material.filament_type_name}*")
                        with col2:
                            svg = self._create_spool_svg(filament.color_hex, filament.length_left / filament.length_total)
                            st.write(f"""<div style="display:flex; justify-content:center;">{svg}</div>""", unsafe_allow_html=True)
                        st.space("xxsmall")
                        grams_left = self._filament_grams_left(filament.length_left, filament.diameter, material.density)
                        fill = filament.length_left / filament.length_total
                        st.progress(fill)
                        if grams_left is not None:
                            st.write(f"**{grams_left:.0f}g** - {int(fill * 100)}%")
                        else:
                            st.write(f"{int(fill * 100)}%")

    def _create_spool_svg(self, fill_hex: str, fill_percentage: float = 1.0) -> str:

        fill_percentage = max(0.0, min(1.0, fill_percentage))

        filament_radius = round(
            self.SVG_SPOOL_FILAMENT_MIN_RADIUS +
            (self.SVG_SPOOL_OUTER_RADIUS - self.SVG_SPOOL_FILAMENT_MIN_RADIUS) * fill_percentage,
            2
        )

        return f"""
        <svg xmlns="http://www.w3.org/2000/svg" width="{self.SVG_SIZE}" height="{self.SVG_SIZE}" viewBox="0 0 {self.SVG_VIEWBOX_SIZE} {self.SVG_VIEWBOX_SIZE}" role="img" aria-label="filament spool"> 
          <circle cx="{self.SVG_VIEWBOX_SIZE / 2}" cy="{self.SVG_VIEWBOX_SIZE / 2}" r="{self.SVG_SPOOL_OUTER_RADIUS}" fill="{self.SVG_SPOOL_FILL_COLOR}" stroke="{self.SVG_SPOOL_STROKE_COLOR}" stroke-width="{self.SVG_SPOOL_STROKE_COLOR_WIDTH}"/>
          <circle cx="{self.SVG_VIEWBOX_SIZE / 2}" cy="{self.SVG_VIEWBOX_SIZE / 2}" r="{filament_radius}" fill="{fill_hex}"/>
          <circle cx="{self.SVG_VIEWBOX_SIZE / 2}" cy="{self.SVG_VIEWBOX_SIZE / 2}" r="{self.SVG_SPOOL_INNER_HOLE_RADIUS}" fill="{self.SVG_SPOOL_INNER_COLOR}" stroke="{self.SVG_SPOOL_STROKE_COLOR}" stroke-width="{self.SVG_SPOOL_STROKE_COLOR_WIDTH}"/>
        </svg>
        """

    @staticmethod
    def _filament_grams_left(length_mm: int, diameter_mm: float, density: float):
        area_mm2 = math.pi * (diameter_mm / 2) ** 2
        volume_mm3 = area_mm2 * length_mm
        volume_cm3 = volume_mm3 / 1000
        grams = volume_cm3 * density
        return grams

    def render(self):
        st.set_page_config(page_title="Filaments",
                           layout="wide")

        st.title("Filaments")

        if not self.api_token:
            st.error("Missing SIMPLYPRINT_API_TOKEN. Set it in your environment and restart.")
            st.stop()

        if not self.api_company_id:
            st.error("Missing SIMPLYPRINT_API_COMPANY_ID. Set it in your environment and restart.")
            st.stop()

        client = SimplyPrintClient(api_base_url=self.api_base_url,
                                   api_token=self.api_token,
                                   api_company_id=self.api_company_id)

        @st.cache_data(ttl=self.refresh_seconds)
        def refresh_data() -> tuple[Dict[int, SimplyPrintMaterial], Dict[int, SimplyPrintFilament], datetime]:
            return client.get_materials(), client.get_filaments(), datetime.now(timezone.utc)

        try:
            materials, filaments, now = refresh_data()
            last_fetch = now.astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
            st.caption(f"Last fetch: {last_fetch} | Materials: {len(materials)} | Spools: {len(filaments)}")
            filtered_materials, filters_active = self._render_materials(materials)
            if filters_active:
                filtered_material_ids = {material.id for material in filtered_materials}
                filtered_filaments = {
                    filament_id: filament
                    for filament_id, filament in filaments.items()
                    if filament.material_id in filtered_material_ids
                }
            else:
                filtered_filaments = filaments
            self._render_filaments(filtered_filaments, materials)
        except SimplyPrintError as exception:
            st.error(str(exception))
            st.stop()

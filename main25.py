# streamlit run "C:\GPSAPPLICATION\main25.py"

import streamlit as st
from streamlit_folium import st_folium
import folium
from branca.element import Element
from supabase import create_client, Client
from datetime import datetime
import geocoder

# Supabase
url = "https://wqtpemsaxmanzxmdwhhp.supabase.co"
key = key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6IndxdHBlbXNheG1hbnp4bWR3aGhwIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDg0NTM2OTIsImV4cCI6MjA2NDAyOTY5Mn0.2pPOuHHX2XN0jXQtCTkoJsJ08qjZVJmDafEImZZvZ-k"
supabase: Client = create_client(url, key)

# Сохранение маршрута
def save_route():
    try:
        for pid in [2147483646, 2147483647]:
            check = supabase.table("route_points").select("id_point").eq("id_point", pid).execute()
            if not check.data:
                supabase.table("route_points").insert({
                    "id_point": pid,
                    "route_id": None,
                    "point_type": "route",
                    "lat": 0.0,
                    "lon": 0.0,
                    "description": "reserved"
                }).execute()

        ip = geocoder.ip("me").ip or "unknown"
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        res = supabase.table("routes").insert({
            "name": st.session_state["route_name"].strip(),
            "description": st.session_state["route_description"].strip(),
            "user_ip": ip,
            "point_id_start": 2147483646,
            "point_id_end": 2147483647,
            "created_at": now
        }).execute()

        if not res.data:
            st.error("Не удалось сохранить маршрут.")
            return

        route_id = res.data[0]["id_route"]
        point_ids = []

        for i, pt in enumerate(st.session_state["free_points"]):
            ptype = "start" if i == 0 else "final" if i == 1 else "route"
            inserted = supabase.table("route_points").insert({
                "route_id": route_id,
                "point_type": ptype,
                "lat": pt["coords"][0],
                "lon": pt["coords"][1],
                "description": pt["desc"] or ""
            }).execute()
            if inserted.data:
                point_ids.append(inserted.data[0]["id_point"])

        if len(point_ids) >= 2:
            supabase.table("routes").update({
                "point_id_start": point_ids[0],
                "point_id_end": point_ids[1]
            }).eq("id_route", route_id).execute()

        st.success(f"Маршрут успешно добавлен (ID: {route_id})")
        st.session_state["free_points"] = []
        st.session_state["selected_description"] = "—"
    except Exception as e:
        st.error(f"Ошибка при сохранении маршрута: {e}")

# Session defaults
for k, v in {
    "free_points": [],
    "point_description": "",
    "selected_description": "—",
    "route_name": "",
    "route_description": "",
}.items():
    st.session_state.setdefault(k, v)

st.set_page_config(page_title="Свободный режим", layout="wide")
st.markdown('<p style="font-size:1.6rem;font-weight:700;">🗘️ Свободный режим на карте</p>', unsafe_allow_html=True)

m = folium.Map(location=[55.75, 37.61], zoom_start=14, width="100%", height=500)
for i, pt in enumerate(st.session_state["free_points"]):
    txt = pt["desc"] or "без описания"
    color = "#cc6600" if i == 0 else "purple" if i == 1 else "green"
    folium.CircleMarker(
        location=pt["coords"], radius=6,
        color=color, fill=True, fill_color=color, fill_opacity=0.9,
        tooltip=txt[:100]
    ).add_to(m)

m.get_root().html.add_child(Element("<style>.leaflet-control-attribution{display:none!important}</style>"))
map_data = st_folium(m, key="map", width=700, height=500, returned_objects=["last_clicked"])

if map_data and map_data.get("last_clicked"):
    lat = map_data["last_clicked"]["lat"]
    lon = map_data["last_clicked"]["lng"]
    matched = any(abs(pt["coords"][0] - lat) < .0001 and abs(pt["coords"][1] - lon) < .0001 for pt in st.session_state["free_points"])
    if not matched:
        st.session_state["free_points"].append({
            "coords": [lat, lon],
            "desc": st.session_state["point_description"].strip() or "без описания"
        })
        st.session_state["point_description"] = ""
        st.rerun()

cols = st.columns([1, 1, 6], gap="small")
with cols[0]:
    if st.button("Добавить", key="add_point", disabled=len(st.session_state["free_points"]) < 2):
        if not st.session_state["route_name"].strip():
            st.warning("Название маршрута не может быть пустой")
        else:
            save_route()
with cols[1]:
    st.button("Закрыть", key="close_mode", disabled=True)

st.text_input("Описание точки", key="point_description", label_visibility="collapsed", placeholder="Описание точки", max_chars=128)
st.text_input("Название маршрута", key="route_name", placeholder="Название маршрута", max_chars=64)
st.text_area("Описание маршрута", key="route_description", height=120, placeholder="Описание маршрута", max_chars=512)

st.markdown("""
<style>
iframe[title="streamlit_folium.st_folium"] {
    width:700px!important; height:500px!important; margin-bottom:0!important;
}
div[data-testid="stVerticalBlock"] > div:has(iframe) {
    padding-bottom:0!important; margin-bottom:0!important;
}

/* Обёртки полей ввода */
div[data-testid="stTextInput"], div[data-testid="stTextArea"] {
    max-width: 700px !important;
    width: 700px !important;
    margin-bottom: 1rem;
}

/* Сами input и textarea */
div[data-testid="stTextInput"] input,
div[data-testid="stTextArea"] textarea {
    width: 100% !important;
    padding: 0.5rem 0.75rem !important;
    font-size: 1rem !important;
    line-height: 1.5rem !important;
    box-sizing: border-box !important;
}

/* Убираем Ctrl+Enter */
div[style*="Ctrl+Enter"] {
    display: none !important;
}

/* Колонки */
div[data-testid="column"] {
    width:225px!important; min-width:200px!important;
}

/* Кнопки */
div.stButton > button {
    width:100%!important; min-width:180px;
    background: none; border: 1px solid #fff; border-radius: 0;
    color: #fff; padding: 0.4rem 0.8rem; font-size: 0.88rem;
    white-space: nowrap; cursor: pointer;
}
div.stButton > button:disabled {
    opacity: 0.5; cursor: not-allowed;
}
</style>
""", unsafe_allow_html=True)

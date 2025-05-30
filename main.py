# streamlit run "C:\GPSAPPLICATION\main.py"

# Закрыть с помощью CTRL+C

# https://supabase.com/dashboard/org/jmgunyoztlsyjwrxvzlm
# https://share.streamlit.io/
# https://github.com/oleg9999999?tab=repositories

# EExckQATDg2WORhM

# КОМАНДЫ В ТЕРМИНАЛ, ЧТОБЫ ОБНОВИТЬ ФАЙЛЫ ПРОЕКТА
# git status
# git add .
# git commit -m "СДЕЛАЛ ИЗМЕНЕНИЕ"
# git push

import streamlit as st
import geocoder
import folium
from streamlit_folium import st_folium
from branca.element import Element
from folium.plugins import LocateControl

# Supabase
from supabase import create_client, Client

# 🔑 Подключение
url = "https://wqtpemsaxmanzxmdwhhp.supabase.co"
key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6IndxdHBlbXNheG1hbnp4bWR3aGhwIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDg0NTM2OTIsImV4cCI6MjA2NDAyOTY5Mn0.2pPOuHHX2XN0jXQtCTkoJsJ08qjZVJmDafEImZZvZ-k"
supabase: Client = create_client(url, key)

# 🚀 Streamlit setup
st.set_page_config(page_title="Виртуальный Экскурсовод", layout="wide")
st.title("🌏️ Карта маршрута", anchor=False)

# 🧬 Session State
st.session_state.setdefault("last_route_id", None)
st.session_state.setdefault("toggle_end", False)
st.session_state.setdefault("show_modal", False)
st.session_state.setdefault("show_complain", False)
st.session_state.setdefault("found_valid_route", False)
st.session_state.setdefault("route_name", None)
st.session_state.setdefault("route_description", None)
st.session_state.setdefault("point_description", None)

# 🔎 Панель поиска
with st.container():
    st.markdown('<div style="height:20px"></div>', unsafe_allow_html=True)
    st.markdown('<h3 style="margin-bottom:0.5em">🔎 ID маршрута</h3>', unsafe_allow_html=True)

    id_col, btn_col = st.columns([3, 1], gap="small")
    with id_col:
        st.text_input("route_id_input", placeholder="Введите ID маршрута", label_visibility="collapsed", key="route_id")
    with btn_col:
        find_clicked = st.button("Найти", key="find_route", type="primary", use_container_width=True)

    m = folium.Map(location=[0, 0], zoom_start=2, width="100%", height=500)

    if find_clicked:
        rid = st.session_state.get("route_id")
        st.session_state["found_valid_route"] = False

        if rid:
            try:
                rid_int = int(rid)
                res = supabase.table("routes").select("*").eq("id_route", rid_int).execute()
                if res.data:
                    route = res.data[0]
                    st.session_state["found_valid_route"] = True
                    st.session_state["last_route_id"] = rid_int
                    st.session_state["route_name"] = route.get("name") or "Без названия"
                    st.session_state["route_description"] = route.get("description") or "без описания"

                    start_id = route.get("point_id_start")
                    end_id = route.get("point_id_end")

                    points = []
                    if start_id:
                        start_point = supabase.table("route_points").select("lat,lon,description").eq("id_point", start_id).execute().data
                        if start_point:
                            pt = start_point[0]
                            points.append((pt["lat"], pt["lon"], "Начало маршрута", "purple", pt.get("description")))
                    if end_id:
                        end_point = supabase.table("route_points").select("lat,lon,description").eq("id_point", end_id).execute().data
                        if end_point:
                            pt = end_point[0]
                            points.append((pt["lat"], pt["lon"], "Конец маршрута", "orange", pt.get("description")))

                    if points:
                        m = folium.Map(location=points[0][:2], zoom_start=18, width="100%", height=500)
                        for lat, lon, tip, color, desc in points:
                            folium.Marker(
                                [lat, lon],
                                tooltip=tip,
                                icon=folium.Icon(color=color)
                            ).add_to(m)
                            if tip == "Начало маршрута":
                                st.session_state["point_description"] = desc or "без описания"

                    all_points = supabase.table("route_points").select("*").eq("route_id", rid_int).eq("point_type", "route").execute().data
                    for pt in all_points:
                        desc = (pt.get("description") or "без описания")[:100]
                        marker = folium.CircleMarker(
                            location=[pt["lat"], pt["lon"]],
                            radius=5,
                            color="green",
                            fill=True,
                            fill_opacity=0.9,
                            tooltip=desc
                        )
                        marker.add_child(folium.Popup(desc))
                        m.add_child(marker)
                else:
                    st.warning("Маршрут не найден")
                    st.session_state["found_valid_route"] = False
                    st.session_state["route_name"] = None
                    st.session_state["route_description"] = None
                    st.session_state["point_description"] = None
            except ValueError:
                st.warning("ID должен быть числом")
        else:
            st.warning("Введите ID маршрута")

    if st.session_state["found_valid_route"]:
        st.markdown(f"**Название маршрута:** {st.session_state['route_name']}")
        st.markdown(f"**Описание маршрута:** {st.session_state['route_description']}")
    else:
        st.markdown("**Маршрут не выбран**")

    LocateControl(auto_start=False, flyTo=True, position="bottomright").add_to(m)
    m.get_root().html.add_child(Element("""
        <style>
        .leaflet-control-attribution { display: none!important; }
        .folium-map { padding:0!important; height:500px!important; }
        </style>
    """))

    map_data = st_folium(m, width=700, height=500, returned_objects=["last_clicked"])
    if map_data.get("last_clicked"):
        clicked_lat = map_data["last_clicked"]["lat"]
        clicked_lon = map_data["last_clicked"]["lng"]
        rid = st.session_state.get("last_route_id")
        if rid:
            all_points = supabase.table("route_points").select("*").eq("route_id", rid).execute().data
            for pt in all_points:
                if abs(pt["lat"] - clicked_lat) < 0.0001 and abs(pt["lon"] - clicked_lon) < 0.0001:
                    st.session_state["point_description"] = pt.get("description") or "без описания"
                    break

# ── Кнопки под картой ─────────────────────
sp_l, col_create, sp_c, col_my, sp_r, col_complain, sp_r2 = st.columns([0.5, 2, 0.5, 2, 0.5, 2, 0.5])

with col_create:
    if st.button("Создать маршрут", key="btn_create", type="secondary"):
        st.session_state["show_modal"] = True

with col_my:
    st.button("Мои маршруты", key="btn_my", type="secondary")

with col_complain:
    if st.button("Пожаловаться", key="btn_complain", type="secondary",
                 disabled=not st.session_state["found_valid_route"]):
        st.session_state["show_complain"] = True

# ── Модалка: Создать маршрут ───────────────
if st.session_state["show_modal"]:
    st.markdown("### 🌍 Укажите маршрут")
    modal_map = folium.Map(location=[55.75, 37.61], zoom_start=14, width="100%", height="500")
    LocateControl(auto_start=True).add_to(modal_map)
    modal_map.get_root().html.add_child(Element(
        "<style>.leaflet-control-attribution{display:none!important}</style>"))
    st_folium(modal_map, key="modal_map_unique", width=700, height=500)

    if st.button("Закрыть окно", key="btn_close", use_container_width=True):
        st.session_state["show_modal"] = False

# ── Модалка: Жалоба ────────────────────────
if st.session_state.get("show_complain") and st.session_state.get("last_route_id"):
    st.markdown(f"### 🤬 Пожаловаться на маршрут (ID: {st.session_state['last_route_id']})")
    message = st.text_area("Опишите проблему", key="complaint_text", height=100)

    col_left, col_right, _ = st.columns([1, 1, 3])
    with col_left:
        if st.button("Отправить", key="btn_submit_complaint"):
            if message and message.strip():
                try:
                    ip = geocoder.ip('me').ip or "unknown"
                    supabase.table("complaints").insert({
                        "route_id": st.session_state["last_route_id"],
                        "message": message.strip(),
                        "user_ip": ip
                    }).execute()
                    st.success("Ваша жалоба отправлена")
                    st.session_state["show_complain"] = False
                except Exception as e:
                    st.error(f"Ошибка при отправке жалобы: {e}")
            else:
                st.warning("Жалоба не может быть пустой")
    with col_right:
        if st.button("Закрыть", key="btn_cancel_complaint"):
            st.session_state["show_complain"] = False

# ── CSS ────────────────────────────────────
st.markdown(r"""
<style>
button[kind="primary"],
button[kind="secondary"],
button[kind="primary"]:disabled,
button[kind="secondary"]:disabled {
    background: none !important;
    border: 1px solid #fff !important;
    border-radius: 0 !important;
    color: #fff !important;
    padding: 0.2rem 0.8rem !important;
    font-size: 0.85rem !important;
    height: auto !important;
    width: auto !important;
}
div[data-testid="stVerticalBlock"] > div:has(iframe){
    padding: 0 !important;
    background: none !important;
}
iframe[title="streamlit_folium.st_folium"] {
    height: 500px !important;
    min-height: 500px !important;
    margin-bottom: 0 !important;
    display: block;
}
h1 a, h2 a, h3 a { display: none !important; }
.block-container {
    padding: 1rem 2rem;
    max-width: 800px;
    margin: auto;
}
</style>
""", unsafe_allow_html=True)
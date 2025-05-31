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
import folium
from streamlit_folium import st_folium
from branca.element import Element
from folium.plugins import LocateControl
from datetime import datetime
import geocoder
from streamlit_javascript import st_javascript

# Supabase
from supabase import create_client, Client

# 🔑 Подключение
url = "https://wqtpemsaxmanzxmdwhhp.supabase.co"
key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6IndxdHBlbXNheG1hbnp4bWR3aGhwIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDg0NTM2OTIsImV4cCI6MjA2NDAyOTY5Mn0.2pPOuHHX2XN0jXQtCTkoJsJ08qjZVJmDafEImZZvZ-k"
supabase: Client = create_client(url, key)

# ── Ф-я сохранения маршрута (для «Свободного режима») ────────────────────────
def save_route() -> None:
    """Сохраняет новый маршрут из st.session_state.free_points."""
    try:
        # резервируем две «фиктивные» точки, если их ещё нет
        for pid in (2147483646, 2147483647):
            exists = supabase.table("route_points").select("id_point") \
                     .eq("id_point", pid).execute()
            if not exists.data:
                supabase.table("route_points").insert({
                    "id_point": pid, "route_id": None, "point_type": "route",
                    "lat": 0.0, "lon": 0.0, "description": "reserved"
                }).execute()

        ip  = geocoder.ip("me").ip or "unknown"
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        res = supabase.table("routes").insert({
            "name":        st.session_state["route_name"].strip(),
            "description": st.session_state["route_description"].strip(),
            "user_ip":     ip,
            "point_id_start": 2147483646,
            "point_id_end":   2147483647,
            "created_at": now,
        }).execute()
        if not res.data:
            st.error("Не удалось сохранить маршрут.")
            return

        route_id  = res.data[0]["id_route"]
        point_ids = []

        # добавляем реальные точки маршрута
        for i, pt in enumerate(st.session_state["free_points"]):
            ptype = "start" if i == 0 else "final" if i == 1 else "route"
            ins   = supabase.table("route_points").insert({
                "route_id":  route_id,
                "point_type": ptype,
                "lat": pt["coords"][0], "lon": pt["coords"][1],
                "description": pt["desc"] or ""
            }).execute()
            if ins.data:
                point_ids.append(ins.data[0]["id_point"])

        # обновляем ссылки на начало/конец, если есть ≥2 точек
        if len(point_ids) >= 2:
            supabase.table("routes").update({
                "point_id_start": point_ids[0],
                "point_id_end":   point_ids[1],
            }).eq("id_route", route_id).execute()

        st.success(f"Маршрут успешно добавлен (ID {route_id})")
        # очистка временных данных
        st.session_state["free_points"]       = []
        st.session_state["point_description"] = ""
        st.session_state["route_name"]        = ""
        st.session_state["route_description"] = ""
    except Exception as e:
        st.error(f"Ошибка при сохранении маршрута: {e}")

# ───────────────────────────────────────────────────────────
# main.py  (Part 2/4)
# ───────────────────────────────────────────────────────────
# ── Настройка страницы ─────────────────────────────────────
st.set_page_config(page_title="Виртуальный Экскурсовод", layout="wide")
st.title("🌏 Карта маршрута", anchor=False)

# ── Session State (общие + свободный режим) ───────────────
defaults = {
    "last_route_id":     None,
    "toggle_end":        False,
    "show_modal":        False,   # модалка «Создать маршрут»
    "show_complain":     False,
    "found_valid_route": False,
    "route_name":        None,
    "route_description": None,
    "point_description": None,
    # свободный режим
    "free_points":       [],
}
for k, v in defaults.items():
    st.session_state.setdefault(k, v)

# ── Панель поиска ID маршрута ─────────────────────────────
with st.container():
    st.markdown('<div style="height:20px"></div>', unsafe_allow_html=True)
    st.markdown('<h3 style="margin:0 0 .5em 0">🔎 ID маршрута</h3>', unsafe_allow_html=True)

    id_col, btn_col = st.columns([3, 1], gap="small")
    with id_col:
        st.text_input("route_id_input", placeholder="Введите ID маршрута",
                      label_visibility="collapsed", key="route_id")
    with btn_col:
        find_clicked = st.button("Найти", key="find_route",
                                 type="primary", use_container_width=True)

    # карта-заглушка, если маршрут ещё не выбран
    m = folium.Map(location=[0, 0], zoom_start=2, width="100%", height=500)

    # ── Поиск маршрута ────────────────────────────────────
    if find_clicked:
        rid = st.session_state.get("route_id")
        st.session_state["found_valid_route"] = False
        if rid:
            try:
                rid_int = int(rid)
                res     = supabase.table("routes").select("*") \
                          .eq("id_route", rid_int).execute()
                if res.data:
                    route = res.data[0]
                    st.session_state.update({
                        "found_valid_route": True,
                        "last_route_id":     rid_int,
                        "route_name":        route.get("name") or "Без названия",
                        "route_description": route.get("description") or "без описания",
                    })

                    start_id, end_id = route.get("point_id_start"), route.get("point_id_end")
                    points = []
                    if start_id:
                        sp = supabase.table("route_points").select("lat,lon,description") \
                             .eq("id_point", start_id).execute().data
                        if sp:
                            pt = sp[0]
                            points.append((pt["lat"], pt["lon"], "Начало маршрута",
                                           "purple", pt.get("description")))
                    if end_id:
                        ep = supabase.table("route_points").select("lat,lon,description") \
                             .eq("id_point", end_id).execute().data
                        if ep:
                            pt = ep[0]
                            points.append((pt["lat"], pt["lon"], "Конец маршрута",
                                           "orange", pt.get("description")))

                    # перерисовываем карту выбранного маршрута
                    if points:
                        m = folium.Map(location=points[0][:2], zoom_start=18,
                                       width="100%", height=500)
                        for lat, lon, tip, color, desc in points:
                            folium.Marker([lat, lon], tooltip=tip,
                                          icon=folium.Icon(color=color)).add_to(m)
                            if tip == "Начало маршрута":
                                st.session_state["point_description"] = desc or "без описания"

                    # промежуточные точки
                    all_pts = supabase.table("route_points").select("*") \
                              .eq("route_id", rid_int).eq("point_type", "route").execute().data
                    for pt in all_pts:
                        desc = (pt.get("description") or "без описания")[:100]
                        folium.CircleMarker([pt["lat"], pt["lon"]],
                                            radius=5, color="green", fill=True,
                                            fill_opacity=.9, tooltip=desc) \
                              .add_to(m)
                else:
                    st.warning("Маршрут не найден")
            except ValueError:
                st.warning("ID должен быть числом")
        else:
            st.warning("Введите ID маршрута")

    # ── Инфо о маршруте ──────────────────────────────────
    if st.session_state["found_valid_route"]:
        st.markdown(f"**Название маршрута:** {st.session_state['route_name']}")
        st.markdown(f"**Описание маршрута:** {st.session_state['route_description']}")
    else:
        st.markdown("**Маршрут не выбран**")

    # элементы управления картой
    LocateControl(auto_start=False, flyTo=True, position="bottomright").add_to(m)
    m.get_root().html.add_child(Element("""
        <style>
        .leaflet-control-attribution{display:none!important}
        .folium-map{padding:0!important;height:500px!important}
        </style>
    """))
    map_data = st_folium(m, width=700, height=500,
                         returned_objects=["last_clicked"])
    if map_data.get("last_clicked"):
        clat, clon = map_data["last_clicked"]["lat"], map_data["last_clicked"]["lng"]
        rid        = st.session_state.get("last_route_id")
        if rid:
            pts = supabase.table("route_points").select("*") \
                  .eq("route_id", rid).execute().data
            for pt in pts:
                if abs(pt["lat"]-clat) < .0001 and abs(pt["lon"]-clon) < .0001:
                    st.session_state["point_description"] = pt.get("description") or "без описания"
                    break

# ── Кнопки под картой ─────────────────────────────────────
sp_l, col_create, sp_c, col_my, sp_r, col_complain, sp_r2 = \
    st.columns([.5, 2, .5, 2, .5, 2, .5])

with col_create:
    if st.button("Создать маршрут", key="btn_create", type="secondary"):
        # чистим временные данные и открываем модалку
        st.session_state.update({
            "free_points":       [],
            "point_description": "",
            "route_name":        "",
            "route_description": "",
            "show_modal":        True,
        })

with col_my:
    if st.button("Мои маршруты", key="btn_my", type="secondary"):
        st.session_state["show_my_routes"] = True

with col_complain:
    if st.button("Пожаловаться", key="btn_complain", type="secondary",
                 disabled=not st.session_state["found_valid_route"]):
        st.session_state["show_complain"] = True

# ── Модалка «Создать маршрут» (Свободный режим) ───────────
if st.session_state["show_modal"]:
    st.markdown('<p style="font-size:1.6rem;font-weight:700;">'
                '🗘 Добавление карты</p>', unsafe_allow_html=True)

    modal_map = folium.Map(location=[55.75, 37.61],
                           zoom_start=14, width="100%", height=500)

    # существующие точки
    for i, pt in enumerate(st.session_state["free_points"]):
        txt   = pt["desc"] or "без описания"
        color = "#cc6600" if i == 0 else "purple" if i == 1 else "green"
        folium.CircleMarker(pt["coords"], radius=6,
                            color=color, fill=True, fill_color=color,
                            fill_opacity=.9, tooltip=txt[:100]).add_to(modal_map)

    modal_map.get_root().html.add_child(
        Element("<style>.leaflet-control-attribution{display:none!important}</style>"))
    md = st_folium(modal_map, key="modal_map", width=700, height=500,
                   returned_objects=["last_clicked"])

    # клик по модальной карте — добавление точки
    if md and md.get("last_clicked"):
        lat, lon = md["last_clicked"]["lat"], md["last_clicked"]["lng"]
        already  = any(abs(pt["coords"][0]-lat) < .0001 and
                       abs(pt["coords"][1]-lon) < .0001
                       for pt in st.session_state["free_points"])
        if not already:
            st.session_state["free_points"].append({
                "coords": [lat, lon],
                "desc":   st.session_state["point_description"].strip() or "без описания"
            })
            st.session_state["point_description"] = ""
            st.rerun()

    # кнопки «Добавить/Закрыть»
    cols = st.columns([1, 1, 6], gap="small")
    with cols[0]:
        if st.button("Добавить", key="add_route",
                     disabled=len(st.session_state["free_points"]) < 2):
            if not st.session_state["route_name"].strip():
                st.warning("Название маршрута не может быть пустым")
            else:
                save_route()
                st.session_state["show_modal"] = False
    with cols[1]:
        if st.button("Закрыть", key="close_free"):
            st.session_state["show_modal"]  = False
            st.session_state["free_points"] = []

    # поля ввода
    st.text_input("Описание точки", key="point_description",
                  label_visibility="collapsed",
                  placeholder="Описание точки", max_chars=128)
    st.text_input("Название маршрута", key="route_name",
                  placeholder="Название маршрута", max_chars=64)
    st.text_area("Описание маршрута", key="route_description",
                 height=120, placeholder="Описание маршрута", max_chars=512)

# ── Модалка «Жалоба» ──────────────────────────────────────
if st.session_state.get("show_complain") and st.session_state.get("last_route_id"):
    st.markdown(f"### 🤬 Пожаловаться на маршрут (ID {st.session_state['last_route_id']})")
    msg = st.text_area("Опишите проблему", key="complaint_text", height=100)

    cl, cr, _ = st.columns([1, 1, 3])
    with cl:
        if st.button("Отправить", key="submit_complaint"):
            if msg and msg.strip():
                try:
                    ip = geocoder.ip("me").ip or "unknown"
                    supabase.table("complaints").insert({
                        "route_id": st.session_state["last_route_id"],
                        "message":  msg.strip(),
                        "user_ip":  ip,
                    }).execute()
                    st.success("Ваша жалоба отправлена")
                    st.session_state["show_complain"] = False
                except Exception as e:
                    st.error(f"Ошибка при отправке жалобы: {e}")
            else:
                st.warning("Жалоба не может быть пустой")
    with cr:
        if st.button("Закрыть", key="cancel_complaint"):
            st.session_state["show_complain"] = False

# ── Секция «Мои маршруты» ─────────────────────────────────
if st.session_state.get("show_my_routes"):                 # ⇽⇽ NEW
    st.markdown("""
    <div style="font-size:1.8rem; font-weight:700; margin-bottom:0.5rem;">
    📍 Мои маршруты
    </div>
    """, unsafe_allow_html=True)

    try:
        ip = geocoder.ip("me").ip or "unknown"
        response = supabase.table("routes").select("id_route, name") \
                   .eq("user_ip", ip).order("created_at", desc=True).execute()
        routes = response.data

        if not routes:
            st.info("У вас пока нет сохранённых маршрутов")
        else:
            for route in routes:
                st.markdown(f"""
                    <div style="border-bottom:1px solid white; padding:0.5rem 0;">
                        <div style="font-weight:600;">
                            Название маршрута: {route['name']}
                        </div>
                        <div style="opacity:0.8;">
                            ID маршрута: {route['id_route']}
                        </div>
                    </div>
                """, unsafe_allow_html=True)
    except Exception as e:
        st.error(f"Ошибка при загрузке маршрутов: {e}")

# ── CSS (общее + модалки) ─────────────────────────────────

# ── CSS (общее + модалки) ─────────────────────────────────
st.markdown(r"""
<style>
/* Buttons (и в основной части, и в модалках) */
button[kind="primary"],
button[kind="secondary"],
button[kind="primary"]:disabled,
button[kind="secondary"]:disabled,
div.stButton > button{
    background:none!important;
    border:1px solid #fff!important;
    border-radius:0!important;
    color:#fff!important;
    padding:.35rem .9rem!important;
    font-size:.85rem!important;
    height:auto!important;
    width:auto!important;
    white-space:nowrap;
}
div.stButton > button:disabled{opacity:.5;cursor:not-allowed}

/* карты */
iframe[title="streamlit_folium.st_folium"]{
    height:500px!important;min-height:500px!important;
    margin-bottom:0!important;display:block;
}
div[data-testid="stVerticalBlock"]>div:has(iframe){
    padding:0!important;background:none!important;
}

/* input / textarea в модалке */
div[data-testid="stTextInput"],
div[data-testid="stTextArea"]{
    max-width:700px!important;width:700px!important;
    margin-bottom:1rem;
}
div[data-testid="stTextInput"] input,
div[data-testid="stTextArea"] textarea{
    width:100%!important;padding:.5rem .75rem!important;
    font-size:1rem!important;line-height:1.5rem!important;
    box-sizing:border-box!important;
}

/* колонка с кнопками в модалке */
div[data-testid="column"]{width:225px!important;min-width:200px!important}

/* Ctrl+Enter hint */
div[style*="Ctrl+Enter"]{display:none!important}

/* layout */
.block-container{padding:1rem 2rem;max-width:800px;margin:auto}
h1 a,h2 a,h3 a{display:none!important}
</style>
""", unsafe_allow_html=True)
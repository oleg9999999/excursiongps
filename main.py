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
import ipaddress


# Supabase
from supabase import create_client, Client

# 🔑 Подключение
url = "https://wqtpemsaxmanzxmdwhhp.supabase.co"
key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6IndxdHBlbXNheG1hbnp4bWR3aGhwIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDg0NTM2OTIsImV4cCI6MjA2NDAyOTY5Mn0.2pPOuHHX2XN0jXQtCTkoJsJ08qjZVJmDafEImZZvZ-k"
supabase: Client = create_client(url, key)



# ── 1. Получаем список IP/подсетей из таблицы blacklist ─────────────────────────
def load_blacklist() -> set[str]:
    """
    Возвращает множество записей из столбца user_ip:
    • поддерживает как одиночные IP («192.168.100.1»),
    • так и диапазоны в нотации CIDR («192.168.100.0/24»).
    """
    try:
        res = supabase.table("blacklist").select("user_ip").execute()
        return {row["user_ip"].strip() for row in res.data or []}
    except Exception as e:
        # если не удалось прочитать таблицу — лучше пустой блэклист,
        # чем заблокировать всех пользователей
        print(f"[warn] can't load blacklist: {e}")
        return set()

BLACKLIST = load_blacklist()

# ── 2. Проверяем IP клиента ─────────────────────────────────────────────────────
def client_ip() -> str | None:
    """
    Ваше текущее решение через geocoder остаётся рабочим,
    если приложение развёрнуто на машине-одиночке.
    Для продакшена на Streamlit Cloud / Render / Vercel
    понадобится передавать IP из JavaScript (fetch https://api.ipify.org)
    и класть его в st.session_state — по желанию.
    """
    return geocoder.ip("me").ip

def is_blocked(ip: str | None) -> bool:
    if not ip:
        return False   # пустые/неопределённые адреса пропускаем
    for banned in BLACKLIST:
        if "/" in banned:                   # CIDR-диапазон
            try:
                if ipaddress.ip_address(ip) in ipaddress.ip_network(banned, strict=False):
                    return True
            except ValueError:
                pass                         # некорректная запись в БД — игнорируем
        elif ip == banned:                   # точное совпадение
            return True
    return False

# ── 3. Если адрес в блэклисте — мгновенно останавливаем приложение ──────────────
if is_blocked(client_ip()):
    st.markdown("""
        <h2 style="color:#ff4d4f;text-align:center;margin-top:4rem;">
            🚫 Доступ запрещён
        </h2>
        <p style="text-align:center;">
            Ваш IP-адрес заблокирован администратором
        </p>
    """, unsafe_allow_html=True)
    st.stop()




# ── Функция сохранения маршрута (для «Свободного режима») ────────────────────────
def save_route() -> None:
    """Сохраняет новый маршрут из st.session_state.free_points."""
    try:
        ip  = geocoder.ip("me").ip or "unknown"
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        res = supabase.table("routes").insert({
            "name":        st.session_state["route_name"].strip(),
            "description": st.session_state["route_description"].strip(),
            "user_ip":     ip,
            "created_at":  now,
        }).execute()
        if not res.data:
            st.error("Не удалось сохранить маршрут.")
            return

        route_id  = res.data[0]["id_route"]
        point_ids = []

        # добавляем реальные точки маршрута
        for i, pt in enumerate(st.session_state["free_points"]):
            ptype = "start" if i == 0 else "final" if i == 1 else "route"
            raw_desc = pt["desc"].strip() if pt["desc"] else ""

            if ptype == "start":
                desc = f"Начало маршрута. {raw_desc}" if raw_desc else "Начало маршрута."
            elif ptype == "final":
                desc = f"Конец маршрута. {raw_desc}" if raw_desc else "Конец маршрута."
            else:
                desc = raw_desc or "Без описания"

            ins = supabase.table("route_points").insert({
                "route_id":   route_id,
                "point_type": ptype,
                "lat":        pt["coords"][0],
                "lon":        pt["coords"][1],
                "description": desc
            }).execute()
            if ins.data:
                point_ids.append(ins.data[0]["id_point"])

        # сообщение об успехе
        st.markdown(f"""
            <div class="success-message">
                Маршрут успешно добавлен&nbsp;(ID&nbsp;{route_id})
            </div>
        """, unsafe_allow_html=True)

        # очистка временных данных
        st.session_state["free_points"]       = []
        st.session_state["point_description"] = ""
        st.session_state["route_name"]        = ""
        st.session_state["route_description"] = ""

    except Exception as e:
        st.error(f"Ошибка при сохранении маршрута: {e}")

# ── Настройка страницы ─────────────────────────────────────

st.set_page_config(page_title="Виртуальный Путеводитель", layout="wide")
st.title("🌏 Виртуальный Путеводитель", anchor=False)

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
    "free_points":       []
}
for k, v in defaults.items():
    st.session_state.setdefault(k, v)

# ── Панель поиска ID маршрута ─────────────────────────────
with st.container():
    st.markdown('<div style="height:20px"></div>', unsafe_allow_html=True)
    st.markdown('<h3 style="margin:1.5rem 0 .375em 0">🔎 Поиск маршрута</h3>', unsafe_allow_html=True)

    id_col, col_id, col_word = st.columns([2, 1, 1], gap="small")

    with id_col:
        st.text_input(
            "route_id_input",
            placeholder="Введите ID маршрута или ключевое слово",
            label_visibility="collapsed",
            key="route_id"
        )

    with col_id:
        find_by_id = st.button("Найти по ID", key="find_by_id", type="primary")

    with col_word:
        find_by_word = st.button("Найти по слову", key="find_by_word", type="primary")

    # убираем промежуток между колонками — «слипаем» поле и кнопку
    st.markdown(
        """
        <style>
        div[data-testid="stHorizontalBlock"] > div:first-child{padding-right:0!important;}
        div[data-testid="stHorizontalBlock"] > div:first-child + div{padding-left:0!important;}
        </style>
        """,
        unsafe_allow_html=True,
    )

    # карта-заглушка, если маршрут ещё не выбран
    m = folium.Map(location=[46.3381433785881, 48.0677175521851], zoom_start=2, width="100%", height=500)

    # ── Поиск маршрута ────────────────────────────────────
    rid = st.session_state.get("route_id", "").strip()
    st.session_state["found_valid_route"] = False

    if find_by_id:
        if rid:
            try:
                rid_int = int(rid)
                res = supabase.table("routes").select("*") \
                    .eq("id_route", rid_int).execute()
                if res.data:
                    route = res.data[0]
                    st.session_state.update({
                        "found_valid_route": True,
                        "last_route_id": rid_int,
                        "route_name": route.get("name") or "Без названия",
                        "route_description": route.get("description") or "Без описания",
                    })

                    points = []

                    start_pts = supabase.table("route_points").select("lat,lon,description") \
                        .eq("route_id", rid_int).eq("point_type", "start").execute().data
                    if start_pts:
                        pt = start_pts[0]
                        points.append((pt["lat"], pt["lon"], "Начало маршрута", "purple", pt.get("description")))

                    final_pts = supabase.table("route_points").select("lat,lon,description") \
                        .eq("route_id", rid_int).eq("point_type", "final").execute().data
                    if final_pts:
                        pt = final_pts[0]
                        points.append((pt["lat"], pt["lon"], "Конец маршрута", "orange", pt.get("description")))

                    # перерисовываем карту выбранного маршрута
                    if points:
                        m = folium.Map(location=points[0][:2], zoom_start=18,
                                       width="100%", height=500)
                        for lat, lon, tip, color, desc in points:
                            tooltip_text = desc.strip() if desc else tip
                            folium.Marker(
                                [lat, lon],
                                tooltip=tooltip_text,
                                icon=folium.Icon(color=color)
                            ).add_to(m)
                            if tip == "Начало маршрута":
                                st.session_state["point_description"] = desc or ". Без описания"

                    # промежуточные точки
                    all_pts = supabase.table("route_points").select("*") \
                        .eq("route_id", rid_int).eq("point_type", "route").execute().data
                    for pt in all_pts:
                        desc = pt.get("description", "").strip() or "Без описания"
                        desc = desc[:100]
                        folium.CircleMarker([pt["lat"], pt["lon"]],
                                            radius=5, color="green", fill=True,
                                            fill_opacity=.9, tooltip=desc) \
                            .add_to(m)
                else:
                    with id_col:
                        st.markdown("""
                        <div style="
                            color:#f9c74f;
                            background:#3b3b1b;
                            padding:0.5rem 1rem;
                            border-radius:8px;
                            width:170px;
                            white-space:nowrap;
                            font-size:1rem;
                            margin-top:0.5rem;
                            margin-bottom:1rem;
                        ">
                        Маршрут не найден
                        </div>
                        """, unsafe_allow_html=True)
            except ValueError:
                with id_col:
                    st.markdown("""
                    <div style="
                        color:#f9c74f;
                        background:#3b3b1b;
                        padding:0.5rem 1rem;
                        border-radius:8px;
                        width:fit-content;
                        white-space:nowrap;
                        font-size:1rem;
                        margin:6px 0;
                    ">
                    Введите ID маршрута
                    </div>
                    """, unsafe_allow_html=True)
        else:
            with id_col:
                st.markdown("""
                <div style="
                    color:#f9c74f;
                    background:#3b3b1b;
                    padding:0.5rem 1rem;
                    border-radius:8px;
                    width:fit-content;
                    white-space:nowrap;
                    font-size:1rem;
                    margin:6px 0;
                ">
                Введите ID маршрута
                </div>
                """, unsafe_allow_html=True)

    elif find_by_word:
        if rid:
            # всё приводим к ВЕРХНЕМУ регистру
            search_word = rid.upper()

            # ищем совпадение либо в name, либо в description
            # (ILIKE – регистронезависимый, но делаем upper() «для верности»)
            res = supabase.table("routes") \
                .select("id_route, name, description") \
                .or_(f"name.ilike.*{search_word}*,description.ilike.*{search_word}*") \
                .execute()

            # кладём результат в session_state, чтобы отрисовать блок ниже
            st.session_state["keyword_results"] = {
                "word": search_word,
                "routes": res.data or []
            }
        else:
            # если поле было пустым – всё по-старому
            with id_col:
                st.markdown("""
                <div style="
                    color:#f9c74f;
                    background:#3b3b1b;
                    padding:0.5rem 1rem;
                    border-radius:8px;
                    width:fit-content;
                    font-size:1rem;
                    margin:6px 0;
                ">
                Введите клюечвое слово
                </div>
                """, unsafe_allow_html=True)
            # стираем предыдущие результаты, если были
            st.session_state.pop("keyword_results", None)

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
                    st.session_state["point_description"] = pt.get("description", "").strip() or "Без описания"
                    break

# ── Блок «Маршруты по ключевому слову …» ────────────────────────────────────────

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
    st.markdown("""
        <div style="margin-top:2.5rem;">
            <p style="font-size:1.6rem;font-weight:700;">
                🗺️ Добавление маршрута
            </p>
        </div>
    """, unsafe_allow_html=True)

    modal_map = folium.Map(location=[46.3381433785881, 48.0677175521851],
                           zoom_start=14, width="100%", height=500)

    LocateControl(auto_start=False, flyTo=True, position="bottomright").add_to(modal_map)

    # существующие точки
    for i, pt in enumerate(st.session_state["free_points"]):
        raw_desc = pt["desc"].strip() if pt["desc"] else ""
        color = "purple" if i == 0 else "#cc6600" if i == 1 else "green"

        if i == 0:
            tooltip_text = f"Начало маршрута. {raw_desc}" if raw_desc else "Начало маршрута."
        elif i == 1:
            tooltip_text = f"Конец маршрута. {raw_desc}" if raw_desc else "Конец маршрута."
        else:
            tooltip_text = raw_desc or "Без описания"

        folium.CircleMarker(
            pt["coords"],
            radius=6,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=.9,
            tooltip=tooltip_text[:100]
        ).add_to(modal_map)

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
                "desc":   st.session_state["point_description"].strip() or "Без описания"
            })
            st.session_state["point_description"] = ""
            st.rerun()

    # кнопки «Откатить/Добавить/Закрыть»
    sp_l, col_back, sp_c, col_add, sp_r, col_close, sp_r2 = st.columns([1, 2, .5, 2, .5, 2, 1])

    with col_back:
        if st.button("Шаг назад", key="undo_point", type="secondary", disabled=not st.session_state["free_points"]):
            st.session_state["free_points"].pop()
            st.rerun()

    with col_add:
        if st.button("Добавить", key="add_route",
                     disabled=len(st.session_state["free_points"]) < 2):
            if not st.session_state["route_name"].strip():
                st.markdown("""<div style="color:#f9c74f;background:#3b3b1b;padding:0.5rem 1rem;
                                border-radius:8px;width:335px;white-space:nowrap;
                                font-size:1rem;margin:.5rem 0 1rem 0;">
                                Название маршрута не может быть пустым
                               </div>""", unsafe_allow_html=True)
            else:
                save_route()
                st.session_state["show_modal"] = False

    with col_close:
        if st.button("Закрыть", key="close_free"):
            st.session_state["show_modal"] = False
            st.session_state["free_points"] = []

    st.text_input("Описание точки", key="point_description",
                  placeholder="Описание точки", max_chars=128)
    st.text_input("Название маршрута", key="route_name",
                  placeholder="Название маршрута", max_chars=64)
    st.text_area("Описание маршрута", key="route_description",
                 height=120, placeholder="Описание маршрута", max_chars=512)

# ── Модалка «Жалоба» ──────────────────────────────────────
if st.session_state.get("show_complain") and st.session_state.get("last_route_id"):
    st.markdown(f"### 🤬 Пожаловаться на маршрут (ID {st.session_state['last_route_id']})")
    msg = st.text_area("Опишите проблему", key="complaint_text", height=100)

    sp_l, col_send, sp_c, col_cancel, sp_r = st.columns([2, 2, 1, 2, 2])
    with col_send:
        if st.button("Отправить", key="submit_complaint"):
            if msg and msg.strip():
                try:
                    ip = geocoder.ip("me").ip or "unknown"
                    supabase.table("complaints").insert({
                        "route_id": st.session_state["last_route_id"],
                        "message":  msg.strip(),
                        "user_ip":  ip,
                    }).execute()
                    st.markdown("""
                    <div style="
                        color:#90ee90;
                        background:#1e3d2f;
                        padding:0.5rem 1rem;
                        border-radius:8px;
                        width:212px;
                        white-space:nowrap;
                        font-size:1rem;
                    ">
                    Ваша жалоба отправлена
                    </div>
                    """, unsafe_allow_html=True)
                    st.session_state["show_complain"] = False
                except Exception as e:
                    st.error(f"Ошибка при отправке жалобы: {e}")
            else:
                st.markdown("""
                <div style="
                    color:#f9c74f;
                    background:#3b3b1b;
                    padding:0.5rem 1rem;
                    border-radius:8px;
                    width:243px;
                    white-space:nowrap;
                    font-size:1rem;
                ">
                Жалоба не может быть пустой
                </div>
                """, unsafe_allow_html=True)
    with col_cancel:
        if st.button("Закрыть", key="cancel_complaint"):
            st.session_state["show_complain"] = False

# ── Секция «Мои маршруты» ─────────────────────────────────
if st.session_state.get("show_my_routes"):
    st.markdown("""
    <div style="margin-top:2.5rem; font-size:1.8rem; font-weight:700; margin-bottom:0.5rem;">
        🚶 Мои маршруты
    </div>
    """, unsafe_allow_html=True)

    try:
        ip = geocoder.ip("me").ip or "unknown"
        response = supabase.table("routes").select("id_route, name, description") \
            .eq("user_ip", ip).order("created_at", desc=True).execute()
        routes = response.data

        if not routes:
            st.markdown("""
            <div style="
                color: #cfe5f3;
                background-color: #3A3AEB;
                padding: 0.5rem 1rem;
                border-radius: 8px;
                width: fit-content;
                white-space: nowrap;
                font-size: 1rem;
                margin: 6px 0;
            ">
            У вас нет сохранённых маршрутов
            </div>
            """, unsafe_allow_html=True)
        else:
            st.session_state.setdefault("deleted_route_ids", set())

            for route in routes:
                route_id = route["id_route"]

                # Блок маршрута
                with st.container():
                    st.markdown(f"""
                        <div style="color:#fff; margin-bottom:0.25rem;">
                            Название маршрута: {route['name']}
                        </div>
                        <div style="color:#fff; margin-bottom:0.25rem;">
                            Описание маршрута: {route['description'] or "без описания"}
                        </div>
                        <div style="color:#fff; margin-bottom:0.75rem;">
                            ID маршрута: {route_id}
                        </div>
                    """, unsafe_allow_html=True)

                    # Кнопка «Удалить»
                    if route_id not in st.session_state["deleted_route_ids"]:
                        if st.button("Удалить", key=f"delete_{route_id}"):
                            try:
                                res = supabase.table("routes").delete().eq("id_route", route_id).execute()
                                if res.data:
                                    st.markdown(f"""
                                    <div style="
                                        color:#90ee90;
                                        background:#1c3b2f;
                                        padding:0.45rem 0.75rem;
                                        border-radius:6px;
                                        width:fit-content;
                                        max-width:260px;
                                        font-size:0.95rem;
                                        line-height:1.45rem;  
                                        margin:3px 0 4px 0;
                                    ">
                                    Маршрут с ID {route_id} удалён
                                    </div>
                                    """, unsafe_allow_html=True)
                                    st.session_state["deleted_route_ids"].add(route_id)
                                else:
                                    st.warning(f"Маршрут с ID {route_id} уже отсутствует")
                            except Exception as e:
                                st.error(f"Ошибка при удалении: {e}")

                    # Полоса + отступ вниз
                    st.markdown("""
                        <div style="border-bottom:1px solid white; margin:0.5rem 0 1.25rem 0;"></div>
                    """, unsafe_allow_html=True)


    except Exception as e:
        st.error(f"Ошибка при загрузке маршрутов: {e}")



# ── Блок «Маршруты по ключевому слову …» ────────────────────────────────────────
if st.session_state.get("keyword_results") is not None:
    kw_data = st.session_state["keyword_results"]
    kw      = kw_data["word"]          # слово, которым искали (уже верхний регистр)
    routes  = kw_data["routes"]

    st.markdown(f"""
        <div style="margin-top:2.5rem;
                    font-size:1.8rem;
                    font-weight:700;
                    margin-bottom:0.5rem;">
            🔍 Маршруты по ключевому слову "{kw}"
        </div>
    """, unsafe_allow_html=True)

    if not routes:
        st.markdown("""
        <div style="
        color: #cfe5f3;
        background-color: #3A3AEB;
            padding:0.5rem 1rem;
            border-radius:8px;
            width:fit-content;
            white-space:nowrap;
            font-size:1rem;
            margin:6px 0;
        ">
        Совпадений не найдено
        </div>
        """, unsafe_allow_html=True)
    else:
        for r in routes:
            with st.container():
                st.markdown(f"""
                    <div style="color:#fff; margin-bottom:0.25rem;">
                        Название маршрута: {r['name']}
                    </div>
                    <div style="color:#fff; margin-bottom:0.25rem;">
                        Описание маршрута: {r['description'] or "без описания"}
                    </div>
                    <div style="color:#fff; margin-bottom:0.75rem;">
                        ID маршрута: {r['id_route']}
                    </div>
                """, unsafe_allow_html=True)

                # белая разделительная полоса
                st.markdown("""
                    <div style="border-bottom:1px solid white;
                                margin:0.5rem 0 1.25rem 0;"></div>
                """, unsafe_allow_html=True)


# ── CSS (общее + модалки) ─────────────────────────────────
st.markdown(r"""
<style>
/* ─────────── Кнопки ─────────── */
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

/* ─────────── Карты ─────────── */
iframe[title="streamlit_folium.st_folium"]{
    height:500px!important;min-height:500px!important;
    margin-bottom:0!important;display:block;
}
div[data-testid="stVerticalBlock"]>div:has(iframe){
    padding:0!important;background:none!important;
}

/* ─────────── Размеры input / textarea ─────────── */
/* (1) Узкое поле поиска (первый столбец в горизонтальном блоке) */
div[data-testid="stHorizontalBlock"] > div:first-child div[data-testid="stTextInput"]{
    max-width:325px !important;
    width:325px !important;
}

/* (2) Все остальные text_input + text_area — 700 px */
div[data-testid="stTextInput"],
div[data-testid="stTextArea"]{
    max-width:700px !important;
    width:700px !important;
}

/* (3) Внутренние <input>/<textarea> растягиваем на всю ширину контейнера */
div[data-testid="stTextInput"] input,
div[data-testid="stTextArea"] textarea{
    width:100% !important;
    padding:0.5rem 0.75rem !important;
    font-size:1rem !important;
    line-height:1.5rem !important;
    box-sizing:border-box !important;
}

/* ─────────── Колонки с кнопками в модалке ─────────── */
div[data-testid="column"]{
    width:auto!important;
    min-width:auto!important;
}

/* ─────────── Прочее ─────────── */
div[style*="Ctrl+Enter"]{display:none!important}

.block-container{
    padding:4rem 2rem 1rem 2rem;      /* сверху 4rem, снизу 1rem */
    max-width:800px;
    margin:auto;
}
h1 a,h2 a,h3 a{display:none!important}

div.success-message{
    color:#90ee90;
    background:#1c3b2f;
    padding:0.5rem 1rem;
    border-radius:8px;
    width:fit-content;
    white-space:nowrap;
    font-size:1rem;
    margin:3px 0 4px 0;
}

/* лёгкий сдвиг двух кнопок «Найти» вправо */
div[data-testid="stHorizontalBlock"] > div:nth-child(2){margin-left:15px!important;}
div[data-testid="stHorizontalBlock"] > div:nth-child(3){margin-left:-10px!important;}
</style>
""", unsafe_allow_html=True)
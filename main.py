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



# Основное
import streamlit as st
import json
import geocoder
import folium
from streamlit_folium import st_folium
from branca.element import Element, MacroElement
from jinja2 import Template
from pathlib import Path

# Supabase
from supabase import create_client, Client

# 🔑 Подключение
url = "https://wqtpemsaxmanzxmdwhhp.supabase.co"
key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6IndxdHBlbXNheG1hbnp4bWR3aGhwIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDg0NTM2OTIsImV4cCI6MjA2NDAyOTY5Mn0.2pPOuHHX2XN0jXQtCTkoJsJ08qjZVJmDafEImZZvZ-k"
supabase: Client = create_client(url, key)


# ── Streamlit конфиг ─────────────────────────────
st.set_page_config(page_title="Виртуальный Экскурсовод", layout="wide")
st.title("🗺️ Карта маршрута", anchor=False)

# ── Определяем координаты пользователя ───────────
g = geocoder.ip("me")
user_latlon = g.latlng if g.ok else [55.75, 37.61]

# ── Leaflet-контрол с маленьким SVG 24 × 24 ──────
class GpsControl(MacroElement):
    """Маленькая кнопка GPS в правом-нижнем углу."""

    def __init__(self, lat: float, lon: float, svg_path: str = "gps.svg"):
        super().__init__()
        self._name = "GpsControl"
        self.lat, self.lon = lat, lon
        self.svg = Path(svg_path).read_text(encoding="utf-8")

        self._template = Template(u"""
    {% macro script(this, kwargs) %}
    (function () {
      var lat={{ this.lat }}, lon={{ this.lon }};
      var svg=`{{ this.svg|safe }}`;

      var Btn = L.Control.extend({
        onAdd: function (map) {
          // ⬇️  ОБРАТИТЕ ВНИМАНИЕ: второй аргумент '' — БЕЗ leaflet-bar
          var el = L.DomUtil.create('div', '');
          Object.assign(el.style, {
            width   : '30px',
            height  : '30px',
            display : 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            cursor  : 'pointer',
            background: 'transparent',   // ← для надёжности
          });

          el.innerHTML = svg;
          L.DomEvent.disableClickPropagation(el);
          el.onclick = () => map.flyTo([lat, lon], 15);
          return el;
        }
      });
      new Btn({position: 'bottomright'}).addTo({{ this._parent.get_name() }});
    })();
    {% endmacro %}
    """)


# ── Создаём карту ────────────────────────────────
m = folium.Map(location=user_latlon, zoom_start=13)
m.add_child(GpsControl(user_latlon[0], user_latlon[1]))

# ── Пульсирующая синяя точка ─────────────────────
pulse_html = """
<div class="pulse-marker"></div>
<style>
.pulse-marker{
  width:14px;height:14px;
  background:rgba(0,119,255,.9);
  border:2px solid #0066ff;border-radius:50%;
  box-shadow:0 0 6px #00aaff;
  animation:pulse 1.2s infinite;
}
@keyframes pulse{
  0%{box-shadow:0 0 4px #00aaff;}
 50%{box-shadow:0 0 10px #00aaff;}
100%{box-shadow:0 0 4px #00aaff;}
}
</style>
"""
folium.Marker(location=user_latlon,
              icon=folium.DivIcon(html=pulse_html),
              tooltip="Вы здесь").add_to(m)


m.get_root().html.add_child(folium.Element("""
<style>
/* Вырубаем фильтр и анимацию у любых <img> внутри карты */
html[data-theme="dark"] .leaflet-container img {
    filter: none !important;
    transition: none !important;
}
/* Убираем копирайт Leaflet */
.leaflet-control-attribution {
    display: none !important;
}
</style>

<script>
navigator.geolocation.getCurrentPosition(function(pos) {
    const lat = pos.coords.latitude;
    const lon = pos.coords.longitude;

    // Панорамируем карту
    map.setView([lat, lon], 15);

    // Добавим маркер
    L.marker([lat, lon]).addTo(map).bindPopup("Вы здесь").openPopup();
});
</script>
"""))


# ── Показываем карту ─────────────────────────────
st_folium(m,
          width=700,
          height=500,
          returned_objects=[]   # <- никаких данных ⇒ нет ререндеров
)

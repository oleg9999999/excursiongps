from supabase import create_client, Client

# Подключение к Supabase
url = "https://wqtpemsaxmanzxmdwhhp.supabase.co"
key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6IndxdHBlbXNheG1hbnp4bWR3aGhwIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDg0NTM2OTIsImV4cCI6MjA2NDAyOTY5Mn0.2pPOuHHX2XN0jXQtCTkoJsJ08qjZVJmDafEImZZvZ-k"
supabase: Client = create_client(url, key)

def add_training_data():

    # 1. Вставка маршрутов
    routes_data = [
        {
            "name": "Маршрут у Красной площади",
            "description": "Пешая прогулка по историческому центру",
            "user_ip": "192.168.0.1"
        },
        {
            "name": "Без описания",
            "description": "",
            "user_ip": "192.168.0.2"
        },
        {
            "name": "Переход через парк Зарядье",
            "description": "Маршрут через смотровую площадку и мост",
            "user_ip": "192.168.0.3"
        },
    ]

    try:
        response = supabase.table("routes").insert(routes_data).execute()
        inserted_routes = response.data
        print("✅ Маршруты добавлены")
    except Exception as e:
        print("⚠️ Ошибка при добавлении маршрутов:", str(e))
        exit()

    for idx, route in enumerate(inserted_routes):
        route_id = route["id_route"]

        if idx == 0:
            start = {"route_id": route_id, "point_type": "start", "lat": 55.753930, "lon": 37.620795,
                     "description": "Начало маршрута на Красной площади"}
            end = {"route_id": route_id, "point_type": "final", "lat": 55.752023, "lon": 37.617499, "description": ""}
        elif idx == 1:
            start = {"route_id": route_id, "point_type": "start", "lat": 55.760186, "lon": 37.618711, "description": ""}
            end = {"route_id": route_id, "point_type": "final", "lat": 55.759001, "lon": 37.621951,
                   "description": "Финиш у Манежной площади"}
        else:
            start = {"route_id": route_id, "point_type": "start", "lat": 55.750226, "lon": 37.627186,
                     "description": "Вход в парк Зарядье"}
            end = {"route_id": route_id, "point_type": "final", "lat": 55.748710, "lon": 37.629833, "description": ""}

        try:
            point_start = supabase.table("route_points").insert(start).execute().data[0]
            point_end = supabase.table("route_points").insert(end).execute().data[0]

            supabase.table("routes").update({
                "point_id_start": point_start["id_point"],
                "point_id_end": point_end["id_point"]
            }).eq("id_route", route_id).execute()

            # Добавление промежуточных точек (только в первых 2 маршрутах)
            if idx < 2:
                lat1, lon1 = start["lat"], start["lon"]
                lat2, lon2 = end["lat"], end["lon"]
                n = 8  # число точек

                for i in range(1, n + 1):
                    frac = i / (n + 1)
                    lat = lat1 + (lat2 - lat1) * frac
                    lon = lon1 + (lon2 - lon1) * frac

                    desc = ""  # нечётная точка — без описания
                    if i % 2 == 0:
                        desc = f"Описание точки {i} АААААААААААААА ЧТО ЧТО? ЗДЕСЬ ОГРОМНЫЙ СЛОН ЗДЕСЬ ОГРОМНЫЙ СЛОН"

                    supabase.table("route_points").insert({
                        "route_id": route_id,
                        "point_type": "route",
                        "lat": lat,
                        "lon": lon,
                        "description": desc
                    }).execute()

            print(f"✅ Точки маршрута {route_id} добавлены")
        except Exception as e:
            print(f"⚠️ Ошибка при вставке точек маршрута {route_id}: {e}")

    complaints_data = [
        {"user_ip": "192.168.1.100", "route_id": inserted_routes[0]["id_route"], "message": "Тестовая жалоба 1"},
        {"user_ip": "192.168.1.101", "route_id": inserted_routes[0]["id_route"], "message": "Тестовая жалоба 2"},
        {"user_ip": "192.168.1.102", "route_id": inserted_routes[1]["id_route"], "message": "Тестовая жалоба 3"},
        {"user_ip": "192.168.1.103", "route_id": inserted_routes[1]["id_route"], "message": "Тестовая жалоба 4"},
        {"user_ip": "192.168.1.104", "route_id": inserted_routes[2]["id_route"], "message": "Тестовая жалоба 5"},
    ]
    try:
        supabase.table("complaints").insert(complaints_data).execute()
        print("✅ Жалобы добавлены")
    except Exception as e:
        msg = str(e)
        print("⚠️ Ошибка при добавлении жалоб:", msg)

    blacklist_data = [
        {"user_ip": "192.168.100.1"},
        {"user_ip": "192.168.100.2"},
        {"user_ip": "192.168.100.3"},
        {"user_ip": "192.168.100.4"},
        {"user_ip": "192.168.100.5"},
    ]
    try:
        supabase.table("blacklist").insert(blacklist_data).execute()
        print("✅ IP-адреса добавлены в чёрный список")
    except Exception as e:
        msg = str(e)
        if "violates unique constraint" in msg:
            print("⚠️ Тренировочные строки с IP-адресами в чёрном списке уже присутствуют")
        else:
            print("⚠️ Ошибка при добавлении IP:", msg)

def delete_training_data():
    for i in range(1, 6):
        supabase.table("complaints").delete().eq("message", f"Тестовая жалоба {i}").execute()

    for i in range(1, 6):
        supabase.table("blacklist").delete().eq("user_ip", f"192.168.100.{i}").execute()

    # Удаление маршрутов с описаниями "Маршрут 1", "Маршрут 2", "Маршрут 3"
    for i in range(1, 4):
        supabase.table("routes").delete().eq("description", f"Маршрут {i}").execute()

    # Удаление маршрутов, добавленных вручную с IP 192.168.0.2
    supabase.table("routes").delete().eq("user_ip", "192.168.0.2").execute()




    print("🗑 Тренировочные данные удалены")

def delete_all_data():
    tables = {
        "complaints": "id_complaint",
        "blacklist": "user_ip",
        "route_points": "id_point",
        "routes": "id_route"
    }

    for table, column in tables.items():
        try:
            supabase.table(table).delete().gte(column, 0).execute()
        except Exception as e:
            print(f"⚠️ Ошибка при удалении из таблицы {table}: {e}")

    print("🗑 Все данные из всех таблиц удалены")

def read_complaints():
    while True:
        result = supabase.table("complaints").select("*").order("id_complaint").limit(1).execute()
        complaints = result.data

        if not complaints:
            print("🤷 Жалоб нет в базе данных")
            break

        complaint = complaints[0]
        user_ip = complaint["user_ip"]
        route_id = complaint["route_id"]
        message = complaint["message"]

        print(f"\nIP пользователя: {user_ip}\nID маршрута: {route_id}\nСообщение: {message}")

        print("\nВведите номер действия, которое вы хотите совершить")
        print("1. Удалить жалобу. Прочесть следующую жалобу")
        print("2. Удалить жалобу и выйти в главное меню")
        print("3. Прочесть все жалобы данного пользователя")
        print("4. Выйти в главное меню")

        sub_choice = input("→ Ваш выбор: ")

        if sub_choice == "1":
            supabase.table("complaints").delete().eq("id_complaint", complaint["id_complaint"]).execute()
            print("✅ Жалоба удалена")
        elif sub_choice == "2":
            supabase.table("complaints").delete().eq("id_complaint", complaint["id_complaint"]).execute()
            print("✅ Жалоба удалена")
            break
        elif sub_choice == "3":
            user_complaints = supabase.table("complaints").select("*").eq("user_ip", user_ip).execute().data
            print(f"\nЖалобы от пользователя с IP-адресом {user_ip}:")
            for c in user_complaints:
                print(f"💬 {c['message']}")

            print("\n1. Удалить жалобы пользователя и прочесть жалобы следующего пользователя")
            print("2. Удалить жалобы пользователя и выйти в главное меню")
            print("3. Удалить жалобы пользователя и забанить его. Прочесть следующую жалобу")
            print("4. Удалить жалобы пользователя и забанить его. Выйти в главное меню")
            print("5. Выйти в главное меню")
            sub2_choice = input("→ Ваш выбор: ")

            if sub2_choice in ["1", "2", "3", "4"]:
                supabase.table("complaints").delete().eq("user_ip", user_ip).execute()
                if sub2_choice in ["3", "4"]:
                    supabase.table("blacklist").insert({"user_ip": user_ip}).execute()
                    print("⛔ Пользователь забанен")
                print("🗑 Жалобы пользователя удалены")
                if sub2_choice in ["2", "4"]:
                    break
            elif sub2_choice == "5":
                break  # <-- ВЫХОД В ГЛАВНОЕ МЕНЮ

            print("\n1. Удалить жалобы пользователя и прочесть жалобы следующего пользователя")
            print("2. Удалить жалобы пользователя и выйти в главное меню")
            print("3. Удалить жалобы пользователя и забанить его. Прочесть следующую жалобу")
            print("4. Удалить жалобы пользователя и забанить его. Выйти в главное меню")
            print("5. Выйти в главное меню")
            sub2_choice = input("→ Ваш выбор: ")

            if sub2_choice in ["1", "2", "3", "4"]:
                supabase.table("complaints").delete().eq("user_ip", user_ip).execute()
                if sub2_choice in ["3", "4"]:
                    supabase.table("blacklist").insert({"user_ip": user_ip}).execute()
                    print("⛔ Пользователь забанен")
                print("🗑 Жалобы пользователя удалены")
                if sub2_choice in ["2", "4"]:
                    break
        elif sub_choice == "4":
            break
        else:
            print("❌ Неверный ввод. Попробуйте снова")

def add_ip_to_blacklist():
    ip = input("Введите IP-адрес пользователя, которого нужно забанить: ")
    try:
        supabase.table("blacklist").insert({"user_ip": ip}).execute()
        print(f"⛔ Пользователь с IP-адресом {ip} добавлен в чёрный список")
    except Exception as e:
        msg = str(e)
        if "violates unique constraint" in msg:
            print("⚠️ Пользователь уже в чёрном списке")
        else:
            print("⚠️ Ошибка при добавлении:", msg)


def remove_ip_from_blacklist():
    ip = input("Введите IP-адрес пользователя, которого нужно удалить из чёрного списка: ")
    try:
        # Проверка наличия IP в чёрном списке
        result = supabase.table("blacklist").select("user_ip").eq("user_ip", ip).execute()
        if not result.data:
            print(f"⚠️ Пользователь с IP {ip} не найден в чёрном списке")
            return

        # Удаление, если найден
        supabase.table("blacklist").delete().eq("user_ip", ip).execute()
        print(f"🕊️ Пользователь с IP {ip} удалён из чёрного списка")
    except Exception as e:
        print("⚠️ Ошибка при удалении:", str(e))

def remove_route_by_id():
    try:
        route_id = int(input("Введите ID маршрута: "))
    except ValueError:
        print("❌ Некорректный ввод. ID маршрута должен быть числом")
        return

    try:
        # Проверка существования маршрута
        result = supabase.table("routes").select("id_route").eq("id_route", route_id).execute()
        if not result.data:
            print(f"⚠️ Маршрут с ID {route_id} не найдён в базе данных")
            return

        # Удаление маршрута
        supabase.table("routes").delete().eq("id_route", route_id).execute()
        print(f"🗑 Маршрут с ID {route_id} удалён")
    except Exception as e:
        print("⚠️ Ошибка при удалении маршрута:", str(e))


# Меню
print("\n👑 ДОБРО ПОЖАЛОВАТЬ В ПАНЕЛЬ АДМИНИСТРАТОРА 👑")
while True:
    print("\nКАКИЕ ДЕЙСТВИЯ ВЫ ХОТИТЕ СОВЕРШИТЬ? ВВЕДИТЕ НОМЕР")
    print("1. Добавить тренировочные данные")
    print("2. Удалить тренировочные данные")
    print("3. Удалить все данные с таблиц")
    print("4. Прочесть жалобы")
    print("5. Удалить маршрут")
    print("6. Добавить пользователя в чёрный список")
    print("7. Удалить пользователя из чёрного списка")
    print("8. Выйти из главного меню")

    choice = input("→ Ваш выбор: ")

    if choice == "1":
        add_training_data()
    elif choice == "2":
        delete_training_data()
    elif choice == "3":
        delete_all_data()
    elif choice == "4":
        read_complaints()
    elif choice == "5":
        remove_route_by_id()
    elif choice == "6":
        add_ip_to_blacklist()
    elif choice == "7":
        remove_ip_from_blacklist()
    elif choice == "8":
        print("\n🔚 Завершение работы")
        break
    else:
        print("❌ Неверный ввод. Попробуйте снова")
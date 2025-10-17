import streamlit as st
import requests
import pandas as pd
from io import BytesIO

# --- Configuración de la página ---
st.set_page_config(
    page_title="Circuits API Dashboard",
    page_icon="🏎️",
    layout="wide"
)

# --- Configuración de la API ---
API_BASE_URL = "http://mi-funcion-api:80"

# --- Gestión del estado de la sesión ---
if 'token' not in st.session_state:
    st.session_state.token = None
    st.session_state.role = None
    st.session_state.username = None

# --- Funciones de Login, Registro y Logout ---
def login(username, password):
    try:
        # Paso 1: Obtener el token
        response_token = requests.post(f"{API_BASE_URL}/token", data={"username": username, "password": password})
        response_token.raise_for_status()
        token = response_token.json().get("access_token")
        st.session_state.token = token

        # Paso 2: Usar el token para obtener los datos del usuario
        headers = {"Authorization": f"Bearer {token}"}
        response_user = requests.get(f"{API_BASE_URL}/users/me", headers=headers)
        response_user.raise_for_status()
        user_data = response_user.json()

        # Guardar los datos en la sesión
        st.session_state.role = user_data.get("role")
        st.session_state.username = user_data.get("username")
        st.rerun()

    except requests.exceptions.RequestException as e:
        if e.response and e.response.status_code == 401:
            st.error("Usuario o contraseña incorrectos, o cuenta inactiva.")
        else:
            st.error(f"Error al conectar con la API: {e}")
        # Limpiar todo si falla
        st.session_state.token = None
        st.session_state.role = None
        st.session_state.username = None

def register(username, password):
    try:
        response = requests.post(f"{API_BASE_URL}/register", json={"username": username, "password": password})
        response.raise_for_status()
        st.success(response.json().get("message"))
    except requests.exceptions.RequestException as e:
        if e.response and e.response.status_code == 400:
            st.error("El nombre de usuario ya existe.")
        else:
            st.error(f"Error al registrar: {e}")

def logout():
    st.session_state.token = None
    st.session_state.role = None
    st.session_state.username = None
    # st.rerun() # Eliminado porque es redundante con on_click

# --- Funciones para llamar a la API ---
def get_auth_headers():
    if not st.session_state.token:
        return None
    return {"Authorization": f"Bearer {st.session_state.token}"}

def handle_api_error(e):
    if e.response and e.response.status_code in [401]:
        st.error("Sesión expirada o inválida. Por favor, inicie sesión de nuevo.")
        logout()
        st.rerun()
    else:
        st.error(f"Error al conectar con la API: {e}")

def get_api_data(endpoint):
    headers = get_auth_headers()
    if not headers: return None
    try:
        response = requests.get(f"{API_BASE_URL}/{endpoint}", headers=headers)
        if response.status_code == 403:
            return "FORBIDDEN"
        if response.status_code == 404:
            return "NOT_FOUND"
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        handle_api_error(e)
        return None

def post_api_data(endpoint):
    headers = get_auth_headers()
    if not headers: return None
    try:
        response = requests.post(f"{API_BASE_URL}/{endpoint}", headers=headers)
        response.raise_for_status()
        st.success(response.json().get("message"))
        st.rerun()
    except requests.exceptions.RequestException as e:
        handle_api_error(e)

def delete_api_data(endpoint):
    headers = get_auth_headers()
    if not headers: return None
    try:
        response = requests.delete(f"{API_BASE_URL}/{endpoint}", headers=headers)
        response.raise_for_status()
        st.success(response.json().get("message"))
        st.rerun()
    except requests.exceptions.RequestException as e:
        handle_api_error(e)

def upload_file_api(endpoint, file):
    headers = get_auth_headers()
    if not headers: return None
    try:
        files = {'file': (file.name, file, file.type)}
        response = requests.post(f"{API_BASE_URL}/{endpoint}", headers=headers, files=files)
        response.raise_for_status()
        st.success(response.json().get("detail"))
    except requests.exceptions.RequestException as e:
        if e.response:
            st.error(f"Error al subir el fichero: {e.response.json().get('detail')}")
        else:
            handle_api_error(e)
        
# --- Genera los botones de descarga ---
def show_download_buttons(df):
    st.write("")
    csv_data = df.to_csv(index=False).encode('utf-8')
    excel_buffer = BytesIO()
    df.to_excel(excel_buffer, index=False, engine='openpyxl')
    excel_data = excel_buffer.getvalue()
    col1, col2 = st.columns(2)
    with col1:
        st.download_button(label="📥 Descargar como CSV", data=csv_data, file_name='data.csv', mime='text/csv')
    with col2:
        st.download_button(label="📥 Descargar como Excel (XLSX)", data=excel_data, file_name='data.xlsx', mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

# --- Lógica principal de la aplicación ---
if st.session_state.token is None:
    st.title("Bienvenido al Dashboard de Circuitos")
    login_tab, register_tab = st.tabs(["Iniciar Sesión", "Registrarse"])

    with login_tab:
        with st.form("login_form"):
            username = st.text_input("Usuario")
            password = st.text_input("Contraseña", type="password")
            submitted = st.form_submit_button("Login")
            if submitted:
                login(username, password)

    with register_tab:
        with st.form("register_form"):
            reg_username = st.text_input("Elige un nombre de usuario")
            reg_password = st.text_input("Elige una contraseña", type="password")
            reg_submitted = st.form_submit_button("Crear Cuenta")
            if reg_submitted:
                register(reg_username, reg_password)
else:
    st.sidebar.title(f"Bienvenido, {st.session_state.username}")
    st.sidebar.caption(f"Rol: {st.session_state.role}")
    st.sidebar.button("Cerrar Sesión", on_click=logout)
    
    menu_options = ["Ver Todos", "Buscar por ID", "Filtrar por Localización", "Filtrar por País"]
    if st.session_state.role == 'admin':
        menu_options.append("Ver Pilotos")
        menu_options.append("Buscar Piloto")
        menu_options.append("Panel de Admin")
        menu_options.append("Importar Datos")
        
    page = st.sidebar.radio("Menú:", menu_options)

    if page == "Ver Todos":
        st.title("Dashboard de Circuitos de Carreras 🏎️")
        st.write("Esta página muestra todos los circuitos disponibles en la API.")
        data = get_api_data("items")
        if data and isinstance(data, list):
            df = pd.DataFrame(data)
            st.dataframe(df)
            show_download_buttons(df)

    elif page == "Buscar por ID":
        st.title("Buscar Circuito por ID")
        circuit_id = st.text_input("Introduce el ID del circuito:")
        if st.button("Buscar"):
            if circuit_id:
                circuit_data = get_api_data(f"items/{circuit_id}")
                if circuit_data == "NOT_FOUND":
                    st.warning(f"No se encontró ningún circuito con el ID: {circuit_id}")
                elif circuit_data:
                    st.json(circuit_data)
                    df = pd.DataFrame([circuit_data])
                    show_download_buttons(df)
            else:
                st.warning("Por favor, introduce un ID.")

    elif page == "Filtrar por Localización":
        st.title("Filtrar Circuitos por Localización")
        location = st.text_input("Introduce la localización (ej: Melbourne):")
        if st.button("Filtrar"):
            if location:
                circuits = get_api_data(f"location/{location}")
                if circuits and isinstance(circuits, list):
                    if len(circuits) > 0:
                        st.write(f"Se encontraron {len(circuits)} circuitos en {location}:")
                        df = pd.DataFrame(circuits)
                        st.dataframe(df)
                        show_download_buttons(df)
                    else:
                        st.info(f"No se encontraron circuitos para la localización: {location}")
            else:
                st.warning("Por favor, introduce una localización.")

    elif page == "Filtrar por País":
        st.title("Filtrar Circuitos por País")
        country = st.text_input("Introduce el país (ej: Spain):")
        if st.button("Filtrar"):
            if country:
                circuits = get_api_data(f"country/{country}")
                if circuits and isinstance(circuits, list):
                    if len(circuits) > 0:
                        st.write(f"Se encontraron {len(circuits)} circuitos en {country}:")
                        df = pd.DataFrame(circuits)
                        st.dataframe(df)
                        show_download_buttons(df)
                    else:
                        st.info(f"No se encontraron circuitos para el país: {country}")
            else:
                st.warning("Por favor, introduce un país.")
            
    elif page == "Ver Pilotos":
        st.title("Dashboard de Pilotos 🧑‍✈️")
        data = get_api_data("pilots")
        if data == "FORBIDDEN":
            st.warning("🔒 No tienes permisos de administrador para ver esta sección.")
        elif data and isinstance(data, list):
            df = pd.DataFrame(data)
            st.dataframe(df)
            
    elif page == "Buscar Piloto":
        st.title("Buscar Piloto por Nombre 🧑‍✈️")
        pilot_name = st.text_input("Introduce el nombre o parte del nombre del piloto:")
        if st.button("Buscar Piloto"):
            if pilot_name:
                pilots = get_api_data(f"pilots/search/{pilot_name}")
                if pilots and isinstance(pilots, list):
                    if len(pilots) > 0:
                        st.write(f"Resultados de la búsqueda para '{pilot_name}':")
                        df = pd.DataFrame(pilots)
                        st.dataframe(df)
                    else:
                        st.info(f"No se encontraron pilotos con el nombre: {pilot_name}")
            else:
                st.warning("Por favor, introduce un nombre.")
            
    elif page == "Panel de Admin":
        st.title("Panel de Administración de Usuarios ⚙️")
        st.write("Aquí puedes aprobar las solicitudes de registro de nuevos usuarios.")
        
        pending_users = get_api_data("admin/pending-users")
        
        if pending_users == "FORBIDDEN":
             st.warning("🔒 No tienes permisos de administrador para ver esta sección.")
        elif pending_users and isinstance(pending_users, list):
            if len(pending_users) > 0:
                st.write("Usuarios pendientes de aprobación:")
                for username in pending_users:
                    col1, col2, col3 = st.columns([3, 1, 1])
                    with col1:
                        st.write(username)
                    with col2:
                        if st.button(f"Aprobar", key=f"approve_{username}"):
                            post_api_data(f"admin/approve-user/{username}")
                    with col3:
                        if st.button(f"Rechazar", key=f"decline_{username}"):
                            delete_api_data(f"admin/decline-user/{username}")
            else:
                st.info("No hay usuarios pendientes de aprobación.")

    elif page == "Importar Datos":
        st.title("Importar Datos desde CSV 📂")
        st.write("Sube ficheros CSV para añadir nuevos circuitos o pilotos a la base de datos.")

        st.subheader("Subir CSV de Circuitos")
        st.info("El fichero debe contener las columnas: `name`, `location`, `country`")
        uploaded_circuits_file = st.file_uploader("Elige un fichero de circuitos", key="circuits_uploader")
        if uploaded_circuits_file is not None:
            if st.button("Importar Circuitos"):
                upload_file_api("upload-circuits-csv/", uploaded_circuits_file)

        st.subheader("Subir CSV de Pilotos")
        st.info("El fichero debe contener las columnas del F1DriversDataset.csv original.")
        uploaded_pilots_file = st.file_uploader("Elige un fichero de pilotos", key="pilots_uploader")
        if uploaded_pilots_file is not None:
            if st.button("Importar Pilotos"):
                upload_file_api("upload-pilots-csv/", uploaded_pilots_file)

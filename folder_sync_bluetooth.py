import socket
import threading
import os
import time
import shutil

recv_bits = 1000000

# Configuración inicial:
peer_addr = "58:6C:25:61:A9:BC"  # Dirección MAC del otro dispositivo
local_addr = "7C:25:DA:C2:86:A9"  # Dirección MAC local
port = 30  # Canal Bluetooth (RFCOMM)
local_folder_route = "D:/Carpeta1/"  # Carpeta local a sincronizar
sync_interval = 2  # Intervalo de sincronización (en segundos)

# Lock para sincronizar el acceso a recursos compartidos
folder_lock = threading.Lock()


############################################################################################################################################################


# Obtener todos los items nuevos en el directorio
def get_all_items(folder_path):
    files_in_dir = []
    files_mod_time = []
    folders_in_dir = []
    for root, dirs, files in os.walk(folder_path):
        # Agregar directorios
        for dir_name in dirs:
            # Aquí es necesario verificar que estén dentro, ya que al recibir solicitud se agregan y podría existir un duplicado
            if folders_in_dir.count(os.path.join(root, dir_name))==0:
                folders_in_dir.append(os.path.join(root, dir_name))
        # Agregar archivos
        for file_name in files:
            # Aquí es necesario verificar que estén dentro, ya que al recibir solicitud se agregan y podría existir un duplicado
            if files_in_dir.count(os.path.join(root, file_name))==0:
                files_in_dir.append(os.path.join(root, file_name))
                files_mod_time.append(os.path.getmtime(os.path.join(root, file_name)))
    return (files_in_dir,folders_in_dir, files_mod_time)

# Obtener archivos nuevos (tambien es usado para obtener carpetas nuevas y archivos y carpetas borradas)
def get_files(new_files_set, init_files_set):
    new_files = []
    if len(init_files_set)==0 and len(new_files_set)>0:
        return new_files_set
    for i in range (len(new_files_set)):
        for j in range (len(init_files_set)):
            if new_files_set[i]==init_files_set[j]:
                break
            if j==len(init_files_set)-1:
                new_files.append(new_files_set[i])
    return new_files

# Obtener archivos modificados comparando fechas de modificación
def compare_files_mod_time(init_files_in_folder, current_files_in_folder, init_modif_times, current_modif_times):
    modif_files = []
    for i in range(len(current_files_in_folder)):
        for j in range(len(init_files_in_folder)):
            if current_files_in_folder[i]==init_files_in_folder[j] and current_modif_times[i]!=init_modif_times[j]:
                modif_files.append(current_files_in_folder[i])
    return modif_files

# Función para enviar un archivo
def send_file(sock, file_path, absolute_route):
    #file_name = os.path.basename(file_path)
    print(f"Enviando archivo: {file_path}")
    sock.send(f"FILE::{file_path}".encode())
    with open(absolute_route, "rb") as file:
        while True:
            data = file.read(recv_bits)
            if not data:
                break
            sock.send(data)
    print(f"Archivo enviado: {file_path}")

# Función para enviar una carpeta
def send_folder(sock, folder_path):
    print(f"Enviando archivo: {folder_path}")
    sock.send(f"FOLDER::{folder_path}".encode())
    print(f"Archivo enviado: {folder_path}")


############################################################################################################################################################


# Función para recibir un archivo
def receive_file(sock, target_folder, file_name):
    """Recibe un archivo desde el dispositivo remoto y lo guarda."""
    try:
        # Recibir el paquete de información del archivo
        data=b''
        while True:
            chunk = sock.recv(recv_bits)  # Recibe hasta 4096 bytes
            print(len(chunk))
            if not chunk:
                # Si chunk está vacío, significa que se ha cerrado la conexión
                break
            data += chunk  # Agrega el chunk recibido al buffer

        file_path = os.path.join(target_folder, file_name)
        print(f"Recibiendo archivo: {file_name}")

        # Creando nuevo directorio de ser necesario
        directory = os.path.dirname(file_name)
        if directory:  # Evita problemas si no hay carpeta en el path
            os.makedirs(directory, exist_ok=True)

        # Abrir el archivo para escribir los datos recibidos
        with open(file_path, "wb") as file:
            file.write(data)

        # Agregar el archivo a la lista de archivos
        files_in_folder.append(file_path)
        modif_times.append(os.path.getmtime(file_path))
        last_received_files.append(file_path)               #ARREGLADO BUG#1

        print(f"Archivo recibido: {file_name}")
    except Exception as e:
        print(f"Error al recibir archivo: {e}")

# Función para eliminar un archivo
def delete_file(target_folder, file_name):
    file_path = os.path.join(target_folder, file_name)
    if os.path.exists(file_path):
        os.remove(file_path)

        # Eliminar el archivo de la lista de archivos
        i = files_in_folder.count(file_path)
        if i>0:
            for j in range(i):
                files_in_folder.remove(file_path)

        print(f"Archivo eliminado: {file_name}")

# Función para recibir una carpeta
def receive_folder(sock, target_folder, folder_name):
    """Recibe un archivo desde el dispositivo remoto y lo guarda."""
    try:       
        folder_path = os.path.join(target_folder, folder_name)
        print(f"Recibiendo carpeta: {folder_name}")

        # Creando nuevo directorio de ser necesario
        if folder_path:  # Evita problemas si no hay carpeta en el path
            os.makedirs(folder_path, exist_ok=True)

        folders_in_folder.append(folder_path)
        print(f"Carpeta recibida: {folder_name}")
    except Exception as e:
        print(f"Error al recibir archivo: {e}")

# Función para eliminar una carpeta
def delete_folder(target_folder, folder_name):
    folder_path = os.path.join(target_folder, folder_name)
    if os.path.exists(folder_path):
        shutil.rmtree(folder_path)              #ARREGLADO BUG#3

        # Eliminar el archivo de la lista de archivos
        i = folders_in_folder.count(folder_path)
        if i>0:
            for j in range(i):
                folders_in_folder.remove(folder_path)
        print(f"Carpeta eliminada: {folder_name}")


############################################################################################################################################################


# Servidor: Maneja conexiones entrantes
def start_server(local_addr, port, local_folder_route):
    # Iniciar socket bluetooth
    sock = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
    sock.bind((local_addr, port))
    sock.listen(1)
    print(f"Servidor escuchando en {local_addr}:{port}")

    # Servidor recibiendo conexión
    while True:
        client_sock, address = sock.accept()
        print(f"Conexión recibida de {address[0]}")
        data = client_sock.recv(recv_bits).decode()

        # Bloqueando acceso al monitor de carpetas
        with folder_lock:
            # Verificando acción
            if data.startswith("FILE::"):
                file_name = data.split("::")[1]
                receive_file(client_sock, local_folder_route, file_name)
            elif data.startswith("FOLDER::"):
                file_name = data.split("::")[1]
                receive_folder(client_sock, local_folder_route, file_name)
            elif data.startswith("DELETE::"):
                file_name = data.split("::")[1]
                delete_file(local_folder_route, file_name)
            elif data.startswith("DELETEF::"):
                file_name = data.split("::")[1]
                delete_folder(local_folder_route, file_name)
            # Cerrando socket
            client_sock.close()

# Monitor: Sincroniza cambios locales con el otro dispositivo
def monitor_folder(local_folder_route, peer_addr, port):
    # Incluyendo variables globales                         #ARREGLADO BUG#1
    global files_in_folder, folders_in_folder, modif_times, last_received_files 

    # Monitor de carpetas en espera a cambios
    while True:
        time.sleep(sync_interval)
        # Bloqueando el acceso a conexiones entrantes
        with folder_lock:

            # Extrayendo cambios en la carpeta
            (current_files_in_folder, current_folders_in_folder, current_modif_times) = get_all_items(local_folder_route)
            new_files = get_files(current_files_in_folder, files_in_folder)
            new_folders = get_files(current_folders_in_folder, folders_in_folder)
            deleted_files = get_files(files_in_folder, current_files_in_folder)
            deleted_folders = get_files(folders_in_folder, current_folders_in_folder)
            modified_files = compare_files_mod_time(files_in_folder, current_files_in_folder, modif_times, current_modif_times)
            modified_files = get_files(modified_files, new_files)
            modified_files = get_files(modified_files, deleted_files)
            modified_files = get_files(modified_files, last_received_files)         #ARREGLADO BUG#1

            # Mostrando cambios al usuario
            if len(new_files)>0:
                print(f"Nuevos archivos:")
                print(", ".join(new_files))
            if len(new_folders)>0:
                print(f"Nuevas carpetas:")
                print(", ".join(new_folders))
            if len(deleted_files)>0:
                print(f"Archivos borrados:")
                print(", ".join(deleted_files))
            if len(deleted_folders)>0:
                print(f"Carpetas borradas:")
                print(", ".join(deleted_folders))
            if len(modified_files)>0:
                print(f"Archivos modificados:")
                print(", ".join(modified_files))
            if len(new_files)>0 or len(new_folders)>0 or len(deleted_files)>0 or len(deleted_folders)>0 or len(modified_files)>0:
                print(f"\n")

            # Integrando archivos modificados a las listas para realizar acciones de borrado y enviado (#ARREGLADO BUG#2)
            for file_name in modified_files:
                deleted_files.append(file_name)
                new_files.append(file_name)

            # Enviando solicitud para archivos borrados
            for file_name in deleted_files:
                relative_route = os.path.relpath(file_name, start=local_folder_route)
                print(f"Archivo eliminado localmente: {file_name}")
                with socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM) as sock:
                    try:
                        sock.connect((peer_addr, port))
                        sock.send(f"DELETE::{relative_route}".encode())
                    except Exception as e:
                        print(f"Error al conectar con el servidor: {e}")
                print(f"\n")

            # Enviando solicitud para carpetas borradas
            for folder_name in deleted_folders:
                relative_route = os.path.relpath(folder_name, start=local_folder_route)
                print(f"Carpeta eliminada localmente: {folder_name}")
                with socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM) as sock:
                    try:
                        sock.connect((peer_addr, port))
                        sock.send(f"DELETEF::{relative_route}".encode())
                    except Exception as e:
                        print(f"Error al conectar con el servidor: {e}")
                print(f"\n")        

            # Enviando solicitud para carpetas nuevas
            for folder_name in new_folders:
                relative_route = os.path.relpath(folder_name, start=local_folder_route)
                print(f"Detectada nueva carpeta: {folder_name}")
                with socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM) as sock:
                    try:
                        sock.connect((peer_addr, port))
                        send_folder(sock, relative_route)
                    except Exception as e:
                        print(f"Error al conectar con el servidor: {e}")
                print(f"\n")        

            # Enviando solicitud para archivos nuevos
            for file_name in new_files:
                relative_route = os.path.relpath(file_name, start=local_folder_route)
                print(f"Detectado nuevo archivo: {file_name}")
                with socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM) as sock:
                    try:
                        sock.connect((peer_addr, port))
                        send_file(sock, relative_route, file_name)
                    except Exception as e:
                        print(f"Error al conectar con el servidor: {e}")
                print(f"\n")        

            # Actualizando cambios de la carpeta
            files_in_folder = current_files_in_folder
            folders_in_folder = current_folders_in_folder
            modif_times = current_modif_times
            last_received_files = []                         #ARREGLADO BUG#1


############################################################################################################################################################


# Recibir entrada del usuario
entrada = input("Por favor, ingresa la dirección MAC local: XX:XX:XX:XX:XX:XX\n Dirección MAC local: ")
# Verificando que la dirección MAC ingresada sea correcta
while not len(entrada) == 17 or not entrada[2] == ':' or not entrada[5] == ':' or not entrada[8] == ':' or not entrada[11] == ':' or not entrada[14] == ':':
    entrada = input("Formato inválido, por favor inserte la dirección MAC local: XX:XX:XX:XX:XX:XX\n Dirección MAC local: ")
local_addr = entrada

entrada = input("Por favor, ingresa la dirección MAC remota: XX:XX:XX:XX:XX:XX\n Dirección MAC remota: ")
# Verificando que la dirección MAC ingresada sea correcta
while not len(entrada) == 17 or not entrada[2] == ':' or not entrada[5] == ':' or not entrada[8] == ':' or not entrada[11] == ':' or not entrada[14] == ':':
    entrada = input("Formato inválido, por favor inserte la dirección MAC remota: XX:XX:XX:XX:XX:XX\n Dirección MAC remota: ")
peer_addr = entrada

entrada = input("Por favor, ingresa la ruta a la carpeta que desea sincronizar: C:/ruta/a/la/carpeta/ \n Ruta a la carpeta: ")
# Verificando que la dirección MAC ingresada sea correcta
while not entrada or not entrada[-1] == '/' or not os.path.exists(entrada):
    entrada = input("Ruta inválido, por favor ingresa la ruta a la carpeta que desea sincronizar: C:/ruta/a/la/carpeta/ \n Ruta a la carpeta: ")
local_folder_route = entrada

#Items iniciales dentro de la carpeta             #ARREGLADO BUG#1
(files_in_folder, folders_in_folder, modif_times, last_received_files) = ([], [], [], [])   

# Iniciar servidor en un hilo
server_thread = threading.Thread(target=start_server, args=(local_addr, port, local_folder_route))
server_thread.daemon = True
server_thread.start()

# Iniciar cliente en un hilo
monitor_thread = threading.Thread(target=monitor_folder, args=(local_folder_route, peer_addr, port))
monitor_thread.daemon = True
monitor_thread.start()

print("Sincronización en ejecución. Presiona Ctrl+C para salir.")
try:
    while True:
        time.sleep(1)  # Mantener el script corriendo
except KeyboardInterrupt:
    print("Sincronización detenida.")

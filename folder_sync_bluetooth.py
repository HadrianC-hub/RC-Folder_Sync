import socket
import threading
import os
import time

# Configuración inicial.
local_addr = "90:09:DF:A2:85:D1"  # Dirección MAC del otro dispositivo
peer_addr = "7C:25:DA:C2:86:A9"  # Dirección MAC local
port = 30  # Canal Bluetooth (RFCOMM)
local_folder_route = "D:/Carpeta2/"  # Carpeta local a sincronizar

# Función para recibir un archivo
def receive_file(sock, target_folder, file_name):
    """Recibe un archivo desde el dispositivo remoto y lo guarda."""
    try:
        # Recibir el paquete de información del archivo
        data=b''
        while True:
            chunk = sock.recv(4096)  # Recibe hasta 4096 bytes
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
        data = client_sock.recv(1024).decode()

        # Verificando acción
        if data.startswith("FILE::"):
            file_name = data.split("::")[1]
            receive_file(client_sock, local_folder_route, file_name)
        elif data.startswith("FOLDER::"):
            #IMPLEMENTAR RECIBIR CARPETAS
        elif data.startswith("DELETE::"):
            file_name = data.split("::")[1]
            delete_file(local_folder_route, file_name)
        elif data.startswith("DELETEF::"):
            #IMPLEMENTAR BORRADO DE CARPETAS
        # Cerrando socket
        client_sock.close()

# Iniciar servidor en un hilo
server_thread = threading.Thread(target=start_server, args=(local_addr, port, local_folder_route))
server_thread.daemon = True
server_thread.start()

print("Sincronización en ejecución. Presiona Ctrl+C para salir.")
try:
    while True:
        time.sleep(1)  # Mantener el script corriendo
except KeyboardInterrupt:
    print("Sincronización detenida.")

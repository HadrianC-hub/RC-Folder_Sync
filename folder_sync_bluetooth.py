import socket
import threading
import os
import time

# Configuración inicial
peer_addr = "90:09:DF:A2:85:D1"  # Dirección MAC del otro dispositivo
local_addr = "7C:25:DA:C2:86:A9"  # Dirección MAC local
port = 30  # Canal Bluetooth (RFCOMM)
local_folder_route = "D:/Carpeta1/"  # Carpeta local a sincronizar

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
      
        #(LAURA)
        # Verificando acción
        if data.startswith("FILE::"):
            #IMPLEMENTAR RECIBIR ARCHIVOS
        elif data.startswith("FOLDER::"):
            #IMPLEMENTAR RECIBIR CARPETAS
        elif data.startswith("DELETE::"):
            #IMPLEMENTAR BORRADO DE ARCHIVOS
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

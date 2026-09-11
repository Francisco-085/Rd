import socket
import threading


# ======================================================
# BLOCO 1 - Configuração geral
# ======================================================
IP = "0.0.0.0"
PORTA = 5000

# Variáveis usadas pelo modo TCP
clientes_tcp = []
nomes_tcp = {}

# Variáveis usadas pelo modo UDP
socket_udp = None
enderecos_udp = []
nomes_udp = {}

modo = None  # guarda se está rodando em "TCP" ou "UDP"


# ======================================================
# BLOCO 2 - Transmitir mensagem para todos (funciona nos 2 modos)
# ======================================================
def transmitir(mensagem, remetente=None):
    if modo == "TCP":
        for cliente in clientes_tcp:
            if cliente != remetente:
                try:
                    cliente.send(mensagem.encode("utf-8"))
                except:
                    pass
    elif modo == "UDP":
        for endereco in enderecos_udp:
            if endereco != remetente:
                socket_udp.sendto(mensagem.encode("utf-8"), endereco)


# ======================================================
# BLOCO 3 - Servidor digitar mensagens (funciona nos 2 modos)
# ======================================================
def enviar_mensagens_servidor():
    while True:
        mensagem = input()
        if mensagem.lower() == "sair":
            print("Encerrando envio do servidor (conexões continuam ativas).")
            break
        transmitir(f"[Servidor]: {mensagem}")


# ======================================================
# BLOCO 4 - Modo TCP: cuidar de cada cliente conectado
# ======================================================
def lidar_cliente_tcp(conexao):
    try:
        nome = conexao.recv(1024).decode("utf-8")
        nomes_tcp[conexao] = nome
        clientes_tcp.append(conexao)
        print(f"[+] {nome} entrou no chat.")
        transmitir(f"[Servidor] {nome} entrou no chat.")

        while True:
            mensagem = conexao.recv(1024).decode("utf-8")
            if not mensagem:
                break
            print(f"{nome}: {mensagem}")
            transmitir(f"{nome}: {mensagem}", remetente=conexao)

    except:
        pass
    finally:
        if conexao in clientes_tcp:
            clientes_tcp.remove(conexao)
        nome_saiu = nomes_tcp.pop(conexao, "Alguém")
        print(f"[-] {nome_saiu} saiu do chat.")
        transmitir(f"[Servidor] {nome_saiu} saiu do chat.")
        conexao.close()


# ======================================================
# BLOCO 5 - Modo TCP: iniciar servidor e aceitar conexões
# ======================================================
def iniciar_servidor_tcp():
    servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    servidor.bind((IP, PORTA))
    servidor.listen()
    print(f"Servidor TCP rodando em {IP}:{PORTA}")
    print("Digite uma mensagem e aperte Enter para enviar a todos os clientes.\n")

    thread_input = threading.Thread(target=enviar_mensagens_servidor)
    thread_input.daemon = True
    thread_input.start()

    while True:
        conexao, endereco = servidor.accept()
        print(f"Nova conexão: {endereco}")
        thread = threading.Thread(target=lidar_cliente_tcp, args=(conexao,))
        thread.start()


# ======================================================
# BLOCO 6 - Modo UDP: escutar mensagens (não tem "conexão" fixa)
# ======================================================
def iniciar_servidor_udp():
    global socket_udp
    socket_udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    socket_udp.bind((IP, PORTA))
    print(f"Servidor UDP rodando em {IP}:{PORTA}")
    print("Digite uma mensagem e aperte Enter para enviar a todos os clientes.\n")

    thread_input = threading.Thread(target=enviar_mensagens_servidor)
    thread_input.daemon = True
    thread_input.start()

    while True:
        dados, endereco = socket_udp.recvfrom(1024)
        mensagem = dados.decode("utf-8")

        if endereco not in enderecos_udp:
            # primeira mensagem recebida desse endereço = o nome dele
            enderecos_udp.append(endereco)
            nomes_udp[endereco] = mensagem
            print(f"[+] {mensagem} entrou no chat.")
            transmitir(f"[Servidor] {mensagem} entrou no chat.", remetente=endereco)
        else:
            nome = nomes_udp.get(endereco, str(endereco))
            print(f"{nome}: {mensagem}")
            transmitir(f"{nome}: {mensagem}", remetente=endereco)


# ======================================================
# BLOCO 7 - Escolher o protocolo e iniciar
# ======================================================
def iniciar_servidor():
    global modo
    protocolo = input("Escolha o protocolo (TCP ou UDP): ").strip().upper()

    if protocolo == "TCP":
        modo = "TCP"
        iniciar_servidor_tcp()
    elif protocolo == "UDP":
        modo = "UDP"
        iniciar_servidor_udp()
    else:
        print("Protocolo inválido. Digite TCP ou UDP.")


if __name__ == "__main__":
    iniciar_servidor()

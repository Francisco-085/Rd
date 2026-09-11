import socket
import threading


# ======================================================
# BLOCO 1 - Modo TCP: conectar e trocar mensagens
# ======================================================
def cliente_tcp(ip_servidor, porta_servidor, nome):
    cliente = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        cliente.connect((ip_servidor, porta_servidor))
        cliente.send(nome.encode("utf-8"))
    except Exception as erro:
        print(f"Não foi possível conectar: {erro}")
        return

    print("Conectado! Digite suas mensagens (ou 'sair' para encerrar).\n")

    thread_receber = threading.Thread(target=receber_mensagens_tcp, args=(cliente,))
    thread_receber.daemon = True
    thread_receber.start()

    while True:
        mensagem = input()
        if mensagem.lower() == "sair":
            cliente.close()
            print("Desconectado.")
            break
        try:
            cliente.send(mensagem.encode("utf-8"))
        except:
            print("Erro ao enviar. Conexão perdida.")
            break
 

def receber_mensagens_tcp(cliente):
    while True:
        try:
            mensagem = cliente.recv(1024).decode("utf-8")
            if not mensagem:
                print("\nConexão encerrada pelo servidor.")
                break
            print(mensagem)
        except:
            break


# ======================================================
# BLOCO 2 - Modo UDP: registrar nome e trocar mensagens
# ======================================================
def cliente_udp(ip_servidor, porta_servidor, nome):
    cliente = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    endereco_servidor = (ip_servidor, porta_servidor)

    # primeira mensagem enviada = o nome (é assim que o servidor identifica você)
    cliente.sendto(nome.encode("utf-8"), endereco_servidor)

    print("Registrado! Digite suas mensagens (ou 'sair' para encerrar).\n")

    thread_receber = threading.Thread(target=receber_mensagens_udp, args=(cliente,))
    thread_receber.daemon = True
    thread_receber.start()

    while True:
        mensagem = input()
        if mensagem.lower() == "sair":
            cliente.close()
            print("Desconectado.")
            break
        cliente.sendto(mensagem.encode("utf-8"), endereco_servidor)


def receber_mensagens_udp(cliente):
    while True:
        try:
            dados, _ = cliente.recvfrom(1024)
            print(dados.decode("utf-8"))
        except:
            break


# ======================================================
# BLOCO 3 - Escolher protocolo e dados de conexão
# ======================================================
def iniciar_cliente():
    protocolo = input("Escolha o protocolo (TCP ou UDP): ").strip().upper()
    ip_servidor = input("Digite o IP do servidor: ").strip()
    porta_servidor = int(input("Digite a porta do servidor: ").strip())
    nome = input("Digite seu nome: ").strip()

    if protocolo == "TCP":
        cliente_tcp(ip_servidor, porta_servidor, nome)
    elif protocolo == "UDP":
        cliente_udp(ip_servidor, porta_servidor, nome)
    else:
        print("Protocolo inválido. Digite TCP ou UDP.")


if __name__ == "__main__":
    iniciar_cliente()

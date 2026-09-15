import socket
import threading
import json
import time
import subprocess  # Usado para executar comandos do sistema operacional (tracert, nslookup, ping)
import platform    # Usado para detectar se estamos no Windows, Linux ou Mac
import re          # Usado para "filtrar" (extrair) informações de dentro de textos com expressões regulares
from collections import deque
import statistics

# Configuração
SERVIDOR_IP = "localhost"  # Mude para o IP do servidor se estiver remoto
PORTA = 5000
TAMANHO_HISTORICO = 50

class ClienteRede:
    def __init__(self, nome):
        self.nome = nome
        self.protocolo = None
        self.socket = None
        self.conectado = False
        self.latencias = deque(maxlen=TAMANHO_HISTORICO)
        self.pacotes_enviados = 0
        self.pacotes_recebidos = 0
    
    def adicionar_latencia(self, latencia_ms):
        """Adiciona uma medição de latência"""
        self.latencias.append(latencia_ms)
    
    def obter_jitter(self):
        """Calcula o jitter"""
        if len(self.latencias) < 2:
            return 0
        return statistics.stdev(self.latencias)
    
    def obter_latencia_media(self):
        """Retorna latência média"""
        if not self.latencias:
            return 0
        return statistics.mean(self.latencias)
    
    def obter_latencia_min_max(self):
        """Retorna min/max de latência"""
        if not self.latencias:
            return 0, 0
        return min(self.latencias), max(self.latencias)
    
    def obter_relatorio(self):
        """Gera relatório de estatísticas"""
        if not self.latencias:
            return "Sem dados de latência ainda."
        
        media = self.obter_latencia_media()
        jitter = self.obter_jitter()
        min_lat, max_lat = self.obter_latencia_min_max()
        
        return f"""
╔════════════════════════════════════════════╗
║       ESTATÍSTICAS DE REDE - {self.nome}
╠════════════════════════════════════════════╣
║ Latência Média:        {media:>8.2f} ms
║ Latência Mínima:       {min_lat:>8.2f} ms
║ Latência Máxima:       {max_lat:>8.2f} ms
║ Jitter:                {jitter:>8.2f} ms
║ Pacotes Enviados:      {self.pacotes_enviados:>8}
║ Pacotes Recebidos:     {self.pacotes_recebidos:>8}
║ Medições Coletadas:    {len(self.latencias):>8}/{TAMANHO_HISTORICO}
╚════════════════════════════════════════════╝
        """

def criar_pong(timestamp):
    """Cria resposta de pong"""
    return json.dumps({
        "tipo": "PONG",
        "timestamp": timestamp
    })


def obter_ip_local():
    """
    Descobre o IP local do cliente na rede (LAN).
    Usa o truque do socket UDP "fake connect" a um IP externo só para o
    SO escolher a interface de rede correta (não envia dados de verdade).
    """
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
        finally:
            s.close()
    except Exception:
        return "127.0.0.1"




# ============================================================
# ============= DIAGNÓSTICO DE REDE DO SISTEMA =============
# ============================================================
# Estas funções chamam comandos que já existem no sistema operacional
# (ping, tracert/traceroute, nslookup) para diagnosticar a rede da
# máquina do CLIENTE (não a do servidor). Isso é útil para o usuário
# descobrir se um problema de conexão é culpa da rede dele mesmo.
#
# O módulo "subprocess" executa esses comandos como se fossem
# digitados no terminal, e captura o texto que eles retornam.
# O módulo "platform" diz se estamos no Windows, Linux ou macOS,
# porque o nome/parâmetros desses comandos mudam entre eles.

def sistema_operacional():
    """
    Retorna o nome do sistema operacional atual em letras minúsculas.
    Ex: 'windows', 'linux' ou 'darwin' (darwin = macOS).
    """
    return platform.system().lower()


def mostrar_meu_ip():
    """
    Mostra o(s) IP(s) da máquina do cliente.

    Truque usado: abrimos um socket UDP e "conectamos" (sem enviar
    dados de verdade) a um endereço externo (8.8.8.8). O sistema
    operacional escolhe a interface de rede que seria usada para
    alcançar esse endereço, e lemos o IP dessa interface.
    """
    print("\n" + "=" * 60)
    print("📡 INFORMAÇÕES DE IP (cliente)")
    print("=" * 60)

    try:
        hostname = socket.gethostname()
        print(f"Hostname: {hostname}")

        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("8.8.8.8", 80))
            ip_local = s.getsockname()[0]
        finally:
            s.close()
        print(f"IP Local (rede): {ip_local}")

        try:
            ips_todos = socket.gethostbyname_ex(hostname)[2]
            print(f"Todos os IPs encontrados: {', '.join(ips_todos)}")
        except Exception:
            pass

        try:
            resultado = subprocess.run(
                ["curl", "-s", "--max-time", "3", "https://api.ipify.org"],
                capture_output=True, text=True, timeout=4
            )
            if resultado.returncode == 0 and resultado.stdout.strip():
                print(f"IP Público: {resultado.stdout.strip()}")
        except Exception:
            print("IP Público: não foi possível obter (sem 'curl' ou sem internet)")

    except Exception as e:
        print(f"❌ Erro ao obter IP: {e}")

    print("=" * 60 + "\n")


def mostrar_gateway():
    """
    Mostra o Gateway padrão da máquina do cliente (o "roteador"/"modem"
    por onde a rede local sai para a internet).
        • Windows -> "ipconfig"
        • Linux   -> "ip route"
        • macOS   -> "route -n get default"
    """
    print("\n" + "=" * 60)
    print("🌐 GATEWAY PADRÃO (cliente)")
    print("=" * 60)

    so = sistema_operacional()
    try:
        if so == "windows":
            saida = subprocess.run(["ipconfig"], capture_output=True, text=True, timeout=5).stdout
            encontrados = [ip for ip in re.findall(r"Default Gateway[^\:]*:\s*([\d\.]+)", saida) if ip]
            if encontrados:
                for ip in encontrados:
                    print(f"Gateway: {ip}")
            else:
                print("Gateway não encontrado.")

        elif so == "linux":
            saida = subprocess.run(["ip", "route"], capture_output=True, text=True, timeout=5).stdout
            encontrado = re.search(r"default via ([\d\.]+)", saida)
            print(f"Gateway: {encontrado.group(1)}" if encontrado else "Gateway não encontrado.")

        elif so == "darwin":  # macOS
            saida = subprocess.run(["route", "-n", "get", "default"], capture_output=True, text=True, timeout=5).stdout
            encontrado = re.search(r"gateway:\s*([\d\.]+)", saida)
            print(f"Gateway: {encontrado.group(1)}" if encontrado else "Gateway não encontrado.")
        else:
            print("Sistema operacional não suportado para esta função.")

    except FileNotFoundError:
        print("❌ Comando do sistema não encontrado.")
    except Exception as e:
        print(f"❌ Erro ao obter gateway: {e}")

    print("=" * 60 + "\n")


def mostrar_dns():
    """
    Mostra os servidores DNS configurados na máquina do cliente.
        • Windows -> "ipconfig /all"
        • Linux   -> lê /etc/resolv.conf
        • macOS   -> "scutil --dns"
    """
    print("\n" + "=" * 60)
    print("🧭 SERVIDORES DNS (cliente)")
    print("=" * 60)

    so = sistema_operacional()
    try:
        if so == "windows":
            saida = subprocess.run(["ipconfig", "/all"], capture_output=True, text=True, timeout=5).stdout
            encontrados = re.findall(r"DNS Servers[^\:]*:\s*([\d\.]+)", saida)
            if encontrados:
                for ip in encontrados:
                    print(f"DNS: {ip}")
            else:
                print("Nenhum DNS encontrado.")

        elif so == "linux":
            try:
                with open("/etc/resolv.conf", "r") as arquivo:
                    linhas = arquivo.readlines()
                encontrados = [l.split()[1] for l in linhas if l.strip().startswith("nameserver")]
                if encontrados:
                    for ip in encontrados:
                        print(f"DNS: {ip}")
                else:
                    print("Nenhum DNS encontrado em /etc/resolv.conf")
            except FileNotFoundError:
                print("Arquivo /etc/resolv.conf não encontrado.")

        elif so == "darwin":  # macOS
            saida = subprocess.run(["scutil", "--dns"], capture_output=True, text=True, timeout=5).stdout
            encontrados = re.findall(r"nameserver\[\d+\]\s*:\s*([\d\.]+)", saida)
            vistos = []
            for ip in encontrados:
                if ip not in vistos:
                    vistos.append(ip)
                    print(f"DNS: {ip}")
            if not vistos:
                print("Nenhum DNS encontrado.")
        else:
            print("Sistema operacional não suportado para esta função.")

    except FileNotFoundError:
        print("❌ Comando do sistema não encontrado.")
    except Exception as e:
        print(f"❌ Erro ao obter DNS: {e}")

    print("=" * 60 + "\n")


def executar_tracert(destino):
    """
    Executa um "traceroute" (tracert) até o destino informado, mostrando
    cada "salto" (roteador) pelo qual os pacotes passam. Ajuda a
    descobrir em qual ponto do caminho a rede está lenta.
        • Windows -> "tracert"
        • Linux/macOS -> "traceroute"
    """
    if not destino:
        print("❌ Uso correto: /tracert <endereço ou site>  (ex: /tracert google.com)")
        return

    print(f"\n🔍 Executando tracert para '{destino}'... (isso pode demorar alguns segundos)\n")

    so = sistema_operacional()
    comando = ["tracert", "-h", "15", destino] if so == "windows" else ["traceroute", "-m", "15", destino]

    try:
        processo = subprocess.Popen(
            comando,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        for linha in processo.stdout:
            print(linha.rstrip())
        processo.wait(timeout=60)
        print(f"\n✓ Tracert concluído para '{destino}'\n")

    except FileNotFoundError:
        print("❌ Comando 'tracert/traceroute' não encontrado no sistema.")
    except subprocess.TimeoutExpired:
        print("❌ Tracert demorou demais e foi cancelado (timeout de 60s).")
    except Exception as e:
        print(f"❌ Erro ao executar tracert: {e}")


def executar_nslookup(destino):
    """
    Executa "nslookup", consultando o DNS para obter o IP de um domínio
    (ou o nome de um IP, no caso de DNS reverso).
    """
    if not destino:
        print("❌ Uso correto: /nslookup <endereço ou site>  (ex: /nslookup google.com)")
        return

    print(f"\n🔎 Executando nslookup para '{destino}'...\n")

    try:
        resultado = subprocess.run(
            ["nslookup", destino],
            capture_output=True, text=True, timeout=10
        )
        saida = resultado.stdout if resultado.stdout else resultado.stderr
        print(saida)
        print(f"✓ nslookup concluído para '{destino}'\n")

    except FileNotFoundError:
        print("❌ Comando 'nslookup' não encontrado no sistema.")
    except subprocess.TimeoutExpired:
        print("❌ nslookup demorou demais e foi cancelado (timeout de 10s).")
    except Exception as e:
        print(f"❌ Erro ao executar nslookup: {e}")


def executar_jitter_sistema(destino="8.8.8.8", quantidade=10):
    """
    Testa o JITTER (variação da latência) da conexão do CLIENTE contra
    um destino externo, usando o "ping" do próprio sistema operacional.

    Diferença em relação ao /stats: o /stats mede a latência entre o
    cliente e o SERVIDOR do chat; já esta função mede a estabilidade da
    conexão do cliente com a internet/rede em geral (por padrão contra
    8.8.8.8, o DNS do Google).

    Como o jitter é calculado:
    1. Enviamos vários pings para o destino.
    2. Guardamos o tempo de resposta de cada um.
    3. Calculamos a diferença entre pings CONSECUTIVOS.
    4. A média dessas diferenças é o jitter aproximado.
    """
    print(f"\n📶 Executando teste de jitter contra '{destino}' ({quantidade} pacotes)...\n")

    so = sistema_operacional()
    parametro_quantidade = "-n" if so == "windows" else "-c"

    try:
        resultado = subprocess.run(
            ["ping", parametro_quantidade, str(quantidade), destino],
            capture_output=True, text=True, timeout=quantidade * 2 + 10
        )
        saida = resultado.stdout

        # Tenta extrair os tempos tanto no formato em português ("tempo=")
        # quanto em inglês ("time="), pois varia conforme o idioma do SO.
        tempos_encontrados = re.findall(r"tempo[=<]([\d\.]+)\s*ms", saida, re.IGNORECASE)
        if not tempos_encontrados:
            tempos_encontrados = re.findall(r"time[=<]([\d\.]+)\s*ms", saida, re.IGNORECASE)

        tempos = [float(t) for t in tempos_encontrados]

        if len(tempos) < 2:
            print("❌ Não foi possível coletar tempo suficiente de resposta.")
            print("Saída bruta do ping para conferência:\n")
            print(saida)
            return

        diferencas = [abs(tempos[i] - tempos[i - 1]) for i in range(1, len(tempos))]
        jitter_medio = sum(diferencas) / len(diferencas)
        desvio_padrao = statistics.stdev(tempos) if len(tempos) > 1 else 0

        print("=" * 60)
        print(f"RESULTADO DO TESTE DE JITTER - destino: {destino}")
        print("=" * 60)
        print(f"Pacotes recebidos: {len(tempos)}/{quantidade}")
        print(f"Latência média: {statistics.mean(tempos):.2f} ms")
        print(f"Latência mínima: {min(tempos):.2f} ms")
        print(f"Latência máxima: {max(tempos):.2f} ms")
        print(f"Jitter (variação média entre pings): {jitter_medio:.2f} ms")
        print(f"Jitter (desvio padrão): {desvio_padrao:.2f} ms")
        print("=" * 60 + "\n")

    except FileNotFoundError:
        print("❌ Comando 'ping' não encontrado no sistema.")
    except subprocess.TimeoutExpired:
        print("❌ Teste de jitter demorou demais e foi cancelado.")
    except Exception as e:
        print(f"❌ Erro ao executar teste de jitter: {e}")

def conectar_tcp(cliente):
    """Conecta ao servidor TCP"""
    try:
        cliente.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        cliente.socket.connect((SERVIDOR_IP, PORTA))
        cliente.socket.send(cliente.nome.encode("utf-8"))
        cliente.conectado = True
        cliente.protocolo = "TCP"
        print(f"\n✓ Conectado ao servidor TCP como '{cliente.nome}'\n")
        return True
    except Exception as e:
        print(f"\n❌ Erro ao conectar ao servidor TCP: {e}\n")
        return False

def conectar_udp(cliente):
    """Conecta ao servidor UDP"""
    try:
        cliente.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        cliente.socket.sendto(cliente.nome.encode("utf-8"), (SERVIDOR_IP, PORTA))
        cliente.conectado = True
        cliente.protocolo = "UDP"
        print(f"\n✓ Conectado ao servidor UDP como '{cliente.nome}'\n")
        return True
    except Exception as e:
        print(f"\n❌ Erro ao conectar ao servidor UDP: {e}\n")
        return False

def receber_mensagens(cliente):
    """Thread para receber mensagens do servidor"""
    while cliente.conectado:
        try:
            if cliente.protocolo == "TCP":
                mensagem = cliente.socket.recv(1024).decode("utf-8")
            else:  # UDP
                mensagem, _ = cliente.socket.recvfrom(1024)
                mensagem = mensagem.decode("utf-8")
            
            if not mensagem:
                break
            
            # Processa ping do servidor
            if mensagem.startswith('{') and 'PING' in mensagem:
                try:
                    dados = json.loads(mensagem)
                    pong = criar_pong(dados.get("timestamp"))
                    if cliente.protocolo == "TCP":
                        cliente.socket.send(pong.encode("utf-8"))
                    else:  # UDP
                        cliente.socket.sendto(pong.encode("utf-8"), (SERVIDOR_IP, PORTA))
                except:
                    pass
            else:
                print(f"\n{mensagem}")
                print(f"{cliente.nome}> ", end="", flush=True)
        except Exception as e:
            if cliente.conectado:
                print(f"\n❌ Erro ao receber mensagem: {e}")
            break
    
    cliente.conectado = False

def enviar_mensagens(cliente):
    """Thread para enviar mensagens para o servidor"""
    mostrar_ajuda()
    
    while cliente.conectado:
        try:
            mensagem = input(f"{cliente.nome}> ").strip()

            if not mensagem:
                continue

            # Separa o comando do restante do texto (ex: "/tracert google.com"
            # vira partes[0] = "/tracert" e partes[1] = "google.com")
            partes = mensagem.split(maxsplit=1)
            comando = partes[0].lower() if partes else ""
            argumento = partes[1].strip() if len(partes) > 1 else ""

            if comando == "/sair":
                cliente.conectado = False
                print("\nDesconectando...")
                break

            elif comando == "/stats":
                print(cliente.obter_relatorio())
                continue

            elif comando == "/ping":
                inicio = time.time()
                if cliente.protocolo == "TCP":
                    cliente.socket.send("PING".encode("utf-8"))
                else:
                    cliente.socket.sendto("PING".encode("utf-8"), (SERVIDOR_IP, PORTA))

                # Simula latência (em aplicação real, seria através do pong)
                latencia = (time.time() - inicio) * 1000
                cliente.adicionar_latencia(latencia)
                print(f"🔹 Ping enviado. Latência estimada: {latencia:.2f}ms")
                continue

            elif comando == "/ajuda":
                mostrar_ajuda()
                continue

            # ----- Comandos de diagnóstico de rede do sistema (local) -----
            elif comando == "/meuip":
                mostrar_meu_ip()
                continue
            elif comando == "/gateway":
                mostrar_gateway()
                continue
            elif comando == "/dns":
                mostrar_dns()
                continue
            elif comando == "/tracert":
                executar_tracert(argumento)
                continue
            elif comando == "/nslookup":
                executar_nslookup(argumento)
                continue
            elif comando == "/jitter":
                destino = argumento if argumento else "8.8.8.8"
                executar_jitter_sistema(destino)
                continue

            elif mensagem.startswith("/"):
                print("❌ Comando desconhecido. Digite '/ajuda' para ver os comandos.")
                continue

            # Envia mensagem normal
            cliente.pacotes_enviados += 1
            if cliente.protocolo == "TCP":
                cliente.socket.send(mensagem.encode("utf-8"))
            else:  # UDP
                cliente.socket.sendto(mensagem.encode("utf-8"), (SERVIDOR_IP, PORTA))
        
        except Exception as e:
            print(f"\n❌ Erro ao enviar mensagem: {e}")
            cliente.conectado = False
            break
    
    cliente.conectado = False

def mostrar_ajuda():
    """Mostra comandos disponíveis"""
    print("""
╔═══════════════════════════════════════════════════════════╗
║            COMANDOS DISPONÍVEIS DO CLIENTE                ║
╠═══════════════════════════════════════════════════════════╣
║  /ajuda                  - Mostra esta mensagem           ║
║  /stats                  - Estatísticas de rede do chat   ║
║  /ping                   - Envia um ping para o servidor  ║
╠═══════════════════ Diagnóstico de Rede ═══════════════════╣
║  /meuip                  - Mostra IP local/público        ║
║  /gateway                - Mostra o gateway padrão        ║
║  /dns                    - Mostra servidores DNS          ║
║  /tracert <destino>      - Executa tracert/traceroute     ║
║  /nslookup <destino>     - Executa nslookup               ║
║  /jitter <destino>       - Testa jitter (padrão 8.8.8.8)  ║
╠═══════════════════════════════════════════════════════════╣
║  /sair                   - Desconecta do servidor         ║
║  (outra mensagem)        - Envia para o servidor e chat   ║
╚═══════════════════════════════════════════════════════════╝
    """)

def verificar_porta_aberta(ip, porta, timeout=3):
    """
    Testa rapidamente se é possível abrir uma conexão TCP no
    IP:porta informado, ANTES de tentar a conexão "de verdade".

    Isso é útil para dar uma mensagem de erro mais clara: se essa
    checagem falhar, sabemos que o problema é de rede/servidor
    desligado, e não um bug no protocolo de chat em si.

    Retorna True se a porta respondeu (algo está escutando ali),
    ou False caso contrário (ex: erro 10061 "conexão recusada",
    ou timeout "sem resposta").
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as teste:
            teste.settimeout(timeout)
            resultado = teste.connect_ex((ip, porta))  # 0 = sucesso
            return resultado == 0
    except socket.gaierror:
        # Erro ao resolver o nome/IP informado (ex: digitado errado)
        print(f"❌ Não foi possível resolver o endereço '{ip}'. Verifique se digitou corretamente.")
        return False
    except Exception:
        return False


def conectar():
    """Função principal de conexão"""
    global SERVIDOR_IP

    print("\n ╔═════════════════════════════════════════╗")
    print(" ║        CLIENTE DE CHAT COM TESTES       ║")
    print(" ╚═════════════════════════════════════════╝\n")

    nome = input("Digite seu nome: ").strip()
    if not nome:
        nome = "Usuário"

    # ----- Pergunta o IP do servidor -----
    # Antes o IP do servidor era fixo no topo do arquivo (SERVIDOR_IP).
    # Isso obrigava a editar o código toda vez que o servidor rodasse
    # em outra máquina. Agora perguntamos na hora: se o usuário apenas
    # apertar Enter, mantemos "localhost" (útil para testar servidor e
    # cliente na MESMA máquina).
    ip_digitado = input(f"IP do servidor [Enter = {SERVIDOR_IP}]: ").strip()
    if ip_digitado:
        SERVIDOR_IP = ip_digitado

    protocolo = input("Escolha o protocolo (TCP ou UDP): ").strip().upper()
    
    cliente = ClienteRede(nome)

    # ----- Checagem rápida antes de tentar o protocolo escolhido -----
    # Isso ajuda a diferenciar dois problemas comuns:
    # 1) "Servidor não está rodando / porta fechada" (erro 10061 do Windows)
    # 2) "Servidor rodando, mas em outro endereço/rede"
    #
    # Só faz sentido para TCP: o UDP não tem "handshake" de conexão,
    # então não existe um jeito confiável de testar "a porta está aberta"
    # sem já estar enviando mensagens reais do protocolo do chat.
    if protocolo == "TCP" and not verificar_porta_aberta(SERVIDOR_IP, PORTA):
        print(f"\n❌ Não foi possível alcançar {SERVIDOR_IP}:{PORTA}.")
        print("   Possíveis causas:")
        print("   1) O servidor não está rodando no momento.")
        print("   2) O IP digitado está errado (confira com '/meuip' no SERVIDOR).")
        print("   3) Um firewall está bloqueando a porta 5000.")
        print("   4) Um roteador/rede está bloqueando a comunicação entre as máquinas.\n")
        return

    # Tenta conectar
    if protocolo == "TCP":
        if not conectar_tcp(cliente):
            return
    elif protocolo == "UDP":
        if not conectar_udp(cliente):
            return
    else:
        print("❌ Protocolo inválido.")
        return
    
    # Inicia threads de envio e recebimento
    thread_receber = threading.Thread(target=receber_mensagens, args=(cliente,), daemon=True)
    thread_receber.start()
    
    thread_enviar = threading.Thread(target=enviar_mensagens, args=(cliente,), daemon=True)
    thread_enviar.start()
    
    # Aguarda desconexão
    try:
        while cliente.conectado:
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\n\nInterrupção detectada. Desconectando...")
    finally:
        cliente.conectado = False
        if cliente.socket:
            cliente.socket.close()
        print("Desconectado do servidor.")

if __name__ == "__main__":
    conectar()

import socket
import threading
import time
import json
import statistics
import subprocess  # Usado para executar comandos do sistema operacional (tracert, nslookup, ping)
import platform    # Usado para detectar se estamos no Windows, Linux ou Mac
import re          # Usado para "filtrar" (extrair) informações de dentro de textos com expressões regulares
from collections import deque
from datetime import datetime

# ============= Configuração Geral =============
IP = "0.0.0.0"
PORTA = 5000

# Variáveis do modo TCP
clientes_tcp = []
nomes_tcp = {}
latencias_tcp = {}
jitters_tcp = {}
historico_latencias = {}  # Armazena últimas N latências

# Variáveis do modo UDP
socket_udp = None
enderecos_udp = []
nomes_udp = {}
latencias_udp = {}
jitters_udp = {}
historico_latencias_udp = {}

modo = None  # "TCP" ou "UDP"
TAMANHO_HISTORICO = 50  # Últimas 50 medições para calcular jitter


# ============= Classe para armazenar dados de rede =============
class EstatisticasRede:
    def __init__(self):
        self.latencias = deque(maxlen=TAMANHO_HISTORICO)
        self.tempo_ultimo_ping = None
        self.pacotes_enviados = 0
        self.pacotes_recebidos = 0
        self.pacotes_perdidos = 0
    
    def adicionar_latencia(self, latencia_ms):
        """Adiciona uma medição de latência em ms"""
        self.latencias.append(latencia_ms)
    
    def obter_jitter(self):
        """Calcula o jitter (variação da latência)"""
        if len(self.latencias) < 2:
            return 0
        return statistics.stdev(self.latencias)
    
    def obter_latencia_media(self):
        """Retorna a latência média"""
        if not self.latencias:
            return 0
        return statistics.mean(self.latencias)
    
    def obter_latencia_min_max(self):
        """Retorna latência mínima e máxima"""
        if not self.latencias:
            return 0, 0
        return min(self.latencias), max(self.latencias)
    
    def obter_relatorio(self):
        """Gera um relatório completo de estatísticas"""
        if not self.latencias:
            return "Sem dados de latência"
        
        media = self.obter_latencia_media()
        jitter = self.obter_jitter()
        min_lat, max_lat = self.obter_latencia_min_max()
        taxa_perda = (self.pacotes_perdidos / (self.pacotes_enviados + self.pacotes_recebidos)) * 100 if (self.pacotes_enviados + self.pacotes_recebidos) > 0 else 0
        
        return f"""
        ├─ Latência Média: {media:.2f}ms
        ├─ Latência Mínima: {min_lat:.2f}ms
        ├─ Latência Máxima: {max_lat:.2f}ms
        ├─ Jitter: {jitter:.2f}ms
        ├─ Pacotes Enviados: {self.pacotes_enviados}
        ├─ Pacotes Recebidos: {self.pacotes_recebidos}
        ├─ Taxa de Perda: {taxa_perda:.2f}%
        └─ Medições: {len(self.latencias)}/{TAMANHO_HISTORICO}"""


# ============= Sistema de Teste de Rede =============
def criar_mensagem_ping():
    """Cria uma mensagem de ping com timestamp"""
    return json.dumps({
        "tipo": "PING",
        "timestamp": time.time() * 1000  # em ms
    })

def processar_pong(mensagem_json, endereco_ou_cliente):
    """Processa resposta de pong e calcula latência"""
    try:
        dados = json.loads(mensagem_json)
        if dados.get("tipo") == "PONG":
            tempo_atual = time.time() * 1000
            latencia = tempo_atual - dados.get("timestamp", tempo_atual)
            
            if modo == "TCP":
                if endereco_ou_cliente in latencias_tcp:
                    latencias_tcp[endereco_ou_cliente].adicionar_latencia(latencia)
            elif modo == "UDP":
                if endereco_ou_cliente in latencias_udp:
                    latencias_udp[endereco_ou_cliente].adicionar_latencia(latencia)
            
            return latencia
    except:
        pass
    return None

def teste_ping_periodico_tcp():
    """Envia pings periodicamente para todos os clientes TCP"""
    global clientes_tcp
    while modo == "TCP":
        time.sleep(5)  # Envia ping a cada 5 segundos
        for cliente in list(clientes_tcp):
            try:
                cliente.send(criar_mensagem_ping().encode("utf-8"))
                if cliente in latencias_tcp:
                    latencias_tcp[cliente].pacotes_enviados += 1
            except:
                pass

def teste_ping_periodico_udp():
    """Envia pings periodicamente para todos os clientes UDP"""
    global socket_udp
    while modo == "UDP":
        time.sleep(5)
        for endereco in list(enderecos_udp):
            try:
                socket_udp.sendto(criar_mensagem_ping().encode("utf-8"), endereco)
                if endereco in latencias_udp:
                    latencias_udp[endereco].pacotes_enviados += 1
            except:
                pass

# ============= Comandos do Servidor =============
def listar_estatisticas():
    """Exibe estatísticas de rede de todos os clientes"""
    print("\n" + "="*60)
    print(f"ESTATÍSTICAS DE REDE - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    if modo == "TCP":
        if not clientes_tcp:
            print("Nenhum cliente conectado.")
        else:
            for cliente in clientes_tcp:
                nome = nomes_tcp.get(cliente, "Desconhecido")
                if cliente in latencias_tcp:
                    print(f"\n📊 Cliente: {nome}")
                    print(latencias_tcp[cliente].obter_relatorio())
    
    elif modo == "UDP":
        if not enderecos_udp:
            print("Nenhum cliente conectado.")
        else:
            for endereco in enderecos_udp:
                nome = nomes_udp.get(endereco, str(endereco))
                if endereco in latencias_udp:
                    print(f"\n📊 Cliente: {nome} ({endereco})")
                    print(latencias_udp[endereco].obter_relatorio())
    
    print("\n" + "="*60 + "\n")

def listar_clientes():
    """Lista todos os clientes conectados"""
    print("\n" + "="*60)
    print(f"CLIENTES CONECTADOS - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    if modo == "TCP":
        if not clientes_tcp:
            print("Nenhum cliente conectado.")
        else:
            for i, cliente in enumerate(clientes_tcp, 1):
                nome = nomes_tcp.get(cliente, "Desconhecido")
                latencia_media = latencias_tcp[cliente].obter_latencia_media() if cliente in latencias_tcp else 0
                print(f"{i}. {nome} - Latência Média: {latencia_media:.2f}ms")
    
    elif modo == "UDP":
        if not enderecos_udp:
            print("Nenhum cliente conectado.")
        else:
            for i, endereco in enumerate(enderecos_udp, 1):
                nome = nomes_udp.get(endereco, str(endereco))
                latencia_media = latencias_udp[endereco].obter_latencia_media() if endereco in latencias_udp else 0
                print(f"{i}. {nome} ({endereco}) - Latência Média: {latencia_media:.2f}ms")
    
    print("="*60 + "\n")

def testar_largura_banda():
    """Teste simples de largura de banda"""
    tamanho_mb = 10  # 10 MB de dados de teste
    print(f"\n⚡ Iniciando teste de largura de banda ({tamanho_mb}MB)...")
    
    dados_teste = "X" * (tamanho_mb * 1024 * 1024)
    mensagem = json.dumps({
        "tipo": "TESTE_LARGURA_BANDA",
        "tamanho": len(dados_teste)
    })
    
    inicio = time.time()
    
    if modo == "TCP":
        for cliente in clientes_tcp:
            try:
                cliente.send(mensagem.encode("utf-8"))
            except:
                pass
    elif modo == "UDP":
        for endereco in enderecos_udp:
            try:
                socket_udp.sendto(mensagem.encode("utf-8"), endereco)
            except:
                pass
    
    tempo_decorrido = time.time() - inicio
    velocidade_mbps = (tamanho_mb * 8) / tempo_decorrido if tempo_decorrido > 0 else 0
    print(f"✓ Teste concluído em {tempo_decorrido:.2f}s - Velocidade: {velocidade_mbps:.2f} Mbps\n")


# ============================================================
# ============= DIAGNÓSTICO DE REDE DO SISTEMA ===============
# ============================================================
# Esta seção usa o módulo "subprocess" para chamar comandos que já
# existem no sistema operacional (como ping, tracert, nslookup).
# O módulo "platform" nos diz se estamos rodando em Windows, Linux
# ou macOS, porque o NOME e os PARÂMETROS desses comandos mudam
# de um sistema para o outro.

def sistema_operacional():
    """
    Retorna o nome do sistema operacional atual em letras minúsculas.
    Ex: 'windows', 'linux' ou 'darwin' (darwin = macOS).
    Usamos essa informação para decidir qual comando/parâmetro chamar.
    """
    return platform.system().lower()


def mostrar_meu_ip():
    """
    Mostra o(s) endereço(s) IP local(is) da máquina que está rodando o servidor.

    Como funciona:
    - Criamos um socket UDP "de mentirinha" (não chega a enviar dados de verdade)
      e "conectamos" ele a um endereço externo (8.8.8.8, DNS do Google).
    - O sistema operacional escolhe automaticamente qual interface de rede
      (placa de rede) seria usada para alcançar esse endereço, e é o IP
      dessa interface que conseguimos ler com getsockname().
    - Isso funciona mesmo sem internet real, pois nenhum pacote é
      efetivamente enviado (é só para o SO decidir a rota).
    """
    print("\n" + "=" * 60)
    print("📡 INFORMAÇÕES DE IP")
    print("=" * 60)

    try:
        # Hostname da máquina (nome do computador na rede)
        hostname = socket.gethostname()
        print(f"Hostname: {hostname}")

        # IP "principal" da máquina (o que seria usado para sair para a internet)
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("8.8.8.8", 80))  # Não envia nada, só decide a rota
            ip_local = s.getsockname()[0]
        finally:
            s.close()
        print(f"IP Local (rede): {ip_local}")

        # Todos os IPs associados ao hostname (pode haver mais de uma interface)
        try:
            ips_todos = socket.gethostbyname_ex(hostname)[2]
            print(f"Todos os IPs encontrados: {', '.join(ips_todos)}")
        except Exception:
            pass

        # IP público (o que aparece "para fora" na internet) - requer conexão externa
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
    Mostra o Gateway padrão (o "roteador"/"modem" por onde a rede local
    sai para a internet).

    Como funciona:
    - Cada sistema operacional guarda essa informação em um lugar diferente,
      então chamamos um comando de terminal apropriado para cada SO e
      filtramos (com expressão regular) a linha que contém o gateway.
        • Windows -> comando "ipconfig"
        • Linux   -> comando "ip route"
        • macOS   -> comando "route -n get default"
    """
    print("\n" + "=" * 60)
    print("🌐 GATEWAY PADRÃO")
    print("=" * 60)

    so = sistema_operacional()
    try:
        if so == "windows":
            saida = subprocess.run(["ipconfig"], capture_output=True, text=True, timeout=5).stdout
            # Procura a linha "Default Gateway . . . : 192.168.0.1"
            encontrados = re.findall(r"Default Gateway[^\:]*:\s*([\d\.]+)", saida)
            encontrados = [ip for ip in encontrados if ip]  # remove valores vazios
            if encontrados:
                for ip in encontrados:
                    print(f"Gateway: {ip}")
            else:
                print("Gateway não encontrado.")

        elif so == "linux":
            saida = subprocess.run(["ip", "route"], capture_output=True, text=True, timeout=5).stdout
            # Procura a linha "default via 192.168.0.1 dev eth0"
            encontrado = re.search(r"default via ([\d\.]+)", saida)
            if encontrado:
                print(f"Gateway: {encontrado.group(1)}")
            else:
                print("Gateway não encontrado.")

        elif so == "darwin":  # macOS
            saida = subprocess.run(["route", "-n", "get", "default"], capture_output=True, text=True, timeout=5).stdout
            encontrado = re.search(r"gateway:\s*([\d\.]+)", saida)
            if encontrado:
                print(f"Gateway: {encontrado.group(1)}")
            else:
                print("Gateway não encontrado.")
        else:
            print("Sistema operacional não suportado para esta função.")

    except FileNotFoundError:
        print("❌ Comando do sistema não encontrado.")
    except Exception as e:
        print(f"❌ Erro ao obter gateway: {e}")

    print("=" * 60 + "\n")


def mostrar_dns():
    """
    Mostra os servidores DNS configurados na máquina (os servidores
    responsáveis por traduzir nomes de sites, ex: google.com, em IPs).

        • Windows -> comando "ipconfig /all"
        • Linux   -> lê o arquivo /etc/resolv.conf
        • macOS   -> comando "scutil --dns"
    """
    print("\n" + "=" * 60)
    print("🧭 SERVIDORES DNS")
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
            # No Linux, os DNS configurados normalmente ficam no arquivo resolv.conf
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
            if encontrados:
                # Remove duplicados mantendo a ordem
                vistos = []
                for ip in encontrados:
                    if ip not in vistos:
                        vistos.append(ip)
                        print(f"DNS: {ip}")
            else:
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
    todos os "saltos" (roteadores) pelos quais os pacotes passam até
    chegar lá. Muito útil para descobrir ONDE, no meio do caminho, a
    rede está lenta ou perdendo pacotes.

        • Windows -> comando "tracert"
        • Linux/macOS -> comando "traceroute"

    O resultado é impresso em tempo real, linha por linha, conforme
    o comando vai respondendo (para o usuário não ficar esperando
    "no escuro" até o final).
    """
    if not destino:
        print("❌ Uso correto: /tracert <endereço ou site>  (ex: /tracert google.com)")
        return

    print(f"\n🔍 Executando tracert para '{destino}'... (isso pode demorar alguns segundos)\n")

    so = sistema_operacional()
    comando = ["tracert", "-h", "15", destino] if so == "windows" else ["traceroute", "-m", "15", destino]

    try:
        # Popen + leitura linha a linha para mostrar o progresso em tempo real
        processo = subprocess.Popen(
            comando,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1  # modo "linha a linha"
        )
        for linha in processo.stdout:
            print(linha.rstrip())
        processo.wait(timeout=60)
        print(f"\n✓ Tracert concluído para '{destino}'\n")

    except FileNotFoundError:
        print(f"❌ Comando 'tracert/traceroute' não encontrado no sistema.")
    except subprocess.TimeoutExpired:
        print("❌ Tracert demorou demais e foi cancelado (timeout de 60s).")
    except Exception as e:
        print(f"❌ Erro ao executar tracert: {e}")


def executar_nslookup(destino):
    """
    Executa um "nslookup", que consulta o servidor DNS e retorna o(s)
    endereço(s) IP correspondente(s) a um nome de domínio (ex: google.com).
    Também funciona ao contrário: se você passar um IP, ele tenta
    descobrir o nome associado (DNS reverso).
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
    Executa um teste de JITTER usando o comando "ping" do próprio sistema
    operacional contra um destino externo (por padrão, 8.8.8.8 - DNS do
    Google). Isso é diferente do jitter calculado entre servidor <-> clientes
    do chat: aqui medimos a estabilidade da conexão do SERVIDOR com a
    internet/rede externa.

    O que é jitter?
    - É a VARIAÇÃO do tempo de resposta (latência) entre um pacote e outro.
    - Uma rede "boa" tem latência parecida sempre (jitter baixo).
    - Uma rede instável tem latências que sobem e descem bastante (jitter alto).

    Como calculamos:
    1. Enviamos vários "pings" (pacotes de teste) para o destino.
    2. Guardamos o tempo de resposta (latência) de cada um.
    3. Calculamos a diferença entre pings CONSECUTIVOS.
    4. Tiramos a média dessas diferenças = jitter aproximado.
    """
    print(f"\n📶 Executando teste de jitter contra '{destino}' ({quantidade} pacotes)...\n")

    so = sistema_operacional()
    # No Windows o parâmetro de quantidade é "-n", no Linux/macOS é "-c"
    parametro_quantidade = "-n" if so == "windows" else "-c"

    try:
        resultado = subprocess.run(
            ["ping", parametro_quantidade, str(quantidade), destino],
            capture_output=True, text=True, timeout=quantidade * 2 + 10
        )
        saida = resultado.stdout

        # Extrai os valores de tempo (latência) de cada linha do ping.
        # Windows escreve algo como "tempo=23ms" ou "time=23ms"
        # Linux/macOS escrevem algo como "time=23.4 ms"
        tempos_encontrados = re.findall(r"tempo[=<]([\d\.]+)\s*ms", saida, re.IGNORECASE)
        if not tempos_encontrados:
            tempos_encontrados = re.findall(r"time[=<]([\d\.]+)\s*ms", saida, re.IGNORECASE)

        tempos = [float(t) for t in tempos_encontrados]

        if len(tempos) < 2:
            print("❌ Não foi possível coletar tempo suficiente de resposta.")
            print("Saída bruta do ping para conferência:\n")
            print(saida)
            return

        # Calcula a diferença absoluta entre pings consecutivos
        diferencas = [abs(tempos[i] - tempos[i - 1]) for i in range(1, len(tempos))]
        jitter_medio = sum(diferencas) / len(diferencas)

        # Também mostramos o desvio padrão, outra forma comum de medir jitter
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


# ============= Função para mostrar ajuda =============
def mostrar_ajuda():
    print("""
╔════════════════════════════════════════════════════════════╗
║             COMANDOS DO SERVIDOR DE CHAT                   ║
╠════════════════════════════════════════════════════════════╣
║  /ajuda                    - Mostra esta mensagem          ║
║  /stats                    - Estatísticas de rede do chat  ║
║  /clientes                 - Lista clientes conectados     ║
║  /largura_banda            - Testa largura de banda        ║
╠════════════════════ Diagnóstico de Rede ═══════════════════╣
║  /meuip                    - Mostra IP local/público       ║
║  /gateway                  - Mostra o gateway padrão       ║
║  /dns                      - Mostra servidores DNS         ║
║  /tracert <destino>        - Executa tracert/traceroute    ║
║  /nslookup <destino>       - Executa nslookup              ║
║  /jitter <destino>         - Testa jitter (padrão 8.8.8.8) ║
╠════════════════════════════════════════════════════════════╣
║  /sair                     - Encerra o servidor            ║
║  (outra mensagem)          - Envia para todos os clientes  ║
╚════════════════════════════════════════════════════════════╝
    """)

# ============= Transmissão de Mensagens =============
def transmitir(mensagem, remetente=None):
    """Transmite mensagem para todos os clientes"""
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
                try:
                    socket_udp.sendto(mensagem.encode("utf-8"), endereco)
                except:
                    pass

# ============= Interface de Comandos do Servidor =============
def enviar_mensagens_servidor():
    """Processa comandos e mensagens do servidor"""
    mostrar_ajuda()
    
    while True:
        try:
            entrada = input(">>> ").strip()

            # Separa o comando do restante do texto (ex: "/tracert google.com"
            # vira partes[0] = "/tracert" e partes[1] = "google.com")
            partes = entrada.split(maxsplit=1)
            comando = partes[0].lower() if partes else ""
            argumento = partes[1].strip() if len(partes) > 1 else ""

            if comando == "/sair":
                print("Encerrando servidor...")
                break
            elif comando == "/ajuda":
                mostrar_ajuda()
            elif comando == "/stats":
                listar_estatisticas()
            elif comando == "/clientes":
                listar_clientes()
            elif comando == "/largura_banda":
                testar_largura_banda()

            # ----- Comandos de diagnóstico de rede do sistema -----
            elif comando == "/meuip":
                mostrar_meu_ip()
            elif comando == "/gateway":
                mostrar_gateway()
            elif comando == "/dns":
                mostrar_dns()
            elif comando == "/tracert":
                executar_tracert(argumento)
            elif comando == "/nslookup":
                executar_nslookup(argumento)
            elif comando == "/jitter":
                # Se o usuário não informar destino, usa 8.8.8.8 (DNS do Google) como padrão
                destino = argumento if argumento else "8.8.8.8"
                executar_jitter_sistema(destino)

            elif entrada.startswith("/"):
                print("Comando desconhecido. Digite '/ajuda' para ver os comandos disponíveis.")
            elif entrada:
                transmitir(f"[Servidor]: {entrada}")
                print(f"Mensagem enviada para todos os clientes.")
        except KeyboardInterrupt:
            print("\nInterrupção detectada. Digite /sair para encerrar.")
        except Exception as e:
            print(f"Erro ao processar entrada: {e}")

# ============= Modo TCP =============
def lidar_cliente_tcp(conexao):
    """Gerencia conexão com um cliente TCP"""
    try:
        nome = conexao.recv(1024).decode("utf-8")
        nomes_tcp[conexao] = nome
        clientes_tcp.append(conexao)
        latencias_tcp[conexao] = EstatisticasRede()
        
        print(f"[+] {nome} entrou no chat.")
        transmitir(f"[Servidor] {nome} entrou no chat.")

        while True:
            mensagem = conexao.recv(1024).decode("utf-8")
            if not mensagem:
                break
            
            # Processa ping/pong
            if mensagem.startswith('{') and 'PONG' in mensagem:
                latencia = processar_pong(mensagem, conexao)
                if latencia:
                    latencias_tcp[conexao].pacotes_recebidos += 1
            else:
                print(f"{nome}: {mensagem}")
                transmitir(f"{nome}: {mensagem}", remetente=conexao)

    except Exception as e:
        print(f"Erro ao lidar com cliente: {e}")
    finally:
        if conexao in clientes_tcp:
            clientes_tcp.remove(conexao)
        nome_saiu = nomes_tcp.pop(conexao, "Alguém")
        print(f"[-] {nome_saiu} saiu do chat.")
        transmitir(f"[Servidor] {nome_saiu} saiu do chat.")
        conexao.close()

def iniciar_servidor_tcp():
    """Inicia servidor TCP"""
    servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    servidor.bind((IP, PORTA))
    servidor.listen()
    print(f"\n🚀 Servidor TCP rodando em {IP}:{PORTA}")
    print("Digite '/ajuda' para ver os comandos disponíveis.\n")

    # Inicia threads de ping e input
    thread_ping = threading.Thread(target=teste_ping_periodico_tcp)
    thread_ping.daemon = True
    thread_ping.start()

    thread_input = threading.Thread(target=enviar_mensagens_servidor)
    thread_input.daemon = True
    thread_input.start()

    try:
        while True:
            conexao, endereco = servidor.accept()
            print(f"Nova conexão: {endereco}")
            thread = threading.Thread(target=lidar_cliente_tcp, args=(conexao,))
            thread.start()
    except KeyboardInterrupt:
        print("\nServidor TCP encerrado.")
        servidor.close()

# ============= Modo UDP =============
def iniciar_servidor_udp():
    """Inicia servidor UDP"""
    global socket_udp
    socket_udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    socket_udp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    socket_udp.bind((IP, PORTA))
    print(f"\n🚀 Servidor UDP rodando em {IP}:{PORTA}")
    print("Digite '/ajuda' para ver os comandos disponíveis.\n")

    # Inicia threads de ping e input
    thread_ping = threading.Thread(target=teste_ping_periodico_udp)
    thread_ping.daemon = True
    thread_ping.start()

    thread_input = threading.Thread(target=enviar_mensagens_servidor)
    thread_input.daemon = True
    thread_input.start()

    try:
        while True:
            dados, endereco = socket_udp.recvfrom(1024)
            mensagem = dados.decode("utf-8")

            if endereco not in enderecos_udp:
                enderecos_udp.append(endereco)
                nomes_udp[endereco] = mensagem
                latencias_udp[endereco] = EstatisticasRede()
                print(f"[+] {mensagem} entrou no chat.")
                transmitir(f"[Servidor] {mensagem} entrou no chat.", remetente=endereco)
            else:
                # Processa ping/pong
                if mensagem.startswith('{') and 'PONG' in mensagem:
                    latencia = processar_pong(mensagem, endereco)
                    if latencia:
                        latencias_udp[endereco].pacotes_recebidos += 1
                else:
                    nome = nomes_udp.get(endereco, str(endereco))
                    print(f"{nome}: {mensagem}")
                    transmitir(f"{nome}: {mensagem}", remetente=endereco)
    except KeyboardInterrupt:
        print("\nServidor UDP encerrado.")
        socket_udp.close()

# ============= Inicialização =============
def iniciar_servidor():
    """Escolhe o protocolo e inicia o servidor"""
    global modo
    
    print("╔═══════════════════════════════════════════╗")
    print("║     SERVIDOR DE CHAT COM TESTES DE REDE   ║")
    print("╚═══════════════════════════════════════════╝\n")
    
    protocolo = input("Escolha o protocolo (TCP ou UDP): ").strip().upper()

    if protocolo == "TCP":
        modo = "TCP"
        iniciar_servidor_tcp()
    elif protocolo == "UDP":
        modo = "UDP"
        iniciar_servidor_udp()
    else:
        print("❌ Protocolo inválido. Digite TCP ou UDP.")
        iniciar_servidor()

if __name__ == "__main__":
    iniciar_servidor()

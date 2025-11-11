import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException, 
    ElementClickInterceptedException, StaleElementReferenceException
)
from selenium.webdriver.chrome.options import Options
import os
import logging
import traceback
import random
from datetime import datetime
import re

# CORRIGIR PROBLEMA DE ENCODING
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

class HappyConsignadoBot:
    def __init__(self):
        # Configurar logging SEM EMOJIS
        self.setup_logging()
        
        self.driver = None
        self.dados_file = os.path.join(os.path.expanduser("~"), "Desktop", "DADOS.txt")
        self.resultados_file = os.path.join(os.path.expanduser("~"), "Desktop", "RESULTADO.txt")
        
        # Credenciais
        self.login = "127.917.777-25"
        self.senha = "Inove@1234"
        
        # URLs CORRETAS
        self.url_login = "https://portal.happyconsig.com.br/login"
        self.url_consignado = "https://portal.happyconsig.com.br/consignado-privado"
        
        # Contadores
        self.clientes_processados = 0
        self.erros_totais = 0
        self.cliente_atual_index = 0
        self.dados_clientes = None
        
    def setup_logging(self):
        """Configura sistema de logging SEM EMOJIS"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('bot_happy.log', encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def espera_inteligente(self, segundos_min=2, segundos_max=4):
        """Espera com variação aleatória"""
        tempo = random.uniform(segundos_min, segundos_max)
        time.sleep(tempo)
    
    def normalizar_telefone(self, telefone):
        """Remove formatação do telefone para comparação"""
        # Remove tudo que não é número
        return re.sub(r'\D', '', telefone)
    
    def normalizar_cpf(self, cpf):
        """Remove formatação do CPF para comparação"""
        # Remove tudo que não é número
        return re.sub(r'\D', '', cpf)
    
    def verificar_bloqueio(self):
        """Verifica se a página foi bloqueada pelo Cloudflare - MAIS PRECISO"""
        try:
            page_source = self.driver.page_source.lower()
            
            # Indicadores de BLOQUEIO REAL (mais específicos)
            bloqueio_indicators = [
                "you have been blocked",
                "access denied", 
                "sorry, you have been blocked",
                "why have i been blocked",
                "this website is using a security service",
                "the action you just performed triggered the security solution"
            ]
            
            # Indicadores de FUNCIONAMENTO NORMAL (se existirem, não é bloqueio)
            funcionamento_indicators = [
                "autorizar",
                "consignado",
                "dataprev",
                "formalizacao",
                "happyconsig",
                "login",
                "senha"
            ]
            
            # Verificar se tem indicadores de BLOQUEIO
            for indicator in bloqueio_indicators:
                if indicator in page_source:
                    self.logger.warning(f"BLOQUEIO REAL DETECTADO: {indicator}")
                    return True
            
            # Verificar se tem elementos de FUNCIONAMENTO NORMAL
            elementos_normais = 0
            for indicator in funcionamento_indicators:
                if indicator in page_source:
                    elementos_normais += 1
            
            # Se encontrou vários elementos normais, provavelmente não está bloqueado
            if elementos_normais >= 2:
                return False
            
            # Verificação extra: tentar encontrar elementos específicos da página
            try:
                # Se conseguir encontrar botões ou elementos específicos, não está bloqueado
                elementos_esperados = [
                    '//button[contains(text(), "Autorizar")]',
                    '//button[contains(text(), "Continuar")]',
                    '//*[contains(text(), "Dataprev")]',
                    '//*[@id="root"]'
                ]
                
                elementos_encontrados = 0
                for xpath in elementos_esperados:
                    try:
                        self.driver.find_element(By.XPATH, xpath)
                        elementos_encontrados += 1
                    except:
                        pass
                
                if elementos_encontrados >= 1:
                    self.logger.info("Página carregada normalmente - elementos esperados encontrados")
                    return False
                    
            except Exception as e:
                pass
            
            # Se não encontrou elementos normais nem de bloqueio, verificar título da página
            try:
                title = self.driver.title.lower()
                if title and "blocked" not in title and "access denied" not in title:
                    self.logger.info(f"Página com título normal: {self.driver.title}")
                    return False
            except:
                pass
                
            return False
            
        except Exception as e:
            self.logger.error(f"Erro ao verificar bloqueio: {e}")
            return False

    def reconectar_navegador(self):
        """Fecha e reabre o navegador, refaz login e volta para onde parou"""
        self.logger.info("RECONECTANDO NAVEGADOR...")
        
        try:
            # Fechar navegador atual
            if self.driver:
                self.driver.quit()
                self.logger.info("Navegador fechado")
            
            # Esperar um pouco antes de reconectar
            self.espera_inteligente(5, 8)
            
            # Reabrir navegador
            if not self.inicializar_navegador():
                return False
            
            # Refazer login
            if not self.fazer_login():
                return False
            
            # Voltar para tela de consulta
            if not self.acessar_tela_consulta():
                return False
            
            self.logger.info("RECONEXÃO REALIZADA COM SUCESSO!")
            return True
            
        except Exception as e:
            self.logger.error(f"Erro na reconexão: {e}")
            return False

    def executar_com_reconexao(self, funcao, *args, **kwargs):
        """Executa uma função com verificação de bloqueio e reconexão automática"""
        tentativas = 0
        max_tentativas = 2
        
        while tentativas < max_tentativas:
            try:
                # Verificar se está bloqueado antes de executar
                if self.verificar_bloqueio():
                    self.logger.warning("Bloqueio detectado antes da execução")
                    if not self.reconectar_navegador():
                        return False
                    # Continuar com a execução após reconexão
                
                # Executar a função
                resultado = funcao(*args, **kwargs)
                
                # Verificar se ficou bloqueado após executar
                if self.verificar_bloqueio():
                    self.logger.warning("Bloqueio detectado após execução")
                    if not self.reconectar_navegador():
                        return False
                    # Tentar executar novamente após reconexão
                    tentativas += 1
                    continue
                
                return resultado
                
            except Exception as e:
                self.logger.error(f"Erro durante execução: {e}")
                tentativas += 1
                if tentativas < max_tentativas:
                    self.logger.info(f"Tentando novamente... ({tentativas}/{max_tentativas})")
                    if not self.reconectar_navegador():
                        return False
                else:
                    self.logger.error("Máximo de tentativas atingido")
                    return False
        
        return False

    def carregar_dados(self):
        """Carrega os dados da planilha"""
        try:
            with open(self.dados_file, 'r', encoding='utf-8') as f:
                linhas = f.readlines()
            
            dados = []
            for linha in linhas:
                linha = linha.strip()
                if not linha:
                    continue
                
                partes = linha.split()
                if len(partes) >= 3:
                    cpf = partes[0]
                    telefone = partes[-1]
                    nome = ' '.join(partes[1:-1])
                    
                    dados.append({
                        'cpf': cpf,
                        'nome': nome,
                        'telefone': telefone
                    })
                    self.logger.info(f"Carregado: {nome} - {cpf}")
            
            self.dados_clientes = pd.DataFrame(dados)
            return self.dados_clientes
            
        except Exception as e:
            self.logger.error(f"Erro ao carregar dados: {e}")
            return None

    def inicializar_navegador(self):
        """Inicializa o Chromium com configurações SIMPLES"""
        try:
            chrome_options = Options()
            
            # CONFIGURAÇÕES MÍNIMAS
            chrome_options.add_argument("--start-maximized")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            
            self.driver = webdriver.Chrome(options=chrome_options)
            
            # IR DIRETO PARA A PÁGINA DE LOGIN
            self.driver.get(self.url_login)
            
            self.logger.info("Chromium inicializado com sucesso!")
            self.logger.info(f"URL: {self.url_login}")
            return True
            
        except Exception as e:
            self.logger.error(f"Erro ao inicializar Chromium: {e}")
            return False

    def fazer_login(self):
        """Faz login no sistema"""
        try:
            self.logger.info("Fazendo login...")
            
            # Aguardar a página carregar completamente
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.XPATH, '//*[@id="identifier"]'))
            )
            
            # Campo login
            campo_login = self.driver.find_element(By.XPATH, '//*[@id="identifier"]')
            campo_login.clear()
            campo_login.send_keys(self.login)
            self.espera_inteligente(1, 2)
            
            # Campo senha
            campo_senha = self.driver.find_element(By.XPATH, '//*[@id="password"]')
            campo_senha.clear()
            campo_senha.send_keys(self.senha)
            self.espera_inteligente(1, 2)
            
            # Pressionar Enter para login
            campo_senha.send_keys(Keys.ENTER)
            self.logger.info("Login realizado!")
            self.espera_inteligente(5, 7)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Erro no login: {e}")
            return False

    def acessar_tela_consulta(self):
        """Acessa a tela de consulta após login"""
        try:
            self.logger.info("Acessando tela de consulta...")
            
            # Aguardar carregamento após login
            self.espera_inteligente(3, 5)
            
            # Clicar no botão para ir para consignado
            botao_consignado = WebDriverWait(self.driver, 15).until(
                EC.element_to_be_clickable((By.XPATH, '//*[@id="root"]/div/main/div/div/div[2]/div/div[1]/div/div/div/div[3]/a/button'))
            )
            botao_consignado.click()
            self.logger.info("Clicou no botão Consignado!")
            self.espera_inteligente(5, 7)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Erro ao acessar tela de consulta: {e}")
            return False

    def verificar_e_clicar_nao_descartar(self):
        """Verifica se há proposta em andamento e clica em NÃO-DESCARTAR"""
        try:
            # Verificar se aparece o modal/popup de proposta em andamento
            time.sleep(3)
            
            # XPATH CORRETO do botão "Não - Descartar"
            botao_nao_descartar = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, '/html/body/div[2]/div/div[2]/div/div[1]/div/div[3]/button[1]'))
            )
            
            if botao_nao_descartar:
                self.logger.info("Proposta pendente encontrada - clicando em Nao - Descartar...")
                botao_nao_descartar.click()
                self.logger.info("Clicou em 'Nao - Descartar'")
                self.espera_inteligente(2, 3)
                return True
                
        except:
            pass
            
        return False

    def verificar_preenchimento_campo(self, elemento, texto_esperado, descricao, tipo_campo="texto"):
        """Verifica se o campo foi preenchido corretamente - ACEITA FORMATAÇÃO"""
        try:
            valor_atual = elemento.get_attribute('value')
            
            if tipo_campo == "telefone":
                # Para telefone, compara apenas os números (ignora formatação)
                valor_atual_limpo = self.normalizar_telefone(valor_atual)
                texto_esperado_limpo = self.normalizar_telefone(texto_esperado)
                
                if valor_atual_limpo == texto_esperado_limpo:
                    self.logger.info(f"✓ {descricao} preenchido corretamente: {valor_atual}")
                    return True
                else:
                    self.logger.warning(f"✗ {descricao} NÃO preenchido corretamente. Esperado: '{texto_esperado}' (ou formato similar), Encontrado: '{valor_atual}'")
                    return False
            
            elif tipo_campo == "cpf":
                # Para CPF, compara apenas os números (ignora formatação)
                valor_atual_limpo = self.normalizar_cpf(valor_atual)
                texto_esperado_limpo = self.normalizar_cpf(texto_esperado)
                
                if valor_atual_limpo == texto_esperado_limpo:
                    self.logger.info(f"✓ {descricao} preenchido corretamente: {valor_atual}")
                    return True
                else:
                    self.logger.warning(f"✗ {descricao} NÃO preenchido corretamente. Esperado: '{texto_esperado}' (ou formato similar), Encontrado: '{valor_atual}'")
                    return False
            
            else:
                # Para nome, compara exatamente (sem formatação automática)
                if valor_atual.strip() == texto_esperado.strip():
                    self.logger.info(f"✓ {descricao} preenchido corretamente: '{texto_esperado}'")
                    return True
                else:
                    self.logger.warning(f"✗ {descricao} NÃO preenchido corretamente. Esperado: '{texto_esperado}', Encontrado: '{valor_atual}'")
                    return False
                    
        except Exception as e:
            self.logger.error(f"Erro ao verificar {descricao}: {e}")
            return False

    def limpar_e_preencher_campo(self, elemento, texto, descricao, tipo_campo="texto"):
        """Limpa e preenche campo de forma segura COM VERIFICAÇÃO INTELIGENTE"""
        try:
            # Limpar campo
            elemento.clear()
            time.sleep(0.5)
            elemento.send_keys(Keys.CONTROL + "a")
            elemento.send_keys(Keys.DELETE)
            time.sleep(0.5)
            
            # Preencher campo
            elemento.send_keys(texto)
            time.sleep(1.5)  # Mais tempo para formatação automática
            
            # VERIFICAR se o campo foi preenchido corretamente
            if not self.verificar_preenchimento_campo(elemento, texto, descricao, tipo_campo):
                self.logger.warning(f"Tentando preencher {descricao} novamente...")
                
                # Tentar novamente de forma diferente
                elemento.clear()
                time.sleep(0.5)
                elemento.send_keys(Keys.CONTROL + "a")
                elemento.send_keys(Keys.DELETE)
                time.sleep(0.5)
                
                # Digitar mais devagar para permitir formatação
                for char in texto:
                    elemento.send_keys(char)
                    time.sleep(0.05)
                time.sleep(1.5)
                
                # Verificar novamente
                if not self.verificar_preenchimento_campo(elemento, texto, descricao, tipo_campo):
                    self.logger.error(f"FALHA ao preencher {descricao} mesmo após segunda tentativa")
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Erro ao preencher {descricao}: {e}")
            return False

    def preencher_dados_cliente(self, nome, cpf, telefone):
        """Preenche dados do cliente COM VERIFICAÇÃO INTELIGENTE"""
        try:
            self.logger.info(f"Preenchendo dados para: {nome}")
            
            # Primeiro verificar se há proposta pendente
            self.verificar_e_clicar_nao_descartar()
            
            # VERIFICAÇÃO EXTRA DO NOME - ANTES DE PREENCHER
            self.logger.info("Verificando se campo Nome está acessível...")
            campo_nome = WebDriverWait(self.driver, 15).until(
                EC.element_to_be_clickable((By.XPATH, '//*[@id="customer_nome_cliente"]'))
            )
            
            # Campo Nome - COM VERIFICAÇÃO REFORÇADA
            if not self.limpar_e_preencher_campo(campo_nome, nome, "Nome", "texto"):
                self.logger.error("Falha ao preencher NOME - tentando recarregar página")
                self.driver.refresh()
                self.espera_inteligente(3, 5)
                
                # Tentar novamente após recarregar
                campo_nome = WebDriverWait(self.driver, 15).until(
                    EC.element_to_be_clickable((By.XPATH, '//*[@id="customer_nome_cliente"]'))
                )
                if not self.limpar_e_preencher_campo(campo_nome, nome, "Nome", "texto"):
                    self.logger.error("Falha crítica ao preencher NOME mesmo após recarregar")
                    return False
            
            # Campo CPF - COM VERIFICAÇÃO (aceita formatação)
            campo_cpf = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, '//*[@id="customer_cpf"]'))
            )
            if not self.limpar_e_preencher_campo(campo_cpf, cpf, "CPF", "cpf"):
                return False
            
            # Campo Telefone - COM VERIFICAÇÃO (aceita formatação)
            campo_telefone = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, '//*[@id="customer_telefone_celular"]'))
            )
            if not self.limpar_e_preencher_campo(campo_telefone, telefone, "Telefone", "telefone"):
                return False
            
            # VERIFICAÇÃO FINAL - Confirmar que todos os campos estão preenchidos
            self.logger.info("VERIFICAÇÃO FINAL - Confirmando preenchimento de todos os campos...")
            
            # Verificar NOME novamente (mais importante)
            if not self.verificar_preenchimento_campo(campo_nome, nome, "NOME FINAL", "texto"):
                self.logger.error("❌ NOME não está preenchido corretamente após todas as tentativas")
                return False
            
            if not self.verificar_preenchimento_campo(campo_cpf, cpf, "CPF FINAL", "cpf"):
                self.logger.error("❌ CPF não está preenchido corretamente")
                return False
            
            if not self.verificar_preenchimento_campo(campo_telefone, telefone, "TELEFONE FINAL", "telefone"):
                self.logger.error("❌ TELEFONE não está preenchido corretamente")
                return False
            
            self.logger.info("✅ TODOS os campos preenchidos e verificados com SUCESSO!")
            
            # Botão Consultar
            botao_consultar = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, '//*[@id="root"]/div/main/div/div/div[3]/div/div[2]/div/div/div/div/form/div[2]/div/button'))
            )
            botao_consultar.click()
            self.logger.info("Clicou em Consultar!")
            self.espera_inteligente(4, 6)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Erro ao preencher dados: {e}")
            return False

    def processar_autorizacao_dataprev(self):
        """Processa a autorização Dataprev com verificação MELHORADA"""
        try:
            self.logger.info("Processando autorização Dataprev...")
            self.espera_inteligente(5, 7)
            
            # VERIFICAR BLOQUEIO ANTES DE COMEÇAR (mais tolerante)
            if self.verificar_bloqueio():
                self.logger.warning("Possível bloqueio detectado antes da autorização")
                # Não retornar bloqueado imediatamente, tentar continuar
                self.logger.info("Tentando continuar mesmo com possível bloqueio...")
            
            # Tentar encontrar o link no campo input
            try:
                campo_link = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, '//*[@id="dataprev_url_formalizacao_curta"]'))
                )
                link_url = campo_link.get_attribute('value')
                
                if link_url and link_url.startswith('http'):
                    self.logger.info(f"Link encontrado: {link_url}")
                    
                    # VERIFICAR BLOQUEIO ANTES DE ABRIR LINK (mais tolerante)
                    if self.verificar_bloqueio():
                        self.logger.warning("Possível bloqueio antes de abrir link, mas tentando...")
                    
                    # Abrir nova aba
                    self.driver.execute_script("window.open('');")
                    self.driver.switch_to.window(self.driver.window_handles[1])
                    self.driver.get(link_url)
                    
                    self.espera_inteligente(5, 7)  # Mais tempo para carregar
                    
                    # VERIFICAR BLOQUEIO NA NOVA ABA (MUITO MAIS TOLERANTE)
                    time.sleep(3)  # Esperar carregar
                    
                    # Só considerar bloqueio REAL agora
                    page_source = self.driver.page_source.lower()
                    bloqueio_real = any(indicator in page_source for indicator in [
                        "you have been blocked",
                        "access denied",
                        "sorry, you have been blocked",
                        "why have i been blocked"
                    ])
                    
                    if bloqueio_real:
                        self.logger.error("✅ BLOQUEIO REAL na aba Dataprev! Fechando...")
                        self.driver.close()
                        self.driver.switch_to.window(self.driver.window_handles[0])
                        return "bloqueado"
                    else:
                        self.logger.info("✅ Página Dataprev carregada normalmente - continuando...")
                        
                        # Tentar clicar em Autorizar mesmo se não for bloqueio
                        try:
                            botao_autorizar = WebDriverWait(self.driver, 10).until(
                                EC.element_to_be_clickable((By.XPATH, '//*[@id="root"]/div/main/div/div/div/div/div[2]/div/div/button'))
                            )
                            botao_autorizar.click()
                            self.logger.info("Clicou em Autorizar!")
                            self.espera_inteligente(3, 5)
                        except Exception as e:
                            self.logger.warning(f"Botão Autorizar não encontrado, mas continuando: {e}")
                        
                        # Fechar aba e voltar
                        self.driver.close()
                        self.driver.switch_to.window(self.driver.window_handles[0])
                        self.espera_inteligente(2, 4)
                        
                else:
                    self.logger.warning("Link não encontrado ou inválido - prosseguindo...")
                    
            except Exception as e:
                self.logger.warning(f"Link de autorização não encontrado - prosseguindo: {e}")
            
            # **SEMPRE TENTAR CLICAR EM CONTINUAR** (com ou sem autorização)
            self.logger.info("Clicando em Continuar após autorização...")
            
            try:
                # XPATH CORRETO do botão Continuar
                botao_continuar = WebDriverWait(self.driver, 15).until(
                    EC.element_to_be_clickable((By.XPATH, '//*[@id="root"]/div/main/div/div/div[3]/div/div[2]/div/div/div/div/form/div[4]/div/div/button'))
                )
                
                botao_continuar.click()
                self.logger.info("Clicou em Continuar!")
                self.espera_inteligente(3, 5)
                return True
                
            except Exception as e:
                self.logger.error(f"Erro ao clicar em Continuar: {e}")
                return False
                
        except Exception as e:
            self.logger.error(f"Erro na autorização Dataprev: {e}")
            # Limpeza
            try:
                if len(self.driver.window_handles) > 1:
                    self.driver.close()
                self.driver.switch_to.window(self.driver.window_handles[0])
            except:
                pass
            
            # Tentar continuar mesmo com erro
            try:
                self.logger.info("Tentando clicar em Continuar mesmo com erro...")
                botao_continuar = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, '//*[@id="root"]/div/main/div/div/div[3]/div/div[2]/div/div/div/div/form/div[4]/div/div/button'))
                )
                botao_continuar.click()
                self.logger.info("Clicou em Continuar após erro!")
                return True
            except:
                return False

    def verificar_elegibilidade(self):
        """Verifica se o cliente é elegível"""
        try:
            self.logger.info("Aguardando verificação (30 segundos)...")
            time.sleep(30)
            
            # Verificar se NÃO é elegível
            try:
                mensagem_nao_elegivel = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Não foi desta vez')]"))
                )
                if mensagem_nao_elegivel:
                    self.logger.warning("Cliente NAO elegivel")
                    return False
            except:
                pass
            
            # Verificar se É elegível (botão Continuar)
            try:
                botao_continuar = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, '//*[@id="root"]/div/main/div/div/div[3]/div/div[2]/div/div/div/div/div/div[6]/div/div/div[2]/button'))
                )
                botao_continuar.click()
                self.logger.info("Cliente ELEGIVEL - clicou em Continuar!")
                self.espera_inteligente(2, 4)
                return True
            except:
                self.logger.warning("Cliente NAO elegivel - botao Continuar nao encontrado")
                return False
                
        except Exception as e:
            self.logger.error(f"Erro ao verificar elegibilidade: {e}")
            return False

    def coletar_dados_proposta(self):
        """Coleta dados da proposta"""
        try:
            self.logger.info("Coletando dados da proposta...")
            self.espera_inteligente(3, 5)
            
            # Empregador
            empregador_element = self.driver.find_element(By.XPATH, '//*[@id="root"]/div/main/div/div/div[3]/div/div[2]/div/div/div/div/div/div[2]/div')
            empregador = empregador_element.text
            
            # Valores
            quadro_element = self.driver.find_element(By.XPATH, '//*[@id="root"]/div/main/div/div/div[3]/div/div[2]/div/div/div/div/form/div/div[2]/div/div[2]')
            texto = quadro_element.text
            
            # Processar valores
            linhas = texto.split('\n')
            valores = {
                'empregador': empregador,
                'valor_solicitado': 'Nao encontrado',
                'valor_parcela': 'Nao encontrado',
                'qtd_parcelas': 'Nao encontrado'
            }
            
            for i, linha in enumerate(linhas):
                linha_lower = linha.lower()
                if 'valor solicitado' in linha_lower:
                    valores['valor_solicitado'] = linhas[i+1] if i+1 < len(linhas) else 'N/A'
                elif 'valor da parcela' in linha_lower:
                    valores['valor_parcela'] = linhas[i+1] if i+1 < len(linhas) else 'N/A'
                elif 'parcelas' in linha_lower:
                    valores['qtd_parcelas'] = linhas[i+1] if i+1 < len(linhas) else 'N/A'
            
            return valores
            
        except Exception as e:
            self.logger.error(f"Erro ao coletar dados: {e}")
            return None

    def salvar_resultado(self, cliente, valores):
        """Salva resultado no arquivo"""
        try:
            with open(self.resultados_file, 'a', encoding='utf-8') as f:
                f.write(f"CLIENTE: {cliente['nome']}\n")
                f.write(f"CPF: {cliente['cpf']}\n")
                f.write(f"TELEFONE: {cliente['telefone']}\n")
                f.write(f"EMPREGADOR: {valores['empregador']}\n")
                f.write(f"VALOR SOLICITADO: {valores['valor_solicitado']}\n")
                f.write(f"VALOR PARCELA: {valores['valor_parcela']}\n")
                f.write(f"QUANTIDADE PARCELAS: {valores['qtd_parcelas']}\n")
                f.write("=" * 50 + "\n")
            
            self.logger.info("Resultado salvo!")
            return True
        except Exception as e:
            self.logger.error(f"Erro ao salvar resultado: {e}")
            return False

    def voltar_tela_inicial(self):
        """Volta para tela inicial"""
        try:
            self.logger.info("Voltando para tela inicial...")
            
            # Clicar no botão voltar várias vezes até chegar no início
            for _ in range(5):
                try:
                    botao_voltar = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, '//*[@id="root"]/div/main/div/div/div[3]/div/div[2]/div/div/div/div/div[3]/div/div[1]/button'))
                    )
                    botao_voltar.click()
                    self.espera_inteligente(1, 2)
                except:
                    break
            
            # Verificar se voltou para tela de consulta
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, '//*[@id="customer_nome_cliente"]'))
                )
                self.logger.info("Voltou para tela de consulta!")
                return True
            except:
                # Se não voltou, recarregar a página
                self.driver.get(self.url_consignado)
                self.espera_inteligente(3, 5)
                return True
                
        except Exception as e:
            self.logger.error(f"Erro ao voltar: {e}")
            self.driver.get(self.url_consignado)
            self.espera_inteligente(3, 5)
            return True

    def processar_cliente(self, cliente):
        """Processa um cliente completo com sistema de reconexão"""
        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"PROCESSANDO: {cliente['nome']}")
        self.logger.info(f"{'='*60}")
        
        # ETAPA 1: Verificar proposta pendente
        self.verificar_e_clicar_nao_descartar()
        
        # ETAPA 2: Preencher dados e consultar (COM RECONEXÃO)
        if not self.executar_com_reconexao(self.preencher_dados_cliente, cliente['nome'], cliente['cpf'], cliente['telefone']):
            return False
        
        # ETAPA 3: Autorização Dataprev (COM VERIFICAÇÃO DE BLOQUEIO ESPECIAL)
        resultado_autorizacao = self.processar_autorizacao_dataprev()
        
        if resultado_autorizacao == "bloqueado":
            self.logger.warning("BLOQUEIO durante autorização - necessário reconexão")
            return "bloqueado"
        elif not resultado_autorizacao:
            return False
        
        # ETAPA 4: Verificar elegibilidade (COM RECONEXÃO)
        if not self.executar_com_reconexao(self.verificar_elegibilidade):
            self.logger.warning("Cliente não elegível - próximo...")
            self.driver.get(self.url_consignado)
            self.espera_inteligente(3, 5)
            self.verificar_e_clicar_nao_descartar()
            return "nao_elegivel"
        
        # ETAPA 5: Coletar dados (COM RECONEXÃO)
        valores = self.executar_com_reconexao(self.coletar_dados_proposta)
        if not valores:
            return False
        
        # ETAPA 6: Salvar resultado
        if not self.salvar_resultado(cliente, valores):
            return False
        
        # ETAPA 7: Voltar para início (COM RECONEXÃO)
        if not self.executar_com_reconexao(self.voltar_tela_inicial):
            return False
        
        self.logger.info(f"SUCESSO: {cliente['nome']} processado com SUCESSO!")
        return True

    def executar(self):
        """Executa o fluxo completo com sistema de reconexão"""
        try:
            self.logger.info("INICIANDO ROBÔ HAPPY CONSIGNADO")
            
            # Carregar dados
            dados = self.carregar_dados()
            if dados is None:
                return
            
            # Inicializar navegador
            if not self.inicializar_navegador():
                return
            
            # Fazer login
            if not self.fazer_login():
                return
            
            # Acessar tela de consulta
            if not self.acessar_tela_consulta():
                return
            
            # Processar cada cliente
            for index, cliente in dados.iterrows():
                self.cliente_atual_index = index
                
                try:
                    resultado = self.processar_cliente(cliente)
                    
                    if resultado is True:
                        self.clientes_processados += 1
                        self.logger.info(f"Progresso: {self.clientes_processados}/{len(dados)}")
                    
                    elif resultado == "nao_elegivel":
                        self.logger.info("Cliente não elegível - próximo...")
                    
                    elif resultado == "bloqueado":
                        self.logger.warning("BLOQUEIO - Reconectando e reprocessando cliente...")
                        # Reconectar e tentar o mesmo cliente novamente
                        if self.reconectar_navegador():
                            resultado = self.processar_cliente(cliente)
                            if resultado is True:
                                self.clientes_processados += 1
                                self.logger.info(f"Progresso após reconexão: {self.clientes_processados}/{len(dados)}")
                        else:
                            self.logger.error("Falha na reconexão - próximo cliente")
                    
                    else:
                        self.logger.error("Falha no processamento - próximo cliente")
                    
                    # Pausa entre clientes
                    if index < len(dados) - 1:
                        self.espera_inteligente(2, 4)
                        
                except Exception as e:
                    self.logger.error(f"Erro processando cliente: {e}")
                    # Tentar reconectar em caso de erro
                    if not self.reconectar_navegador():
                        self.logger.error("Não foi possível reconectar")
                        break
            
            self.logger.info(f"FINALIZADO! Processados: {self.clientes_processados}/{len(dados)}")
            
        except Exception as e:
            self.logger.error(f"ERRO CRITICO: {e}")
        finally:
            if self.driver:
                self.driver.quit()
                self.logger.info("Chromium fechado")

# Executar
if __name__ == "__main__":
    bot = HappyConsignadoBot()
    bot.executar()
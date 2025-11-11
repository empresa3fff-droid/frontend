from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional
import uuid
import asyncio
import subprocess
import sys
import os
import json
from datetime import datetime

app = FastAPI(title="Happy Consignado API")

# CORS para o Lovable
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Modelos de dados
class Cliente(BaseModel):
    cpf: str
    nome: str
    telefone: str

class LoteProcessamento(BaseModel):
    clientes: List[Cliente]

class StatusProcessamento(BaseModel):
    lote_id: str
    status: str
    progresso: int
    total_clientes: int
    clientes_processados: int
    resultados: List[Dict] = []
    erro: Optional[str] = None

# Armazenamento em memória
processos_ativos = {}

# Caminho para seu script Python
SCRIPT_PATH = "happy.py"  # AJUSTE ISSO!

def executar_robo_happy(clientes: List[Cliente], lote_id: str):
    """Executa seu robô Selenium com a lista de clientes"""
    try:
        # Criar arquivo temporário com os clientes
        temp_file = f"temp_clientes_{lote_id}.txt"
        with open(temp_file, 'w', encoding='utf-8') as f:
            for cliente in clientes:
                f.write(f"{cliente.cpf} {cliente.nome} {cliente.telefone}\n")
        
        # Atualizar status
        processos_ativos[lote_id].status = "executando"
        processos_ativos[lote_id].progresso = 10
        
        # Executar seu robô (substitua pelo caminho real do seu script)
        resultado = subprocess.run([
            sys.executable, SCRIPT_PATH, 
            "--arquivo", temp_file,
            "--lote", lote_id
        ], capture_output=True, text=True, encoding='utf-8')
        
        # Processar resultados
        if resultado.returncode == 0:
            processos_ativos[lote_id].status = "concluido"
            processos_ativos[lote_id].progresso = 100
            
            # Simular resultados (você vai adaptar para ler do seu arquivo de resultados)
            # Simular resultados COMPLETOS
for i, cliente in enumerate(clientes):
    processos_ativos[lote_id].resultados.append({
        "cpf": cliente.cpf,
        "nome": cliente.nome,
        "telefone": cliente.telefone,
        "status": "aprovado" if i % 3 != 0 else "rejeitado",
        "valor_parcela": "R$ 150,00" if i % 3 != 0 else None,
        "qtd_parcelas": "36" if i % 3 != 0 else None,
        "valor_solicitado": "R$ 5.000,00" if i % 3 != 0 else None,
        "empregador": "EMPRESA EXEMPLO",
        "margem_disponivel": "R$ 8.000,00" if i % 3 != 0 else "R$ 0,00",
        "timestamp": datetime.now().isoformat()
    })
            processos_ativos[lote_id].status = "erro"
            processos_ativos[lote_id].erro = resultado.stderr
            
    except Exception as e:
        processos_ativos[lote_id].status = "erro"
        processos_ativos[lote_id].erro = str(e)
    finally:
        # Limpar arquivo temporário
        try:
            os.remove(temp_file)
        except:
            pass

@app.post("/processar-lote", response_model=StatusProcessamento)
async def processar_lote(lote: LoteProcessamento, background_tasks: BackgroundTasks):
    """Inicia processamento em lote"""
    lote_id = str(uuid.uuid4())
    
    processos_ativos[lote_id] = StatusProcessamento(
        lote_id=lote_id,
        status="iniciando",
        progresso=0,
        total_clientes=len(lote.clientes),
        clientes_processados=0,
        resultados=[]
    )
    
    # Executar em background
    background_tasks.add_task(executar_robo_happy, lote.clientes, lote_id)
    
    return processos_ativos[lote_id]

@app.get("/status/{lote_id}", response_model=StatusProcessamento)
async def get_status(lote_id: str):
    """Obtém status do processamento"""
    if lote_id not in processos_ativos:
        raise HTTPException(status_code=404, detail="Lote não encontrado")
    
    return processos_ativos[lote_id]

@app.get("/resultados/{lote_id}")
async def get_resultados(lote_id: str):
    """Obtém resultados completos"""
    if lote_id not in processos_ativos:
        raise HTTPException(status_code=404, detail="Lote não encontrado")
    
    return processos_ativos[lote_id].resultados

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
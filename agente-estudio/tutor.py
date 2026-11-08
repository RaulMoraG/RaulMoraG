#!/usr/bin/env python3
"""Tutor de IA para estudiar tus materias de la universidad.

Uso:
    export ANTHROPIC_API_KEY=...
    python tutor.py                 # te deja elegir materia
    python tutor.py calculo         # abre una materia directamente

Cada materia es una carpeta dentro de ./materias con tus apuntes (.md, .txt).
Comandos dentro del chat:
    /quiz [tema]    preguntas de práctica (una a la vez)
    /resumen [tema] resumen con lo esencial
    /plan           plan de estudio para tu examen
    /materia        cambiar de materia
    /salir          terminar (se guarda el historial)
"""
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import anthropic

BASE = Path(__file__).parent
MATERIAS = BASE / "materias"
HISTORIAL = BASE / "historial"
MODELO = os.environ.get("TUTOR_MODEL", "claude-sonnet-5-5")
MAX_APUNTES_CHARS = 150_000  # tope de apuntes enviados como contexto

SISTEMA = """Eres un tutor universitario paciente y claro. Hablas en español.
Materia actual: {materia}.

Cómo enseñas:
- Explica desde lo intuitivo hacia lo formal: idea, ejemplo concreto, luego definición/fórmula.
- Usa los apuntes del estudiante como fuente principal y cítalos ("según tus apuntes de <archivo>").
  Si algo no está en los apuntes, dilo y complementa con conocimiento general, indicándolo.
- No inventes datos, fórmulas ni citas. Si no estás seguro, dilo.
- Al final de explicaciones largas, haz UNA pregunta corta para comprobar que entendió.
- Si el estudiante pide resolver un ejercicio de tarea, guíalo con pistas y pasos antes de dar la solución completa,
  salvo que la pida explícitamente para entenderla.
- Sé conciso: nada de relleno.

=== APUNTES DEL ESTUDIANTE ===
{apuntes}
=== FIN DE APUNTES ==="""

COMANDOS = {
    "/quiz": "Hazme un quiz de práctica sobre {t}. Haz UNA pregunta a la vez, espera mi respuesta, corrígeme y luego sigue con la siguiente.",
    "/resumen": "Hazme un resumen con lo esencial de {t}: conceptos clave, fórmulas y errores comunes.",
    "/plan": "Ayúdame a armar un plan de estudio para mi próximo examen de esta materia. Primero pregúntame la fecha del examen y cuánto tiempo tengo por día.",
}


def listar_materias():
    MATERIAS.mkdir(exist_ok=True)
    return sorted(p.name for p in MATERIAS.iterdir() if p.is_dir())


def cargar_apuntes(materia):
    partes, total = [], 0
    for f in sorted((MATERIAS / materia).rglob("*")):
        if f.suffix.lower() not in {".md", ".txt"} or not f.is_file():
            continue
        texto = f.read_text(encoding="utf-8", errors="ignore")
        if total + len(texto) > MAX_APUNTES_CHARS:
            print(f"  (aviso: {f.name} omitido, superas el límite de apuntes)")
            continue
        total += len(texto)
        partes.append(f"--- archivo: {f.relative_to(MATERIAS / materia)} ---\n{texto}")
    return "\n\n".join(partes) or "(sin apuntes todavía: usa conocimiento general)"


def elegir_materia(arg=None):
    materias = listar_materias()
    if not materias:
        sys.exit("No hay materias. Crea una carpeta en ./materias/<nombre> y pon tus apuntes (.md/.txt).")
    if arg:
        for m in materias:
            if arg.lower() in m.lower():
                return m
        print(f"No encontré '{arg}'.")
    for i, m in enumerate(materias, 1):
        print(f"  {i}. {m}")
    while True:
        sel = input("Elige materia (número): ").strip()
        if sel.isdigit() and 1 <= int(sel) <= len(materias):
            return materias[int(sel) - 1]


def guardar(materia, mensajes):
    HISTORIAL.mkdir(exist_ok=True)
    ruta = HISTORIAL / f"{materia}-{datetime.now():%Y%m%d-%H%M}.json"
    ruta.write_text(json.dumps(mensajes, ensure_ascii=False, indent=2), encoding="utf-8")
    return ruta


def turno(client, materia, apuntes, mensajes):
    sistema = SISTEMA.format(materia=materia, apuntes=apuntes)
    respuesta = ""
    with client.messages.stream(model=MODELO, max_tokens=2048, system=sistema, messages=mensajes) as s:
        for texto in s.text_stream:
            print(texto, end="", flush=True)
            respuesta += texto
    print("\n")
    mensajes.append({"role": "assistant", "content": respuesta})


def main():
    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("Falta ANTHROPIC_API_KEY (export ANTHROPIC_API_KEY=...).")
    client = anthropic.Anthropic()
    materia = elegir_materia(sys.argv[1] if len(sys.argv) > 1 else None)
    apuntes, mensajes = cargar_apuntes(materia), []
    print(f"\n📚 Tutor de {materia}. Pregunta lo que quieras. Comandos: /quiz /resumen /plan /materia /salir\n")
    while True:
        try:
            entrada = input("Tú: ").strip()
        except (EOFError, KeyboardInterrupt):
            entrada = "/salir"
        if not entrada:
            continue
        cmd, _, resto = entrada.partition(" ")
        if cmd == "/salir":
            if mensajes:
                print(f"Historial guardado en {guardar(materia, mensajes)}")
            return
        if cmd == "/materia":
            if mensajes:
                guardar(materia, mensajes)
            materia = elegir_materia()
            apuntes, mensajes = cargar_apuntes(materia), []
            continue
        if cmd in COMANDOS:
            entrada = COMANDOS[cmd].format(t=resto or "toda la materia")
        mensajes.append({"role": "user", "content": entrada})
        print("\nTutor: ", end="")
        try:
            turno(client, materia, apuntes, mensajes)
        except anthropic.APIError as e:
            mensajes.pop()
            print(f"\n[error de API: {e}]\n")


if __name__ == "__main__":
    main()

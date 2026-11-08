# Agente de estudio

Tutor de IA en terminal que te explica tus materias usando **tus propios apuntes**.

## Uso
```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=tu_clave
python tutor.py            # o: python tutor.py calculo
```

1. Crea una carpeta por materia: `materias/<materia>/` y mete tus apuntes en `.md` o `.txt`
   (pega el texto de tus PDFs/diapositivas).
2. Pregunta lo que quieras. Comandos: `/quiz [tema]`, `/resumen [tema]`, `/plan`, `/materia`, `/salir`.
3. Los chats se guardan en `historial/`.

Cambia de modelo con `TUTOR_MODEL=...`.

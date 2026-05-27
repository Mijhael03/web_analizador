try:
    from flask import Flask, redirect, render_template, request, session, url_for, send_from_directory
except ModuleNotFoundError as exc:
    raise SystemExit(
        "Falta instalar Flask. Ejecuta: pip install -r requirements.txt"
    ) from exc

import base64
import json
import os
import random
import string
import subprocess
import sys
from datetime import date, datetime, timedelta
import requests
from werkzeug.utils import secure_filename

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
API_BASE = "http://127.0.0.1:8000"
API_SOLICITUDES = f"{API_BASE}/api/solicitudes/solicitudes/"
SCRIPT_ANALISIS = os.getenv("SCRIPT_ANALISIS", "")
VENV_PYTHON = os.getenv(
    "ANALISIS_PYTHON",
    os.path.join(os.path.dirname(SCRIPT_ANALISIS), ".venv", "bin", "python")
    if SCRIPT_ANALISIS
    else "",
)

app = Flask(__name__)
app.secret_key = "clave-secreta-cambiar-en-produccion"

API_LOGIN = "http://127.0.0.1:8000/api/users/profiles/login/"
CAMPANAS = {
    "Scotiabank": ["Prestamos", "Tarjetas"],
    "Movistar": ["Portabilidad", "Movistar Total"],
}
TIPOS_IMAGEN_PERMITIDOS = {
    "image/jpeg": "jpeg",
    "image/png": "png",
    "image/webp": "webp",
}

RESULTADOS_DIR = os.getenv("RESULTADOS_DIR", os.path.join(BASE_DIR, "RESULTADOS"))
SOLICITUDES_DIR = os.getenv("SOLICITUDES_DIR", os.path.join(BASE_DIR, "solicitudes"))


def listar_resultados():
    archivos = []
    try:
        for f in sorted(os.listdir(RESULTADOS_DIR)):
            if f.endswith(".xlsx"):
                ruta = os.path.join(RESULTADOS_DIR, f)
                stats = os.stat(ruta)
                archivos.append({
                    "nombre": f,
                    "fecha": datetime.fromtimestamp(stats.st_mtime).strftime("%d/%m/%Y %H:%M"),
                    "tamano": _formato_tamano(stats.st_size),
                })
    except Exception as e:
        print(f"Error al listar resultados: {e}")
    return archivos


def _formato_tamano(bytes_):
    if bytes_ < 1024:
        return f"{bytes_} B"
    elif bytes_ < 1024 ** 2:
        return f"{bytes_ / 1024:.1f} KB"
    else:
        return f"{bytes_ / 1024 ** 2:.1f} MB"


def calcular_antiguedad(fecha_ingreso):
    hoy = date.today()
    anios = hoy.year - fecha_ingreso.year
    meses = hoy.month - fecha_ingreso.month
    dias = hoy.day - fecha_ingreso.day
    if dias < 0:
        meses -= 1
        mes_anterior = hoy.month - 1 or 12
        anio_mes_anterior = hoy.year if hoy.month > 1 else hoy.year - 1
        dias_en_mes_anterior = (
            date(anio_mes_anterior, mes_anterior % 12 + 1, 1)
            - date(anio_mes_anterior, mes_anterior, 1)
        ).days
        dias += dias_en_mes_anterior
    if meses < 0:
        anios -= 1
        meses += 12
    partes = []
    if anios:
        partes.append(f"{anios} año{'s' if anios != 1 else ''}")
    if meses:
        partes.append(f"{meses} mes{'es' if meses != 1 else ''}")
    if dias or not partes:
        partes.append(f"{dias} día{'s' if dias != 1 else ''}")
    return ", ".join(partes)


def obtener_registros():
    try:
        resp = requests.get(f"{API_BASE}/api/asesores/registros/", timeout=5)
        resp.raise_for_status()
        data = resp.json()
        registros = []
        for r in data:
            ingreso = datetime.strptime(r['fecha_ingreso'], "%Y-%m-%d").date()
            nacimiento = datetime.strptime(r['fecha_nacimiento'], "%Y-%m-%d").date()
            registros.append({
                'id': r['id'],
                'nombres': r['nombres'],
                'apellidos': r['apellidos'],
                'edad': r.get('edad') or '',
                'genero': (r.get('genero') or '').capitalize(),
                'estado_civil': (r.get('estado_civil') or '').replace('_', ' ').capitalize(),
                'fecha_nacimiento': nacimiento.strftime("%d/%m/%Y"),
                'fecha_ingreso': ingreso.strftime("%d/%m/%Y"),
                'antiguedad': calcular_antiguedad(ingreso),
                'campana': r['cliente'],
                'subcampana': r['campana'],
                'foto_perfil': r['foto_perfil'] if r['foto_perfil'] else '',
            })
        return registros
    except Exception as e:
        print(f"Error al obtener registros: {e}")
        return []


def obtener_solicitudes():
    try:
        resp = requests.get(API_SOLICITUDES, timeout=5)
        resp.raise_for_status()
        data = resp.json()
        solicitudes = []
        for s in data:
            solicitudes.append({
                'codigo': s['codigo'],
                'status': s['status'],
                'fecha': s.get('fecha_solicitud', '')[:10] if s.get('fecha_solicitud') else '',
                'resultado_excel': s.get('resultado_excel') or '',
                'mensaje_error': s.get('mensaje_error') or '',
            })
        solicitudes.sort(key=lambda x: x['codigo'], reverse=True)
        return solicitudes
    except Exception as e:
        print(f"Error al obtener solicitudes: {e}")
        return []


@app.route("/", methods=["GET", "POST"])
def login():
    mensaje = ""
    tipo_mensaje = ""
    if request.method == "POST":
        usuario = request.form.get("usuario", "").strip()
        clave = request.form.get("clave", "").strip()
        if not usuario or not clave:
            mensaje = "Completa el usuario y la contraseña."
            tipo_mensaje = "error"
        else:
            try:
                resp = requests.post(API_LOGIN, json={
                    "user_name": usuario,
                    "password": clave,
                }, timeout=5)
                if resp.status_code == 200:
                    data = resp.json()
                    session["usuario"] = usuario
                    session["profile_id"] = data["id"]
                    return redirect(url_for("bienvenida"))
                else:
                    mensaje = "Usuario o contraseña incorrectos."
                    tipo_mensaje = "error"
            except requests.exceptions.ConnectionError:
                mensaje = "No se pudo conectar al servidor. ¿El backend está corriendo?"
                tipo_mensaje = "error"
    return render_template("login.html", mensaje=mensaje, tipo_mensaje=tipo_mensaje)


@app.route("/bienvenida", methods=["GET", "POST"])
def bienvenida():
    usuario = session.get("usuario")
    mensaje = ""
    tipo_mensaje = ""
    vista = request.args.get("vista", "nuevo-registro")
    cliente_filtro = request.args.get("cliente", "").strip()
    campana_filtro = request.args.get("campania", "").strip()

    if not usuario:
        return redirect(url_for("login"))

    if request.method == "POST":
        asesores = request.form.getlist("asesores")
        if asesores:
            fecha_ini = request.form.get("fecha_inicio", "").strip()
            hora_ini = request.form.get("hora_inicio", "").strip()
            fecha_fin = request.form.get("fecha_fin", "").strip()
            hora_fin = request.form.get("hora_fin", "").strip()

            try:
                inicio = datetime.strptime(f"{fecha_ini} {hora_ini}", "%d/%m/%Y %H:%M")
                fin = datetime.strptime(f"{fecha_fin} {hora_fin}", "%d/%m/%Y %H:%M")
                if fin <= inicio:
                    mensaje = "La hora fin debe ser posterior a la hora inicio."
                    tipo_mensaje = "error"
                else:
                    diff_min = int((fin - inicio).total_seconds() / 60)
                    params = {
                        "minuto_inicio": 0,
                        "minuto_fin": diff_min,
                        "ids_empleados": [int(pid) for pid in asesores],
                    }

                    codigo = "SALES" + "".join(random.choices(string.digits, k=5))

                    profile_id = session.get("profile_id")
                    if not profile_id:
                        mensaje = "Debes iniciar sesión nuevamente."
                        tipo_mensaje = "error"
                    else:
                        solicitud_data = {
                            "codigo": codigo,
                            "status": "en espera",
                            "id_user": profile_id,
                            "json_data": params,
                        }
                        resp = requests.post(API_SOLICITUDES, json=solicitud_data, timeout=5)
                        if resp.status_code not in (201, 200):
                            mensaje = f"Error al registrar solicitud en BD."
                            tipo_mensaje = "error"
                        else:
                            os.makedirs(SOLICITUDES_DIR, exist_ok=True)
                            ruta = os.path.join(SOLICITUDES_DIR, f"{codigo}.json")
                            with open(ruta, "w") as f:
                                json.dump(params, f, indent=4)
                            if os.path.exists(VENV_PYTHON) and os.path.exists(SCRIPT_ANALISIS):
                                subprocess.Popen(
                                    [VENV_PYTHON, SCRIPT_ANALISIS, ruta],
                                    stdout=subprocess.DEVNULL,
                                    stderr=subprocess.DEVNULL,
                                )
                                mensaje = f"Análisis iniciado: {codigo}, {params['ids_empleados']}, {diff_min} min"
                            else:
                                mensaje = f"Solicitud registrada: {codigo}. Configura SCRIPT_ANALISIS para ejecutar el análisis."
                            tipo_mensaje = "success"
            except ValueError:
                mensaje = "Formato de fecha/hora inválido. Usa dd/mm/yyyy y HH:MM."
                tipo_mensaje = "error"
            except Exception as e:
                mensaje = f"Error al guardar solicitud: {e}"
                tipo_mensaje = "error"

        elif request.form.get("nombres", "").strip():
            nombres = request.form.get("nombres", "").strip()
            apellidos = request.form.get("apellidos", "").strip()
            edad = request.form.get("edad", "").strip()
            genero = request.form.get("genero", "").strip()
            estado_civil = request.form.get("estado_civil", "").strip()
            fecha_nacimiento = request.form.get("fecha_nacimiento", "").strip()
            fecha_ingreso = request.form.get("fecha_ingreso", "").strip()
            campana = request.form.get("campana", "").strip()
            subcampana = request.form.get("subcampana", "").strip()
            foto = request.files.get("foto_perfil")

            generos_validos = {"masculino", "femenino"}
            estados_civiles_validos = {"soltero", "casado", "conviviente", "divorciado", "viudo"}

            if not nombres or not apellidos or not edad or not genero or not estado_civil or not fecha_nacimiento or not fecha_ingreso or not campana or not subcampana:
                mensaje = "Completa todos los campos del registro."
                tipo_mensaje = "error"
            elif not edad.isdigit() or not 18 <= int(edad) <= 100:
                mensaje = "Ingresa una edad valida entre 18 y 100."
                tipo_mensaje = "error"
            elif genero not in generos_validos:
                mensaje = "Selecciona un genero valido."
                tipo_mensaje = "error"
            elif estado_civil not in estados_civiles_validos:
                mensaje = "Selecciona un estado civil valido."
                tipo_mensaje = "error"
            elif campana not in CAMPANAS or subcampana not in CAMPANAS[campana]:
                mensaje = "Selecciona una campaña y una opción válidas."
                tipo_mensaje = "error"
            elif not foto or not foto.filename:
                mensaje = "Selecciona una foto de perfil."
                tipo_mensaje = "error"
            elif foto.mimetype not in TIPOS_IMAGEN_PERMITIDOS:
                mensaje = "La foto debe ser JPG, PNG o WEBP."
                tipo_mensaje = "error"
            else:
                try:
                    nacimiento = datetime.strptime(fecha_nacimiento, "%d/%m/%Y").date()
                    ingreso = datetime.strptime(fecha_ingreso, "%d/%m/%Y").date()
                    hoy = date.today()
                except ValueError:
                    mensaje = "Ingresa fechas validas."
                    tipo_mensaje = "error"
                else:
                    if nacimiento > hoy:
                        mensaje = "La fecha de nacimiento no puede ser futura."
                        tipo_mensaje = "error"
                    elif ingreso > hoy:
                        mensaje = "La fecha de ingreso no puede ser futura."
                        tipo_mensaje = "error"
                    else:
                        data = {
                            'nombres': nombres,
                            'apellidos': apellidos,
                            'edad': int(edad),
                            'genero': genero,
                            'estado_civil': estado_civil,
                            'fecha_nacimiento': nacimiento.isoformat(),
                            'fecha_ingreso': ingreso.isoformat(),
                            'cliente': campana,
                            'campana': subcampana,
                        }
                        files = {
                            'foto_perfil': (secure_filename(foto.filename), foto.read(), foto.mimetype)
                        }
                        try:
                            resp = requests.post(
                                f"{API_BASE}/api/asesores/registros/",
                                data=data,
                                files=files,
                                timeout=10
                            )
                            if resp.status_code == 201:
                                mensaje = "Registro guardado correctamente."
                                tipo_mensaje = "success"
                                vista = "empleados"
                            else:
                                mensaje = f"Error al guardar en BD."
                                tipo_mensaje = "error"
                        except requests.exceptions.ConnectionError:
                            mensaje = "No se pudo conectar al servidor de base de datos."
                            tipo_mensaje = "error"

    if cliente_filtro and cliente_filtro not in CAMPANAS:
        cliente_filtro = ""
    if cliente_filtro and campana_filtro not in CAMPANAS.get(cliente_filtro, []):
        campana_filtro = ""

    resultados = listar_resultados()

    registros = obtener_registros()

    registros_filtrados = registros
    if vista == "empleados":
        if cliente_filtro:
            registros_filtrados = [
                r for r in registros_filtrados if r["campana"] == cliente_filtro
            ]
        if campana_filtro:
            registros_filtrados = [
                r for r in registros_filtrados if r["subcampana"] == campana_filtro
            ]

    solicitudes = obtener_solicitudes()

    return render_template(
        "dashboard.html",
        usuario=usuario,
        autenticado=True,
        registros=registros_filtrados,
        total_registros=registros_filtrados if vista == "empleados" else registros,
        resultados=resultados,
        solicitudes=solicitudes,
        mensaje=mensaje,
        tipo_mensaje=tipo_mensaje,
        vista=vista,
        campanas=CAMPANAS,
        cliente_filtro=cliente_filtro,
        campana_filtro=campana_filtro,
    )


@app.route("/descargar_resultado/<path:filename>")
def descargar_resultado(filename):
    if not session.get("usuario"):
        return redirect(url_for("login"))
    return send_from_directory(RESULTADOS_DIR, filename, as_attachment=True)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


if __name__ == "__main__":
    app.run(debug=True, port=int(os.getenv("FRONTEND_PORT", "5001")))

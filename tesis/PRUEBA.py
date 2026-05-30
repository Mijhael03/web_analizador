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
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

load_dotenv()
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


def _get_user_name(codigo):
    try:
        resp = requests.get(API_SOLICITUDES, timeout=5)
        resp.raise_for_status()
        for s in resp.json():
            if s['codigo'] == codigo:
                return s.get('user_name') or codigo
    except Exception as e:
        print(f"Error obteniendo usuario: {e}")
    return codigo


def _get_ids_from_solicitud(codigo):
    try:
        resp = requests.get(API_SOLICITUDES, timeout=5)
        resp.raise_for_status()
        for s in resp.json():
            if s['codigo'] == codigo:
                jd = s.get('json_data')
                if jd:
                    return jd.get('ids_empleados')
    except Exception as e:
        print(f"Error obteniendo ids: {e}")
    return None


def generar_pdf_desde_excel(excel_path, codigo):
    import pandas as pd
    from generar_reporte_pdf import generar_reporte_pdf

    df = pd.read_excel(excel_path, sheet_name="Resultados")

    registros = obtener_registros()
    reg_by_id = {reg['id']: reg for reg in registros}

    ids_solicitados = _get_ids_from_solicitud(codigo)

    if df.empty and not ids_solicitados:
        return None

    cliente = ""
    campana = ""
    if not df.empty:
        cliente = df['cliente'].iloc[0] if 'cliente' in df.columns else ""
        campana = df['campana'].iloc[0] if 'campana' in df.columns else ""

    excel_by_name = {}
    for _, r in df.iterrows():
        key = f"{r['nombres']} {r['apellidos']}".lower()
        excel_by_name[key] = r

    resultados_pdf = []

    if ids_solicitados:
        for pid in ids_solicitados:
            reg = reg_by_id.get(pid)
            if reg:
                nombre_completo = f"{reg['nombres']} {reg['apellidos']}"
                key = nombre_completo.lower()
                if key in excel_by_name:
                    r = excel_by_name[key]
                    pct = r['%_estres']
                else:
                    pct = 0

                genero = reg.get('genero', '')
                estado_civil = reg.get('estado_civil', '')
                antiguedad = reg.get('antiguedad', '')
                edad = reg.get('edad', '')

                if pct < 30:
                    estres_texto = "No presenta"
                    estres_clase = "bajo"
                else:
                    estres_texto = "Si presenta"
                    estres_clase = "alto"

                resultados_pdf.append({
                    "asesor": nombre_completo,
                    "estres": estres_texto,
                    "estres_clase": estres_clase,
                    "genero": genero,
                    "edad": edad,
                    "estado_civil": estado_civil,
                    "antiguedad": antiguedad,
                })
    else:
        for _, r in df.iterrows():
            pct = r['%_estres']
            nombre_completo = f"{r['nombres']} {r['apellidos']}"
            reg = reg_by_id.get(r['id']) if 'id' in r.index else None
            if reg:
                genero = reg.get('genero', '')
                estado_civil = reg.get('estado_civil', '')
                antiguedad = reg.get('antiguedad', '')
                edad = reg.get('edad', '')
            else:
                genero = estado_civil = antiguedad = edad = ""

            if pct < 30:
                estres_texto = "No presenta"
                estres_clase = "bajo"
            else:
                estres_texto = "Si presenta"
                estres_clase = "alto"

            resultados_pdf.append({
                "asesor": nombre_completo,
                "estres": estres_texto,
                "estres_clase": estres_clase,
                "genero": genero,
                "edad": edad,
                "estado_civil": estado_civil,
                "antiguedad": antiguedad,
            })

    user_name = _get_user_name(codigo)
    pdf_name = f"{user_name.replace(' ', '_')}_{codigo}.pdf"
    pdf_path = os.path.join(RESULTADOS_DIR, pdf_name)

    datos = {
        "codigo": codigo,
        "fecha_reporte": date.today().strftime("%d/%m/%Y"),
        "cliente": cliente,
        "campana": campana,
        "periodo": "",
        "resumen": (
            f"El analisis identifica los niveles de estres estimados para "
            f"{len(resultados_pdf)} asesores durante el periodo evaluado."
        ),
        "resultados": resultados_pdf,
        "conclusiones": [
            f"Se analizaron {len(resultados_pdf)} asesores.",
            "Los casos que presentan estres requieren seguimiento individual.",
        ],
        "recomendaciones": [
            "Programar pausas activas durante la jornada.",
            "Realizar seguimiento a asesores con indicadores elevados.",
            "Comparar resultados con evaluaciones posteriores.",
        ],
    }

    try:
        generar_reporte_pdf(datos, pdf_path)
        print(f"PDF generado: {pdf_path}")
        return pdf_name
    except Exception as e:
        print(f"Error generando PDF: {e}")
        return None


def listar_resultados():
    generar_pdfs_pendientes()
    archivos = []
    try:
        for f in os.listdir(RESULTADOS_DIR):
            if f.endswith(".pdf"):
                ruta = os.path.join(RESULTADOS_DIR, f)
                stats = os.stat(ruta)
                archivos.append({
                    "nombre": f,
                    "fecha": datetime.fromtimestamp(stats.st_mtime).strftime("%d/%m/%Y %H:%M"),
                    "tamano": _formato_tamano(stats.st_size),
                    "mtime": stats.st_mtime,
                })
        archivos.sort(key=lambda x: x["mtime"], reverse=True)
    except Exception as e:
        print(f"Error al listar resultados: {e}")
    return archivos


def generar_pdfs_pendientes():
    try:
        archivos = os.listdir(RESULTADOS_DIR)
        excels = [f for f in archivos if f.endswith(".xlsx")]
        pdfs = {f for f in archivos if f.endswith(".pdf")}
        for xlsx in excels:
            codigo = os.path.splitext(xlsx)[0]
            if not any(codigo in pdf for pdf in pdfs):
                ruta = os.path.join(RESULTADOS_DIR, xlsx)
                generar_pdf_desde_excel(ruta, codigo)
    except Exception as e:
        print(f"Error generando PDFs pendientes: {e}")


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
            created = s.get('created_at', '')
            fecha_mostrar = ""
            if created:
                try:
                    dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
                    dt = dt.replace(tzinfo=ZoneInfo("UTC")).astimezone(ZoneInfo("America/Lima"))
                    fecha_mostrar = dt.strftime("%d/%m/%Y %H:%M")
                except ValueError:
                    fecha_mostrar = created[:16]
            solicitudes.append({
                'codigo': s['codigo'],
                'status': s['status'],
                'fecha': fecha_mostrar,
                'resultado_excel': s.get('resultado_excel') or '',
                'mensaje_error': s.get('mensaje_error') or '',
                'user_name': s.get('user_name') or '',
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
    vista = request.args.get("vista", "menu")
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
                                user = session.get("usuario", "")
                                mensaje = f"popup:Análisis iniciado|{user}|{codigo}|Tu código de archivo es {codigo}. Para ver en qué etapa está, dirígete al menú de SEGUIMIENTO."
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
            genero = request.form.get("genero", "").strip()
            estado_civil = request.form.get("estado_civil", "").strip()
            fecha_nacimiento = request.form.get("fecha_nacimiento", "").strip()
            fecha_ingreso = request.form.get("fecha_ingreso", "").strip()
            campana = request.form.get("campana", "").strip()
            subcampana = request.form.get("subcampana", "").strip()
            foto = request.files.get("foto_perfil")

            generos_validos = {"masculino", "femenino"}
            estados_civiles_validos = {"soltero", "casado", "conviviente", "divorciado", "viudo"}

            if not nombres or not apellidos or not genero or not estado_civil or not fecha_nacimiento or not fecha_ingreso or not campana or not subcampana:
                mensaje = "Completa todos los campos del registro."
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

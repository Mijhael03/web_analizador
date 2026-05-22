try:
    from flask import Flask, redirect, render_template, request, session, url_for
except ModuleNotFoundError as exc:
    raise SystemExit(
        "Falta instalar Flask. Ejecuta: pip install -r requirements.txt"
    ) from exc

import base64
from datetime import date, datetime


app = Flask(__name__)
app.secret_key = "clave-secreta-cambiar-en-produccion"

USUARIO_VALIDO = "admin"
CLAVE_VALIDA = "1234"
REGISTROS = []
CAMPANAS = {
    "Scotiabank": ["Prestamos", "Tarjetas"],
    "Movistar": ["Portabilidad", "Movistar Total"],
}
TIPOS_IMAGEN_PERMITIDOS = {
    "image/jpeg": "jpeg",
    "image/png": "png",
    "image/webp": "webp",
}


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
            date(anio_mes_anterior, mes_anterior % 12 + 1, 1) - date(anio_mes_anterior, mes_anterior, 1)
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
        elif usuario == USUARIO_VALIDO and clave == CLAVE_VALIDA:
            session["usuario"] = usuario
            return redirect(url_for("bienvenida"))
        else:
            mensaje = "Usuario o contraseña incorrectos."
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
        nombres = request.form.get("nombres", "").strip()
        apellidos = request.form.get("apellidos", "").strip()
        fecha_nacimiento = request.form.get("fecha_nacimiento", "").strip()
        fecha_ingreso = request.form.get("fecha_ingreso", "").strip()
        campana = request.form.get("campana", "").strip()
        subcampana = request.form.get("subcampana", "").strip()
        foto = request.files.get("foto_perfil")

        if not nombres or not apellidos or not fecha_nacimiento or not fecha_ingreso or not campana or not subcampana:
            mensaje = "Completa todos los campos del registro."
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
                nacimiento = datetime.strptime(fecha_nacimiento, "%Y-%m-%d").date()
                ingreso = datetime.strptime(fecha_ingreso, "%Y-%m-%d").date()
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
                    contenido_foto = foto.read()

                    if not contenido_foto:
                        mensaje = "No se pudo leer la foto seleccionada."
                        tipo_mensaje = "error"
                    else:
                        foto_base64 = base64.b64encode(contenido_foto).decode("utf-8")
                        foto_data_url = f"data:{foto.mimetype};base64,{foto_base64}"

                        REGISTROS.append(
                            {
                                "nombres": nombres,
                                "apellidos": apellidos,
                                "fecha_nacimiento": nacimiento.strftime("%d/%m/%Y"),
                                "fecha_ingreso": ingreso.strftime("%d/%m/%Y"),
                                "antiguedad": calcular_antiguedad(ingreso),
                                "campana": campana,
                                "subcampana": subcampana,
                                "foto_perfil": foto_data_url,
                            }
                        )
                        mensaje = "Registro guardado correctamente."
                        tipo_mensaje = "success"
                        vista = "empleados"

    if cliente_filtro and cliente_filtro not in CAMPANAS:
        cliente_filtro = ""

    if cliente_filtro and campana_filtro not in CAMPANAS.get(cliente_filtro, []):
        campana_filtro = ""

    registros_filtrados = REGISTROS

    if vista == "empleados":
        if cliente_filtro:
            registros_filtrados = [
                registro for registro in registros_filtrados if registro["campana"] == cliente_filtro
            ]
        if campana_filtro:
            registros_filtrados = [
                registro for registro in registros_filtrados if registro["subcampana"] == campana_filtro
            ]

    return render_template(
        "dashboard.html",
        usuario=usuario,
        autenticado=True,
        registros=registros_filtrados,
        total_registros=registros_filtrados if vista == "empleados" else REGISTROS,
        mensaje=mensaje,
        tipo_mensaje=tipo_mensaje,
        vista=vista,
        campanas=CAMPANAS,
        cliente_filtro=cliente_filtro,
        campana_filtro=campana_filtro,
    )


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


if __name__ == "__main__":
    app.run(debug=True)

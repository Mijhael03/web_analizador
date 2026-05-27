import os
from datetime import date

from jinja2 import Environment, FileSystemLoader, select_autoescape


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")


def _renderizar_html(datos):
    env = Environment(
        loader=FileSystemLoader(TEMPLATES_DIR),
        autoescape=select_autoescape(["html", "xml"]),
    )
    template = env.get_template("reporte_pdf.html")
    return template.render(**datos)


def generar_reporte_html(datos, salida_html):
    html = _renderizar_html(datos)
    css_path = os.path.join(STATIC_DIR, "reporte_pdf.css")
    with open(css_path, "r", encoding="utf-8") as css_file:
        css = css_file.read()

    html = html.replace("</head>", f"<style>\n{css}\n</style>\n</head>")
    os.makedirs(os.path.dirname(salida_html), exist_ok=True)
    with open(salida_html, "w", encoding="utf-8") as html_file:
        html_file.write(html)
    return salida_html


def generar_reporte_pdf(datos, salida_pdf):
    try:
        from weasyprint import CSS, HTML
    except (ImportError, OSError) as exc:
        raise RuntimeError(
            "No se pudo cargar WeasyPrint. En macOS requiere librerias del sistema "
            "como pango/glib. Puedes generar HTML con generar_reporte_html y "
            "convertirlo a PDF desde Brave/Chrome."
        ) from exc

    html = _renderizar_html(datos)
    css_path = os.path.join(STATIC_DIR, "reporte_pdf.css")

    os.makedirs(os.path.dirname(salida_pdf), exist_ok=True)
    HTML(string=html, base_url=BASE_DIR).write_pdf(
        salida_pdf,
        stylesheets=[CSS(css_path)],
    )
    return salida_pdf


def datos_demo():
    return {
        "codigo": "SALES00001",
        "fecha_reporte": date.today().strftime("%d/%m/%Y"),
        "cliente": "Scotiabank",
        "campana": "Prestamos",
        "periodo": "01/05/2026 09:00 - 01/05/2026 10:00",
        "resumen": (
            "El analisis identifica los niveles de estres estimados para el "
            "periodo evaluado y consolida observaciones para seguimiento."
        ),
        "resultados": [
            {
                "asesor": "Ana Perez",
                "nivel": "Bajo",
                "nivel_clase": "bajo",
                "puntaje": "18",
                "estado": "Dentro del rango esperado",
                "observacion": "Mantiene indicadores estables durante la evaluacion.",
            },
            {
                "asesor": "Luis Garcia",
                "nivel": "Medio",
                "nivel_clase": "medio",
                "puntaje": "42",
                "estado": "Requiere seguimiento",
                "observacion": "Presenta variacion moderada en el periodo evaluado.",
            },
            {
                "asesor": "Maria Torres",
                "nivel": "Alto",
                "nivel_clase": "alto",
                "puntaje": "76",
                "estado": "Atencion prioritaria",
                "observacion": "Se recomienda evaluacion complementaria.",
            },
        ],
        "conclusiones": [
            "La mayoria de asesores se mantiene dentro de rangos controlados.",
            "Los casos con nivel medio o alto deben revisarse individualmente.",
        ],
        "recomendaciones": [
            "Programar pausas activas durante la jornada.",
            "Realizar seguimiento a asesores con indicadores elevados.",
            "Comparar resultados con evaluaciones posteriores.",
        ],
    }


if __name__ == "__main__":
    output_dir = os.path.join(os.path.dirname(BASE_DIR), "RESULTADOS")
    html_output = os.path.join(output_dir, "reporte_demo.html")
    pdf_output = os.path.join(output_dir, "reporte_demo.pdf")
    generar_reporte_html(datos_demo(), html_output)
    print(f"HTML generado: {html_output}")
    try:
        generar_reporte_pdf(datos_demo(), pdf_output)
        print(f"PDF generado: {pdf_output}")
    except RuntimeError as exc:
        print(exc)

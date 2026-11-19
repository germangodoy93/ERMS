"""Base text of the personal data policy and of the authorizations shown at reception.

IMPORTANT: this is a TEMPLATE prepared from the minimum content required by Ley 1581 de
2012 and Decreto 1377 de 2013 (compiled in Decreto 1074 de 2015, art. 2.2.2.25.3.1). It is
not legal advice. The administrator reviews it, may edit it and publishes it; ideally a
lawyer reviews it. Each consent stores the policy version that was accepted.
"""

import re
from string import Template

from app.modules.privacy.catalog import ConsentPurpose

POLICY_TEMPLATE = Template("""\
POLÍTICA DE TRATAMIENTO DE DATOS PERSONALES

1. RESPONSABLE DEL TRATAMIENTO
$legal_name, identificado con NIT $tax_id, con domicilio en $city, dirección $address,
correo electrónico $email y teléfono $phone (en adelante, "el Taller").

2. MARCO LEGAL
Esta política se adopta en cumplimiento de la Ley 1581 de 2012, el Decreto 1377 de 2013
(compilado en el Decreto 1074 de 2015) y demás normas que los modifiquen o complementen.

3. DATOS QUE SE RECOLECTAN
Nombre, tipo y número de documento, teléfono, correo electrónico y dirección del cliente, y
la información de los equipos que entrega para diagnóstico o reparación (marca, modelo,
serial, IMEI y estado). El Taller no solicita contraseñas de los equipos ni accede a
fotografías, documentos u otros archivos personales almacenados en ellos, salvo
autorización expresa y solo en la medida necesaria para el servicio solicitado.

4. FINALIDADES
Los datos se tratan para:
a) Registrar al cliente y los equipos que entrega.
b) Prestar los servicios de diagnóstico, mantenimiento y reparación.
c) Comunicarse con el cliente sobre el estado del servicio, cotizaciones, autorizaciones y
   entrega del equipo.
d) Gestionar garantías, pagos y reclamaciones.
e) Cumplir obligaciones legales, contables y tributarias.
Con autorización adicional y separada del cliente:
f) Tomar fotografías del estado del equipo como evidencia de recepción y reparación.
g) Ejecutar herramientas de diagnóstico sobre el equipo para recolectar información
   técnica del hardware (sin acceder a archivos personales).

5. DERECHOS DEL TITULAR
Como titular de los datos, usted tiene derecho a:
a) Conocer, actualizar y rectificar sus datos personales.
b) Solicitar prueba de la autorización otorgada.
c) Ser informado sobre el uso que se ha dado a sus datos.
d) Presentar quejas ante la Superintendencia de Industria y Comercio (SIC).
e) Revocar la autorización y/o solicitar la supresión de sus datos, cuando no exista un
   deber legal o contractual de conservarlos.
f) Acceder en forma gratuita a sus datos personales.

6. DATOS DE MENORES DE EDAD
Cuando el titular sea menor de edad, la autorización la otorga su representante legal y
el tratamiento respeta el interés superior del menor.

7. ATENCIÓN DE CONSULTAS Y RECLAMOS
Responsable de la atención: $legal_name, a través del correo $email, el teléfono $phone o
en la dirección $address.
- Consultas: se responden en un máximo de diez (10) días hábiles desde su recibo,
  prorrogables por cinco (5) días hábiles más, informando el motivo.
- Reclamos (corrección, actualización, supresión o revocatoria): se responden en un
  máximo de quince (15) días hábiles desde el día siguiente a su recibo, prorrogables por
  ocho (8) días hábiles más, informando el motivo. Si el reclamo está incompleto, se
  solicitará completarlo dentro de los cinco (5) días siguientes; si pasan dos (2) meses
  sin respuesta del solicitante, se entenderá que desistió.
El titular solo puede acudir a la SIC después de agotar este trámite ante el Taller.

8. SEGURIDAD Y CONSERVACIÓN
Los datos se almacenan en sistemas con acceso restringido al personal autorizado. Se
conservan mientras exista relación con el cliente y durante el tiempo exigido por las
normas contables, comerciales y tributarias. Cuando proceda la supresión, los datos
personales se anonimizan y se conserva únicamente la información técnica del servicio.

9. VIGENCIA
Esta política rige a partir de su publicación en el sistema del Taller. Las bases de
datos tendrán la vigencia necesaria para cumplir las finalidades descritas. Cualquier
cambio sustancial será informado a los titulares.
""")

AUTHORIZATION_TEXTS: dict[ConsentPurpose, Template] = {
    ConsentPurpose.DATA_PROCESSING: Template(
        "Autorizo a $name para tratar mis datos personales con el fin de registrarme como "
        "cliente, prestar el servicio técnico solicitado, comunicarse conmigo y cumplir sus "
        "obligaciones legales, conforme a su Política de Tratamiento de Datos Personales "
        "(versión $version). Conozco mis derechos a conocer, actualizar, rectificar y "
        "suprimir mis datos y a revocar esta autorización."
    ),
    ConsentPurpose.PHOTOS: Template(
        "Autorizo a $name para tomar fotografías del estado de mi equipo como evidencia de "
        "recepción y reparación. Las fotografías no incluirán el contenido de la pantalla "
        "con información personal."
    ),
    ConsentPurpose.DIAGNOSTIC_AGENT: Template(
        "Autorizo a $name para ejecutar herramientas de diagnóstico en mi equipo que "
        "recolectan únicamente información técnica del hardware. No se accederá a mis "
        "archivos personales ni se realizarán borrados, formateos o cambios de firmware sin "
        "mi consentimiento expreso adicional."
    ),
}


_LIST_ITEM = re.compile(r"^(?:[a-z]\)|- )")
_HEADING = re.compile(r"^[\dA-ZÁÉÍÓÚÑ .]+$")


def _starts_new_line(previous: str, line: str) -> bool:
    return bool(_LIST_ITEM.match(line) or _HEADING.match(previous) or previous.endswith((".", ":")))


def _unwrap(text: str) -> str:
    """Joins the hard-wrapped lines of the template so the text flows in any width.

    A line is kept on its own after a heading or a finished sentence, and for list items.
    """
    paragraphs = []
    for block in text.strip().split("\n\n"):
        lines: list[str] = []
        for raw in block.splitlines():
            line = raw.strip()
            if lines and not _starts_new_line(lines[-1], line):
                lines[-1] = f"{lines[-1]} {line}"
            else:
                lines.append(line)
        paragraphs.append("\n".join(lines))
    return "\n\n".join(paragraphs) + "\n"


def render_policy(
    *, legal_name: str, tax_id: str, address: str, city: str, phone: str, email: str
) -> str:
    return _unwrap(
        POLICY_TEMPLATE.substitute(
            legal_name=legal_name,
            tax_id=tax_id,
            address=address,
            city=city,
            phone=phone,
            email=email,
        )
    )


def render_authorizations(*, name: str, version: int) -> dict[ConsentPurpose, str]:
    return {
        purpose: text.substitute(name=name, version=version)
        for purpose, text in AUTHORIZATION_TEXTS.items()
    }

# Sistema INEO

## Descripción

INEO es un sistema web para la gestión médica y administrativa de una institución de salud. Permite administrar pacientes, atenciones médicas, camas, estudios, cuentas, diagnósticos, recetas, reportes PDF, respaldos y análisis de información clínica.

## Tecnologías utilizadas

- Python
- Flask
- MongoDB
- PyMongo
- Jinja2
- HTML
- CSS
- JavaScript
- Bootstrap
- bcrypt
- FPDF
- APScheduler
- Apache Spark
- Machine Learning
- Azure App Service
- Azure Cosmos DB para MongoDB
- Azure Blob Storage
- Azure Monitor
- Azure Key Vault

## Módulos principales

### Administrativo

Permite gestionar pacientes, expedientes, cuentas, presupuestos, corte de caja, documentos y censo hospitalario.

### Médico

Permite consultar pacientes, registrar historia clínica, signos vitales, notas médicas, diagnósticos, recetas y solicitar estudios.

### Estudios

Permite gestionar estudios de laboratorio y gabinete, así como sus resultados.

### Configuración

Permite administrar usuarios, roles, camas, servicios, diagnósticos, respaldos y automatización de tareas.

### Rendimiento

Permite visualizar información del sistema como uso de CPU, memoria RAM, disco, usuarios registrados y logs recientes.

## Base de datos

El sistema utiliza MongoDB. Algunas colecciones principales son:

- users
- pacientes
- atencion
- atencion_medicos
- familiares
- camas
- expedientes
- cuenta_paciente
- presupuesto
- cat_servicios
- examenes
- examenes_det
- diagnosticos
- recetas
- signos_vitales
- logs
- counters

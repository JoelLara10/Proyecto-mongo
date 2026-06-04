from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, lit, when, count, mean, stddev, min, max, 
    collect_list, size, expr, substring, length, avg, sum, desc, asc,
    floor, months_between, current_date, to_date, datediff
)
from pyspark.sql.window import Window
from pyspark.ml.feature import VectorAssembler, StandardScaler
from pyspark.ml.clustering import KMeans
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')
import builtins
import pandas as pd
from datetime import datetime
import json
from pathlib import Path

# Carpeta de resultados - usar la misma ruta que en app.py
RESULTS_DIR = Path(__file__).resolve().parent.parent / "processing" / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


class ClinicalAnalytics:
    """
    Análisis clínico hospitalario con Spark
    """

    def __init__(self, spark, db_name):
        self.spark = spark
        self.db_name = db_name
        self.data = {}
        self.results = {}
        self.results_dir = RESULTS_DIR

    def _save_json(self, data, filename):
        filepath = self.results_dir / filename
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        print(f"  💾 Guardado: {filepath}")
        return filepath

    def _to_python_types(self, value):
        """Convert any value to pure Python type to avoid PySpark interference"""
        if isinstance(value, (list, tuple)):
            return [self._to_python_types(v) for v in value]
        elif isinstance(value, dict):
            return {k: self._to_python_types(v) for k, v in value.items()}
        elif isinstance(value, (int, float, str, bool, type(None))):
            return value
        else:
            try:
                return int(value)
            except (ValueError, TypeError):
                try:
                    return float(value)
                except (ValueError, TypeError):
                    return str(value)

    def _spark_to_pandas(self, df):
        if df is None or df.count() == 0:
            return pd.DataFrame()

        date_fields = [f.name for f in df.schema.fields if f.dataType.typeName() in ('date', 'timestamp')]
        for field in date_fields:
            df = df.withColumn(field, col(field).cast('string'))

        return df.toPandas()

    def _normalize_pandas_dates(self, pdf):
        if pdf.empty:
            return pdf

        for col_name in pdf.columns:
            if pd.api.types.is_datetime64_any_dtype(pdf[col_name]):
                pdf[col_name] = pdf[col_name].dt.strftime('%Y-%m-%dT%H:%M:%S').where(pdf[col_name].notna(), None)
            elif pdf[col_name].dtype == 'object':
                try:
                    parsed = pd.to_datetime(pdf[col_name], errors='coerce')
                    if parsed.notna().any():
                        pdf[col_name] = parsed.dt.strftime('%Y-%m-%dT%H:%M:%S').where(parsed.notna(), None)
                except Exception:
                    pass
                pdf[col_name] = pdf[col_name].apply(lambda x: x.isoformat() if hasattr(x, 'isoformat') else x)

        return pdf

    # ==================== CARGA DE DATOS ====================
    def load_clinical_data(self):
        print("\n📊 Cargando datos clínicos...")

        collections = [
            "pacientes", "atencion", "examenes", "examenes_det",
            "diagnosticos", "catalogo_examenes", "camas", "signos_vitales"
        ]

        for coll in collections:
            try:
                self.data[coll] = self.spark.read \
                    .format("mongodb") \
                    .option("database", self.db_name) \
                    .option("collection", coll) \
                    .load()
                print(f"  ✅ {coll}: {self.data[coll].count()} registros")
            except Exception as e:
                print(f"  ❌ Error cargando {coll}: {e}")
                self.data[coll] = None

        return self.data

    # ==================== 1. PREDICCIÓN DE DIABETES ====================
    def predict_diabetes(self):
        print("\n🩺 1. PREDICCIÓN DE DIABETES")

        df_examenes = self.data.get("examenes_det")
        df_pacientes = self.data.get("pacientes")

        if df_examenes is None:
            print("  ❌ No se encontraron datos de exámenes")
            return None

        # Filtrar exámenes relevantes
        examenes_diabetes = df_examenes.filter(
            col("nombre_examen").isin(["Glucosa", "Química Sanguínea", 
                                       "Hemoglobina Glicosilada", "Perfil Lipídico"])
        )

        diabetes_risk = examenes_diabetes.withColumn(
            "riesgo_diabetes",
            when(
                ((col("nombre_examen") == "Glucosa") & (col("subtotal") > 126)) |
                ((col("nombre_examen") == "Hemoglobina Glicosilada") & (col("subtotal") > 6.5)) |
                ((col("nombre_examen") == "Química Sanguínea") & (col("subtotal") > 126)) |
                ((col("nombre_examen") == "Perfil Lipídico") & (col("subtotal") > 200)),
                1
            ).otherwise(0)
        )

        riesgo_por_paciente = diabetes_risk.groupBy("id_examen").agg(
            sum("riesgo_diabetes").alias("marcadores_positivos"),
            count("*").alias("total_examenes"),
            collect_list("nombre_examen").alias("examenes")
        )

        riesgo_clasificado = riesgo_por_paciente.withColumn(
            "nivel_riesgo",
            when(col("marcadores_positivos") >= 2, "ALTO")
            .when(col("marcadores_positivos") == 1, "MEDIO")
            .otherwise("BAJO")
        )

        if df_pacientes:
            riesgo_final = riesgo_clasificado.join(
                df_pacientes.select("Id_exp", "nom_pac", "papell", "fecnac"),
                riesgo_clasificado["id_examen"] == df_pacientes["Id_exp"],
                "left"
            ).withColumn(
                "edad",
                floor(months_between(current_date(), to_date(col("fecnac"))) / 12)
            )
        else:
            riesgo_final = riesgo_clasificado.withColumn("edad", lit(None))

        diabetes_results = {
            "total_pacientes_analizados": riesgo_final.count(),
            "riesgo_alto": riesgo_final.filter(col("nivel_riesgo") == "ALTO").count(),
            "riesgo_medio": riesgo_final.filter(col("nivel_riesgo") == "MEDIO").count(),
            "riesgo_bajo": riesgo_final.filter(col("nivel_riesgo") == "BAJO").count(),
            "pacientes_riesgo_alto": self._safe_to_pandas(
                riesgo_final.filter(col("nivel_riesgo") == "ALTO")
                .select("id_examen", "nom_pac", "papell", "marcadores_positivos", "edad")
            ),
            "criterios_diabetes": {
                "Glucosa": 126, "Hemoglobina Glicosilada": 6.5,
                "Química Sanguínea": 126, "Perfil Lipídico": 200
            }
        }

        self.results['diabetes_prediction'] = diabetes_results
        self._save_json(diabetes_results, "clinical_01_diabetes_prediction.json")
        print(f"  ✅ Riesgo ALTO de diabetes: {diabetes_results['riesgo_alto']}")
        return diabetes_results

    # ==================== 2. PREDICCIÓN DE REINGRESOS ====================
    def predict_readmissions(self):
        print("\n🏥 2. PREDICCIÓN DE REINGRESOS")

        df_atencion = self.data.get("atencion")
        df_pacientes = self.data.get("pacientes")

        if df_atencion is None:
            print("  ❌ No se encontraron datos de atenciones")
            return None

        atenciones_por_paciente = df_atencion.groupBy("Id_exp").agg(
            count("*").alias("total_atenciones"),
            collect_list("especialidad").alias("especialidades")
        )

        readmission_risk = atenciones_por_paciente.withColumn(
            "riesgo_reingreso",
            when(col("total_atenciones") >= 3, "ALTO")
            .when(col("total_atenciones") == 2, "MEDIO")
            .otherwise("BAJO")
        )

        if df_pacientes:
            readmission_risk = readmission_risk.join(
                df_pacientes.select("Id_exp", "nom_pac", "papell"),
                on="Id_exp", how="left"
            )

        readmission_results = {
            "total_pacientes": readmission_risk.count(),
            "riesgo_alto": readmission_risk.filter(col("riesgo_reingreso") == "ALTO").count(),
            "riesgo_medio": readmission_risk.filter(col("riesgo_reingreso") == "MEDIO").count(),
            "riesgo_bajo": readmission_risk.filter(col("riesgo_reingreso") == "BAJO").count(),
            "pacientes_alto_riesgo": self._safe_to_pandas(
                readmission_risk.filter(col("riesgo_reingreso") == "ALTO")
                .select("Id_exp", "nom_pac", "papell", "total_atenciones")
            ),
            "promedio_atenciones": readmission_risk.agg(avg("total_atenciones")).collect()[0][0] or 0
        }

        self.results['readmission_prediction'] = readmission_results
        self._save_json(readmission_results, "clinical_02_readmission_prediction.json")
        print(f"  ✅ Riesgo ALTO de reingreso: {readmission_results['riesgo_alto']}")
        return readmission_results

    # ==================== 3. ANÁLISIS DE OCUPACIÓN ====================
    def analyze_occupancy(self):
        print("\n🛏️ 3. ANÁLISIS DE OCUPACIÓN HOSPITALARIA")
        df_camas = self.data.get("camas")
        df_atencion = self.data.get("atencion")

        if df_camas is None:
            print("  ❌ No se encontraron datos de camas")
            return self._default_occupancy()

        try:
            camas_pandas = self._spark_to_pandas(df_camas)
            if camas_pandas.empty:
                return self._default_occupancy()

            total_camas = len(camas_pandas)
            ocupadas = int(camas_pandas['ocupada'].astype(bool).sum())
            disponibles = total_camas - ocupadas
            porcentaje_general = builtins.round(ocupadas / total_camas * 100, 2) if total_camas > 0 else 0

            # Por área
            ocupacion_por_area = []
            if 'area' in camas_pandas.columns:
                for area in camas_pandas['area'].dropna().unique():
                    subset = camas_pandas[camas_pandas['area'] == area]
                    total = len(subset)
                    ocup = int(subset['ocupada'].astype(bool).sum())
                    porc = builtins.round(ocup / total * 100, 2) if total > 0 else 0
                    ocupacion_por_area.append({
                        'area': str(area), 'total_camas': total,
                        'ocupadas': ocup, 'disponibles': total - ocup,
                        'porcentaje_ocupacion': porc
                    })

            # Demanda por especialidad
            demanda_dict = []
            if df_atencion is not None:
                at_pandas = self._spark_to_pandas(df_atencion)
                if not at_pandas.empty and 'especialidad' in at_pandas.columns:
                    demanda = at_pandas.groupby(['especialidad', 'area']).size().reset_index(name='total_atenciones')
                    demanda = demanda.sort_values('total_atenciones', ascending=False)
                    demanda_dict = demanda.head(10).to_dict('records')

            occupancy_results = {
                "total_camas": total_camas,
                "camas_ocupadas": ocupadas,
                "camas_disponibles": disponibles,
                "porcentaje_ocupacion_general": porcentaje_general,
                "ocupacion_por_area": ocupacion_por_area,
                "demanda_por_especialidad": demanda_dict,
                "areas_criticas": [a for a in ocupacion_por_area if a['porcentaje_ocupacion'] > 80]
            }

            self.results['occupancy_analysis'] = occupancy_results
            self._save_json(occupancy_results, "clinical_03_occupancy_analysis.json")
            print(f"  ✅ Ocupación general: {porcentaje_general}%")
            return occupancy_results

        except Exception as e:
            print(f"  ❌ Error en análisis de ocupación: {e}")
            return self._default_occupancy()

    def _default_occupancy(self):
        default = {"total_camas": 0, "camas_ocupadas": 0, "camas_disponibles": 0,
                   "porcentaje_ocupacion_general": 0, "ocupacion_por_area": [],
                   "demanda_por_especialidad": [], "areas_criticas": []}
        self.results['occupancy_analysis'] = default
        self._save_json(default, "clinical_03_occupancy_analysis.json")
        return default

    # ==================== 4. DETECCIÓN DE ANOMALÍAS ====================
    def detect_anomalies(self):
        print("\n⚠️ 4. DETECCIÓN DE ANOMALÍAS CLÍNICAS")
        df_examenes = self.data.get("examenes_det")
        df_signos = self.data.get("signos_vitales")

        anomalies = {"examenes_anomalos": [], "signos_anomalos": [], "inconsistencias": []}

        try:
            if df_examenes is not None:
                stats = df_examenes.groupBy("nombre_examen").agg(
                    avg("precio").alias("precio_promedio"), stddev("precio").alias("precio_std"),
                    avg("subtotal").alias("subtotal_promedio"), stddev("subtotal").alias("subtotal_std")
                )
                examenes_con_stats = df_examenes.join(stats, "nombre_examen", "left")
                examenes_anomalos = examenes_con_stats.filter(
                    (col("precio") > col("precio_promedio") + 2 * col("precio_std")) |
                    (col("precio") < col("precio_promedio") - 2 * col("precio_std"))
                )
                anomalies["examenes_anomalos"] = self._safe_to_pandas(examenes_anomalos)

            if df_signos is not None:
                signos_anomalos = df_signos.filter(
                    (col("fc").cast("double") < 60) | (col("fc").cast("double") > 100) |
                    (col("fr").cast("double") < 12) | (col("fr").cast("double") > 20) |
                    (col("temp").cast("double") < 36.1) | (col("temp").cast("double") > 37.2) |
                    (col("spo2").cast("double") < 95)
                )
                anomalies["signos_anomalos"] = self._safe_to_pandas(signos_anomalos)

            if df_examenes is not None and "fecha" in [f.name for f in df_examenes.schema.fields]:
                pendientes = df_examenes.filter(
                    (col("estado") == "PENDIENTE") & (datediff(current_date(), to_date(col("fecha"))) > 7)
                )
                anomalies["inconsistencias"] = self._safe_to_pandas(pendientes)

        except Exception as e:
            print(f"  ⚠️ Error en detección de anomalías: {e}")

        results = {
            "total_anomalias_examenes": len(anomalies["examenes_anomalos"]),
            "total_anomalias_signos": len(anomalies["signos_anomalos"]),
            "total_inconsistencias": len(anomalies["inconsistencias"]),
            "detalles": anomalies,
            "rangos_referencia": {"fc": (60,100), "fr":(12,20), "temp":(36.1,37.2), "spo2":(95,100)}
        }

        self.results['anomaly_detection'] = results
        self._save_json(results, "clinical_04_anomaly_detection.json")
        print(f"  ✅ Anomalías: {results['total_anomalias_examenes']} exámenes | {results['total_anomalias_signos']} signos")
        return results

    def _safe_to_pandas(self, df):
        if df is None or df.count() == 0:
            return []

        try:
            pdf = self._spark_to_pandas(df)
            pdf = self._normalize_pandas_dates(pdf)
            pdf = pdf.where(pd.notnull(pdf), None)
            return pdf.to_dict('records')

        except Exception as e:
            print(f"⚠️ Error convirtiendo a pandas: {e}")
            return []

    # ==================== 5. SEGMENTACIÓN DE PACIENTES ====================
    def segment_patients(self):
        print("\n📊 5. SEGMENTACIÓN DE PACIENTES")
        df_pacientes = self.data.get("pacientes")
        df_atencion = self.data.get("atencion")

        if df_pacientes is None:
            print("  ❌ No hay datos de pacientes")
            return None

        pacientes = df_pacientes.withColumn(
            "edad", floor(months_between(current_date(), to_date(col("fecnac"))) / 12)
        )

        if df_atencion:
            atenciones = df_atencion.groupBy("Id_exp").agg(count("*").alias("num_atenciones"))
            pacientes = pacientes.join(atenciones, "Id_exp", "left").fillna({"num_atenciones": 0})

        pacientes_ml = pacientes.select(
            col("Id_exp"), col("edad").cast("double"), col("num_atenciones").cast("double")
        ).na.drop()

        if pacientes_ml.count() < 3:
            print("  ⚠️ Datos insuficientes para clustering")
            return None

        assembler = VectorAssembler(inputCols=["edad", "num_atenciones"], outputCol="features")
        df_features = assembler.transform(pacientes_ml)

        scaler = StandardScaler(inputCol="features", outputCol="scaled_features")
        scaler_model = scaler.fit(df_features)
        df_scaled = scaler_model.transform(df_features)

        kmeans = KMeans(featuresCol="scaled_features", k=3, seed=42)
        model = kmeans.fit(df_scaled)
        clustered = model.transform(df_scaled)

        stats = clustered.groupBy("prediction").agg(
            avg("edad").alias("edad_prom"), avg("num_atenciones").alias("atenc_prom"), count("*").alias("total")
        ).toPandas().to_dict('records')

        segmentos = []
        for s in stats:
            if s['atenc_prom'] > 2:
                nombre = "ALTA FRECUENCIA"
            elif s['edad_prom'] > 50:
                nombre = "ADULTO MAYOR"
            else:
                nombre = "BAJA FRECUENCIA"
            
            segmentos.append({
                "segmento_id": int(s['prediction']),
                "nombre_segmento": nombre,
                "edad_promedio": builtins.round(float(s['edad_prom']), 1),
                "atenciones_promedio": builtins.round(float(s['atenc_prom']), 2),
                "total_pacientes": int(s['total'])
            })

        result = {"num_segmentos": 3, "segmentos": segmentos, "metodo": "K-Means"}
        self.results['patient_segmentation'] = result
        self._save_json(result, "clinical_05_patient_segmentation.json")
        print(f"  ✅ Segmentos creados: {len(segmentos)}")
        return result

    # ==================== 6. INTELIGENCIA CLÍNICA ====================
    def clinical_intelligence(self):
        print("\n🧠 6. INTELIGENCIA CLÍNICA")
        
        recomendaciones = []
        hallazgos = []
        correlaciones = []
        
        # Análisis de Diabetes
        diabetes = self.results.get('diabetes_prediction', {})
        if diabetes:
            riesgo_alto = diabetes.get('riesgo_alto', 0)
            riesgo_medio = diabetes.get('riesgo_medio', 0)
            
            if riesgo_alto > 0:
                hallazgos.append({
                    "patron": "Riesgo de Diabetes Elevado",
                    "descripcion": f"{riesgo_alto} pacientes con alto riesgo de diabetes detectados"
                })
                recomendaciones.append("🔴 Implementar programa urgente de prevención de diabetes")
                recomendaciones.append("🔴 Intensificar controles de glucosa en pacientes de alto riesgo")
                correlaciones.append({
                    "condicion": "Diabetes + Hipertensión",
                    "riesgo_asociado": "Enfermedad cardiovascular severa",
                    "recomendacion": "Seguimiento cardiológico cada 3 meses"
                })
            elif riesgo_medio > 0:
                hallazgos.append({
                    "patron": "Riesgo de Diabetes Moderado",
                    "descripcion": f"{riesgo_medio} pacientes con riesgo moderado de diabetes"
                })
                recomendaciones.append("🟡 Fortalecer prevención de diabetes en población general")
        
        # Análisis de Reingresos
        readmission = self.results.get('readmission_prediction', {})
        if readmission:
            riesgo_alto_reingreso = readmission.get('riesgo_alto', 0)
            promedio_atenciones = readmission.get('promedio_atenciones', 0)
            
            if riesgo_alto_reingreso > 0:
                hallazgos.append({
                    "patron": "Alto Riesgo de Reingresos",
                    "descripcion": f"{riesgo_alto_reingreso} pacientes con alto riesgo de reingreso"
                })
                recomendaciones.append("🔴 Implementar programa de seguimiento post-alta para pacientes crónicos")
                recomendaciones.append("🔴 Establecer contactos de seguimiento en primeras 48 horas post-alta")
            
            if promedio_atenciones > 2:
                correlaciones.append({
                    "condicion": "Pacientes Multiataques",
                    "riesgo_asociado": "Mayor consumo de recursos hospitalarios",
                    "recomendacion": "Coordinar con atención primaria para manejo ambulatorio"
                })
        
        # Análisis de Ocupación
        occupancy = self.results.get('occupancy_analysis', {})
        if occupancy:
            porcentaje = occupancy.get('porcentaje_ocupacion_general', 0)
            areas_criticas = occupancy.get('areas_criticas', [])
            
            if porcentaje > 80:
                hallazgos.append({
                    "patron": "Ocupación Hospitalaria Crítica",
                    "descripcion": f"Ocupación general: {porcentaje}% - Por encima del umbral seguro"
                })
                recomendaciones.append(f"🔴 CRÍTICO: Ocupación al {porcentaje}% - Activar plan de contingencia")
                recomendaciones.append("🔴 Agilizar egresos de pacientes estables")
            elif porcentaje > 70:
                hallazgos.append({
                    "patron": "Ocupación Hospitalaria Alta",
                    "descripcion": f"Ocupación general: {porcentaje}% - Acercándose al límite"
                })
                recomendaciones.append(f"🟡 Optimizar ocupación hospitalaria (actual: {porcentaje}%)")
            
            if areas_criticas:
                recomendaciones.append(f"🟡 Revisar protocolos de {', '.join([a['area'] for a in areas_criticas])} - ocupación > 80%")
        
        # Análisis de Anomalías
        anomalies = self.results.get('anomaly_detection', {})
        if anomalies:
            anomalias_examenes = anomalies.get('total_anomalias_examenes', 0)
            anomalias_signos = anomalies.get('total_anomalias_signos', 0)
            
            if anomalias_signos > 0:
                hallazgos.append({
                    "patron": "Anomalías en Signos Vitales",
                    "descripcion": f"{anomalias_signos} registros con valores anómalos detectados"
                })
                recomendaciones.append("🔴 Reforzar monitoreo de signos vitales en UCI/áreas críticas")
                recomendaciones.append("🟡 Revisar calibración de dispositivos de monitoreo")
            
            if anomalias_examenes > 0:
                recomendaciones.append(f"🟡 Auditar {anomalias_examenes} exámenes con valores atípicos")
        
        # Análisis de Segmentación
        segmentation = self.results.get('patient_segmentation', {})
        if segmentation:
            segmentos = segmentation.get('segmentos', [])
            
            for seg in segmentos:
                if seg['nombre_segmento'] == 'ADULTO MAYOR':
                    if seg['total_pacientes'] > 5:
                        recomendaciones.append(f"🟡 Implementar programas geriátricos para {seg['total_pacientes']} adultos mayores")
                        correlaciones.append({
                            "condicion": "Adultos Mayores + Múltiples Comorbilidades",
                            "riesgo_asociado": "Internaciones prolongadas y complicaciones",
                            "recomendacion": "Equipo multidisciplinario: geriatra, enfermería, nutrición"
                        })
                elif seg['nombre_segmento'] == 'ALTA FRECUENCIA':
                    if seg['total_pacientes'] > 2:
                        recomendaciones.append(f"🟡 Pacientes de alta frecuencia ({seg['total_pacientes']}): Crear programas de manejo crónico")
        
        # Agregar recomendaciones por defecto si no hay hallazgos críticos
        if not hallazgos:
            hallazgos.append({
                "patron": "Análisis General",
                "descripcion": "Sistema clínico funcionando dentro de parámetros normales"
            })
            recomendaciones.append("✅ Mantener protocolos actuales de calidad asistencial")
            recomendaciones.append("✅ Continuar monitoreo periódico de indicadores")
        
        if not correlaciones:
            correlaciones.append({
                "condicion": "Estado General",
                "riesgo_asociado": "Normal",
                "recomendacion": "Vigilancia clínica rutinaria"
            })
        
        result = {
            "patrones_encontrados": hallazgos,
            "correlaciones_clinicas": correlaciones,
            "recomendaciones": recomendaciones[:10],
            "fecha_analisis": datetime.now().isoformat(),
            "total_recomendaciones": len(recomendaciones)
        }

        self.results['clinical_intelligence'] = result
        self._save_json(result, "clinical_06_clinical_intelligence.json")
        print("  ✅ Inteligencia clínica generada")
        return result

    # ==================== 7. VISUALIZACIONES ====================
    def generate_clinical_visualizations(self):
        print("\n📊 Generando visualizaciones...")
        viz_dir = self.results_dir / "clinical_visualizations"
        viz_dir.mkdir(exist_ok=True)
        
        viz_data = {"graficos_generados": []}
        
        try:
            # Gráfico 1: Distribución de Riesgo de Diabetes
            diabetes = self.results.get('diabetes_prediction', {})
            if diabetes:
                fig, ax = plt.subplots(figsize=(10, 6))
                riesgos = ['BAJO', 'MEDIO', 'ALTO']
                valores = [
                    int(diabetes.get('riesgo_bajo', 0)),
                    int(diabetes.get('riesgo_medio', 0)),
                    int(diabetes.get('riesgo_alto', 0))
                ]
                colores = ['#48bb78', '#ed8936', '#f56565']
                
                bars = ax.bar(riesgos, valores, color=colores, edgecolor='black', linewidth=1.5)
                ax.set_ylabel('Número de Pacientes', fontsize=12, fontweight='bold')
                ax.set_title('Distribución de Riesgo de Diabetes', fontsize=14, fontweight='bold')
                max_val = builtins.max(valores) if valores else 5
                ax.set_ylim(0, max_val + 2)
                
                for bar in bars:
                    height = bar.get_height()
                    if height > 0:
                        ax.text(bar.get_x() + bar.get_width()/2., height,
                               f'{int(height)}', ha='center', va='bottom', fontweight='bold')
                
                plt.tight_layout()
                filepath = viz_dir / "01_diabetes_risk_distribution.png"
                plt.savefig(filepath, dpi=150, bbox_inches='tight')
                plt.close()
                viz_data['graficos_generados'].append(str(filepath))
                print(f"  ✅ Gráfico diabetes: {filepath.name}")
        
        except Exception as e:
            print(f"  ⚠️ Error generando gráfico diabetes: {e}")
        
        try:
            # Gráfico 2: Ocupación Hospitalaria por Área
            occupancy = self.results.get('occupancy_analysis', {})
            areas_data = occupancy.get('ocupacion_por_area', [])
            
            if areas_data and len(areas_data) > 0:
                fig, ax = plt.subplots(figsize=(12, 6))
                areas = [a['area'] for a in areas_data]
                porcentajes = [a['porcentaje_ocupacion'] for a in areas_data]
                
                colores_ocu = ['#f56565' if p > 80 else '#ed8936' if p > 70 else '#48bb78' for p in porcentajes]
                
                bars = ax.barh(areas, porcentajes, color=colores_ocu, edgecolor='black', linewidth=1.5)
                ax.set_xlabel('Porcentaje de Ocupación (%)', fontsize=12, fontweight='bold')
                ax.set_title('Ocupación Hospitalaria por Área', fontsize=14, fontweight='bold')
                ax.set_xlim(0, 100)
                ax.axvline(x=80, color='red', linestyle='--', linewidth=2, label='Umbral Crítico (80%)')
                
                for i, (bar, val) in enumerate(zip(bars, porcentajes)):
                    ax.text(val + 2, i, f'{val}%', va='center', fontweight='bold')
                
                ax.legend()
                plt.tight_layout()
                filepath = viz_dir / "02_occupancy_by_area.png"
                plt.savefig(filepath, dpi=150, bbox_inches='tight')
                plt.close()
                viz_data['graficos_generados'].append(str(filepath))
                print(f"  ✅ Gráfico ocupación: {filepath.name}")
        
        except Exception as e:
            print(f"  ⚠️ Error generando gráfico ocupación: {e}")
        
        try:
            # Gráfico 3: Anomalías Detectadas
            anomalies = self.results.get('anomaly_detection', {})
            anomalia_types = ['Exámenes Anómalos', 'Signos Vitales Anómalos', 'Inconsistencias']
            anomalia_values = [
                int(anomalies.get('total_anomalias_examenes', 0)),
                int(anomalies.get('total_anomalias_signos', 0)),
                int(anomalies.get('total_inconsistencias', 0))
            ]
            colores_anom = ['#667eea', '#f56565', '#ed8936']
            
            fig, ax = plt.subplots(figsize=(10, 6))
            bars = ax.bar(anomalia_types, anomalia_values, color=colores_anom, edgecolor='black', linewidth=1.5)
            ax.set_ylabel('Cantidad Detectada', fontsize=12, fontweight='bold')
            ax.set_title('Anomalías Clínicas Detectadas', fontsize=14, fontweight='bold')
            max_anom = builtins.max(anomalia_values) if anomalia_values else 0
            ax.set_ylim(0, max_anom + 1 if max_anom > 0 else 5)
            
            for bar in bars:
                height = bar.get_height()
                if height > 0:
                    ax.text(bar.get_x() + bar.get_width()/2., height,
                           f'{int(height)}', ha='center', va='bottom', fontweight='bold')
            
            plt.xticks(rotation=15, ha='right')
            plt.tight_layout()
            filepath = viz_dir / "03_anomalies_detected.png"
            plt.savefig(filepath, dpi=150, bbox_inches='tight')
            plt.close()
            viz_data['graficos_generados'].append(str(filepath))
            print(f"  ✅ Gráfico anomalías: {filepath.name}")
        
        except Exception as e:
            print(f"  ⚠️ Error generando gráfico anomalías: {e}")
        
        try:
            # Gráfico 4: Segmentación de Pacientes
            segmentation = self.results.get('patient_segmentation', {})
            segmentos = segmentation.get('segmentos', [])
            
            if segmentos and len(segmentos) > 0:
                fig, ax = plt.subplots(figsize=(10, 7))
                nombres = [s['nombre_segmento'] for s in segmentos]
                totales = [s['total_pacientes'] for s in segmentos]
                colores_seg = ['#667eea', '#48bb78', '#ed8936']
                
                wedges, texts, autotexts = ax.pie(totales, labels=nombres, autopct='%1.1f%%',
                                                    colors=colores_seg[:len(nombres)], 
                                                    startangle=90, textprops={'fontsize': 11, 'fontweight': 'bold'})
                ax.set_title('Segmentación de Pacientes (K-Means)', fontsize=14, fontweight='bold')
                
                for i, (nombre, total) in enumerate(zip(nombres, totales)):
                    ax.text(0, -1.3 - i*0.15, f"{nombre}: {total} pacientes", fontsize=10)
                
                plt.tight_layout()
                filepath = viz_dir / "04_patient_segmentation_pie.png"
                plt.savefig(filepath, dpi=150, bbox_inches='tight')
                plt.close()
                viz_data['graficos_generados'].append(str(filepath))
                print(f"  ✅ Gráfico segmentación: {filepath.name}")
        
        except Exception as e:
            print(f"  ⚠️ Error generando gráfico segmentación: {e}")
        
        try:
            # Gráfico 5: Riesgo de Reingresos
            readmission = self.results.get('readmission_prediction', {})
            if readmission:
                fig, ax = plt.subplots(figsize=(10, 6))
                riesgos_reingreso = ['BAJO', 'MEDIO', 'ALTO']
                valores_reingreso = [
                    int(readmission.get('riesgo_bajo', 0)),
                    int(readmission.get('riesgo_medio', 0)),
                    int(readmission.get('riesgo_alto', 0))
                ]
                colores_reingreso = ['#48bb78', '#ed8936', '#f56565']
                
                bars = ax.bar(riesgos_reingreso, valores_reingreso, color=colores_reingreso, 
                             edgecolor='black', linewidth=1.5)
                ax.set_ylabel('Número de Pacientes', fontsize=12, fontweight='bold')
                ax.set_title('Riesgo de Reingresos Hospitalarios', fontsize=14, fontweight='bold')
                max_reingreso = builtins.max(valores_reingreso) if valores_reingreso else 0
                ax.set_ylim(0, max_reingreso + 2)
                
                for bar in bars:
                    height = bar.get_height()
                    if height > 0:
                        ax.text(bar.get_x() + bar.get_width()/2., height,
                               f'{int(height)}', ha='center', va='bottom', fontweight='bold')
                
                plt.tight_layout()
                filepath = viz_dir / "05_readmission_risk.png"
                plt.savefig(filepath, dpi=150, bbox_inches='tight')
                plt.close()
                viz_data['graficos_generados'].append(str(filepath))
                print(f"  ✅ Gráfico reingresos: {filepath.name}")
        
        except Exception as e:
            print(f"  ⚠️ Error generando gráfico reingresos: {e}")
        
        self.results['clinical_visualizations'] = viz_data
        self._save_json(viz_data, "clinical_07_visualizations_metadata.json")
        print("  ✅ Visualizaciones generadas exitosamente")
        return viz_data

    # ==================== EJECUCIÓN COMPLETA ====================
    def run_complete_analysis(self):
        print("\n" + "="*60)
        print("🏥 ANÁLISIS CLÍNICO HOSPITALARIO")
        print("="*60)

        self.load_clinical_data()
        self.predict_diabetes()
        self.predict_readmissions()
        self.analyze_occupancy()
        self.detect_anomalies()
        self.segment_patients()
        self.clinical_intelligence()
        self.generate_clinical_visualizations()

        complete = {
            "timestamp": datetime.now().isoformat(),
            **self.results
        }
        self._save_json(complete, "clinical_00_complete_results.json")

        print("\n✅ ANÁLISIS COMPLETADO EXITOSAMENTE")
        return complete
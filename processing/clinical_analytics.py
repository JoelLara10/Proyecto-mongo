from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, lit, when, count, mean, stddev, min, max, 
    collect_list, size, expr, substring, length, avg, sum, desc, asc,
    floor, months_between, current_date, to_date, datediff
)
from pyspark.sql.window import Window
from pyspark.ml.feature import VectorAssembler, StandardScaler
from pyspark.ml.clustering import KMeans
from pyspark.ml.classification import LogisticRegression
from pyspark.ml.regression import LinearRegression, RandomForestRegressor, GBTRegressor
from pyspark.ml.evaluation import RegressionEvaluator, ClusteringEvaluator, MulticlassClassificationEvaluator
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')
import builtins
import pandas as pd
from datetime import datetime
import json
from pathlib import Path
import math

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

    # ==================== 1. PREDICCIÓN DE RECAÍDA OCULAR ====================
    def predict_readmissions(self):
        """
        Predicción heurística de recaída o necesidad de seguimiento ocular.

        Nota de compatibilidad: se conserva el nombre del método, la llave
        readmission_prediction y el archivo clinical_01_readmission_prediction.json
        para no romper app.py ni la variable readmission que ya usa la vista.
        """
        print("\n👁️ 1. PREDICCIÓN DE RECAÍDA OCULAR")

        df_detalle = self.data.get("examenes_det")
        df_examenes = self.data.get("examenes")
        df_atencion = self.data.get("atencion")
        df_pacientes = self.data.get("pacientes")
        df_diagnosticos = self.data.get("diagnosticos")

        default_results = {
            "tipo_prediccion": "recaida_ocular",
            "total_pacientes": 0,
            "total_pacientes_con_examen_ocular": 0,
            "total_examenes_oculares": 0,
            "riesgo_alto": 0,
            "riesgo_medio": 0,
            "riesgo_bajo": 0,
            "pacientes_alto_riesgo": [],
            "promedio_examenes_oculares": 0,
            "promedio_atenciones": 0,
            "criterios_recaida_ocular": {
                "alto": "Score >= 8",
                "medio": "Score 4-7",
                "bajo": "Score 0-3"
            }
        }

        if df_detalle is None or df_examenes is None or df_atencion is None:
            print("  ❌ No hay datos suficientes de exámenes/atenciones para predicción ocular")
            self.results['readmission_prediction'] = default_results
            self.results['ocular_relapse_prediction'] = default_results
            self._save_json(default_results, "clinical_01_readmission_prediction.json")
            return default_results

        try:
            for campo in ["id_catalogo", "nombre_examen", "estado", "fecha_realizado"]:
                if campo not in df_detalle.columns:
                    df_detalle = df_detalle.withColumn(campo, lit(None))

            base_pacientes = df_atencion.select("Id_exp").filter(col("Id_exp").isNotNull()).distinct()

            # Renombramos fecha para evitar ambigüedad después del join.
            df_examenes_base = df_examenes.select(
                "id_examen",
                "id_atencion",
                col("fecha").alias("fecha_examen")
            )

            detalles = df_detalle.join(
                df_examenes_base,
                on="id_examen", how="left"
            ).join(
                df_atencion.select("id_atencion", "Id_exp"),
                on="id_atencion", how="left"
            ).filter(
                col("Id_exp").isNotNull()
            ).withColumn(
                "id_catalogo_num", col("id_catalogo").cast("int")
            ).withColumn(
                "nombre_lower", expr("lower(coalesce(nombre_examen, ''))")
            ).withColumn(
                "estado_normalizado", expr("upper(coalesce(estado, ''))")
            ).withColumn(
                "fecha_estudio", to_date(expr("coalesce(fecha_realizado, fecha_examen)"))
            )

            ocular_ids = list(range(1, 16))
            retina_ids = [5, 7, 12, 13]
            glaucoma_ids = [3, 6, 8, 14]
            cornea_ids = [9, 10, 15]
            sistemicos_ids = [17, 18, 21, 25]

            condicion_ocular = col("id_catalogo_num").isin(ocular_ids)
            for palabra in ["oct", "tonometr", "fondo de ojo", "campimetr", "paquimetr",
                            "topograf", "retinograf", "angiograf", "gonioscop", "queratometr",
                            "biomicroscop", "agudeza", "refracci", "ultrasonido ocular"]:
                condicion_ocular = condicion_ocular | col("nombre_lower").contains(palabra)

            condicion_retina = (
                col("id_catalogo_num").isin(retina_ids) |
                col("nombre_lower").contains("retin") |
                col("nombre_lower").contains("macul") |
                col("nombre_lower").contains("fondo de ojo") |
                col("nombre_lower").contains("angiograf")
            )
            condicion_glaucoma = (
                col("id_catalogo_num").isin(glaucoma_ids) |
                col("nombre_lower").contains("tonometr") |
                col("nombre_lower").contains("campimetr") |
                col("nombre_lower").contains("nervio") |
                col("nombre_lower").contains("gonioscop")
            )
            condicion_cornea = (
                col("id_catalogo_num").isin(cornea_ids) |
                col("nombre_lower").contains("paquimetr") |
                col("nombre_lower").contains("topograf") |
                col("nombre_lower").contains("queratometr") |
                col("nombre_lower").contains("corneal")
            )

            examenes_oculares = detalles.filter(condicion_ocular)

            ocular_por_paciente = examenes_oculares.groupBy("Id_exp").agg(
                count("*").alias("total_examenes_oculares"),
                expr("count(DISTINCT nombre_examen)").alias("tipos_examenes_oculares"),
                sum(when(col("estado_normalizado") == "REALIZADO", 1).otherwise(0)).alias("examenes_realizados"),
                sum(when(col("estado_normalizado") == "PENDIENTE", 1).otherwise(0)).alias("examenes_pendientes"),
                sum(when(condicion_retina, 1).otherwise(0)).alias("estudios_retina"),
                sum(when(condicion_glaucoma, 1).otherwise(0)).alias("estudios_glaucoma"),
                sum(when(condicion_cornea, 1).otherwise(0)).alias("estudios_corneales"),
                collect_list("nombre_examen").alias("examenes_oculares"),
                min("fecha_estudio").alias("primer_estudio"),
                max("fecha_estudio").alias("ultimo_estudio")
            ).withColumn(
                "examenes_repetidos",
                col("total_examenes_oculares") - col("tipos_examenes_oculares")
            )

            marcadores_sistemicos = detalles.filter(
                col("id_catalogo_num").isin(sistemicos_ids) |
                col("nombre_lower").contains("glucosa") |
                col("nombre_lower").contains("glicosilada") |
                col("nombre_lower").contains("lip") |
                col("nombre_lower").contains("química") |
                col("nombre_lower").contains("quimica")
            ).groupBy("Id_exp").agg(
                count("*").alias("marcadores_sistemicos"),
                collect_list("nombre_examen").alias("examenes_sistemicos")
            )

            riesgo = base_pacientes.join(ocular_por_paciente, "Id_exp", "left") \
                .join(marcadores_sistemicos, "Id_exp", "left")

            if df_diagnosticos is not None:
                for campo in ["diagnostico_principal", "diagnosticos_secundarios", "observaciones"]:
                    if campo not in df_diagnosticos.columns:
                        df_diagnosticos = df_diagnosticos.withColumn(campo, lit(""))

                diagnosticos = df_diagnosticos.join(
                    df_atencion.select("id_atencion", "Id_exp"),
                    on="id_atencion", how="left"
                ).filter(
                    col("Id_exp").isNotNull()
                ).withColumn(
                    "texto_diag",
                    expr("lower(concat_ws(' ', coalesce(diagnostico_principal, ''), coalesce(diagnosticos_secundarios, ''), coalesce(observaciones, '')))")
                )

                condicion_diag_ocular = (
                    col("texto_diag").contains("glau") |
                    col("texto_diag").contains("retin") |
                    col("texto_diag").contains("macul") |
                    col("texto_diag").contains("catar") |
                    col("texto_diag").contains("querat") |
                    col("texto_diag").contains("uve") |
                    col("texto_diag").contains("cornea") |
                    col("texto_diag").contains("córnea") |
                    col("texto_diag").contains("ocular") |
                    col("texto_diag").contains("ojo")
                )

                diag_por_paciente = diagnosticos.groupBy("Id_exp").agg(
                    max(when(condicion_diag_ocular, 1).otherwise(0)).alias("diagnostico_ocular"),
                    count("*").alias("total_diagnosticos"),
                    collect_list("diagnostico_principal").alias("diagnosticos")
                )
                riesgo = riesgo.join(diag_por_paciente, "Id_exp", "left")
            else:
                riesgo = riesgo.withColumn("diagnostico_ocular", lit(0)).withColumn("total_diagnosticos", lit(0))

            riesgo = riesgo.fillna({
                "total_examenes_oculares": 0,
                "tipos_examenes_oculares": 0,
                "examenes_realizados": 0,
                "examenes_pendientes": 0,
                "estudios_retina": 0,
                "estudios_glaucoma": 0,
                "estudios_corneales": 0,
                "examenes_repetidos": 0,
                "marcadores_sistemicos": 0,
                "diagnostico_ocular": 0,
                "total_diagnosticos": 0
            })

            score_examenes = when(col("total_examenes_oculares") >= 5, 3) \
                .when(col("total_examenes_oculares") >= 3, 2) \
                .when(col("total_examenes_oculares") >= 1, 1) \
                .otherwise(0)

            riesgo = riesgo.withColumn(
                "score_recaida",
                score_examenes +
                when(col("estudios_retina") >= 2, 2).when(col("estudios_retina") >= 1, 1).otherwise(0) +
                when(col("estudios_glaucoma") >= 2, 2).when(col("estudios_glaucoma") >= 1, 1).otherwise(0) +
                when(col("estudios_corneales") >= 2, 2).when(col("estudios_corneales") >= 1, 1).otherwise(0) +
                when(col("examenes_repetidos") >= 1, 2).otherwise(0) +
                when(col("examenes_pendientes") >= 3, 1).otherwise(0) +
                when(col("diagnostico_ocular") == 1, 2).otherwise(0) +
                when(col("marcadores_sistemicos") >= 2, 1).otherwise(0)
            ).withColumn(
                "nivel_riesgo_recaida",
                when(col("score_recaida") >= 8, "ALTO")
                .when(col("score_recaida") >= 4, "MEDIO")
                .otherwise("BAJO")
            ).withColumn(
                "perfil_principal",
                when(
                    (col("estudios_retina") >= col("estudios_glaucoma")) &
                    (col("estudios_retina") >= col("estudios_corneales")) &
                    (col("estudios_retina") > 0),
                    "Retina/Mácula"
                ).when(
                    (col("estudios_glaucoma") >= col("estudios_retina")) &
                    (col("estudios_glaucoma") >= col("estudios_corneales")) &
                    (col("estudios_glaucoma") > 0),
                    "Glaucoma/Nervio óptico"
                ).when(
                    col("estudios_corneales") > 0,
                    "Córnea"
                ).otherwise("Sin perfil ocular dominante")
            ).withColumn(
                "factores_detectados",
                expr("""
                    concat_ws(', ',
                        case when estudios_retina > 0 then 'Retina/Mácula' end,
                        case when estudios_glaucoma > 0 then 'Glaucoma/Nervio óptico' end,
                        case when estudios_corneales > 0 then 'Córnea' end,
                        case when marcadores_sistemicos > 0 then 'Metabólico' end
                    )
                """)
            ).withColumn(
                "dias_desde_ultimo_estudio",
                datediff(current_date(), col("ultimo_estudio"))
            )

            if df_pacientes is not None and "Id_exp" in df_pacientes.columns:
                paciente_cols = [c for c in ["Id_exp", "nom_pac", "papell", "sapell", "fecnac"] if c in df_pacientes.columns]
                riesgo = riesgo.join(df_pacientes.select(*paciente_cols), "Id_exp", "left")
                if "fecnac" in riesgo.columns:
                    riesgo = riesgo.withColumn("edad", floor(months_between(current_date(), to_date(col("fecnac"))) / 12))
                else:
                    riesgo = riesgo.withColumn("edad", lit(None))
            else:
                riesgo = riesgo.withColumn("edad", lit(None))

            for campo in ["nom_pac", "papell", "sapell"]:
                if campo not in riesgo.columns:
                    riesgo = riesgo.withColumn(campo, lit(""))

            promedio_examenes = riesgo.agg(avg("total_examenes_oculares")).collect()[0][0] or 0
            total_examenes = riesgo.agg(sum("total_examenes_oculares")).collect()[0][0] or 0

            ocular_results = {
                "tipo_prediccion": "recaida_ocular",
                "total_pacientes": riesgo.count(),
                "total_pacientes_con_examen_ocular": riesgo.filter(col("total_examenes_oculares") > 0).count(),
                "total_examenes_oculares": int(total_examenes),
                "riesgo_alto": riesgo.filter(col("nivel_riesgo_recaida") == "ALTO").count(),
                "riesgo_medio": riesgo.filter(col("nivel_riesgo_recaida") == "MEDIO").count(),
                "riesgo_bajo": riesgo.filter(col("nivel_riesgo_recaida") == "BAJO").count(),
                "pacientes_alto_riesgo": self._safe_to_pandas(
                    riesgo.filter(col("nivel_riesgo_recaida") == "ALTO")
                    .orderBy(desc("score_recaida"))
                    .select(
                        "Id_exp", "nom_pac", "papell", "edad", "score_recaida",
                        "total_examenes_oculares", "examenes_repetidos", "examenes_pendientes",
                        "perfil_principal", "factores_detectados", "ultimo_estudio"
                    )
                ),
                "promedio_examenes_oculares": builtins.round(float(promedio_examenes), 2),
                "promedio_atenciones": builtins.round(float(promedio_examenes), 2),
                "criterios_recaida_ocular": {
                    "alto": "Score >= 8: múltiples estudios oculares, repetición y/o patrones retina-glaucoma-córnea",
                    "medio": "Score 4-7: seguimiento oftalmológico activo con uno o más grupos de riesgo",
                    "bajo": "Score 0-3: sin patrón ocular activo o controles aislados",
                    "grupos": {
                        "retina_macula": ["OCT de mácula", "Fondo de ojo", "Angiografía fluoresceínica", "Retinografía"],
                        "glaucoma_nervio_optico": ["Tonometría", "Campimetría", "OCT de nervio óptico", "Gonioscopía"],
                        "cornea": ["Paquimetría", "Topografía corneal", "Queratometría"]
                    }
                }
            }

            self.results['readmission_prediction'] = ocular_results
            self.results['ocular_relapse_prediction'] = ocular_results
            self._save_json(ocular_results, "clinical_01_readmission_prediction.json")
            print(f"  ✅ Riesgo ALTO de recaída ocular: {ocular_results['riesgo_alto']}")
            return ocular_results

        except Exception as e:
            print(f"  ❌ Error en predicción de recaída ocular: {e}")
            self.results['readmission_prediction'] = default_results
            self.results['ocular_relapse_prediction'] = default_results
            self._save_json(default_results, "clinical_01_readmission_prediction.json")
            return default_results

    # ==================== 2. ANÁLISIS DE OCUPACIÓN ====================
    def analyze_occupancy(self):
        print("\n🛏️ 2. ANÁLISIS DE OCUPACIÓN HOSPITALARIA")
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
            self._save_json(occupancy_results, "clinical_02_occupancy_analysis.json")
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
        self._save_json(default, "clinical_02_occupancy_analysis.json")
        return default

    # ==================== 3. DETECCIÓN DE ANOMALÍAS ====================
    def detect_anomalies(self):
        print("\n⚠️ 3. DETECCIÓN DE ANOMALÍAS CLÍNICAS")
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
        self._save_json(results, "clinical_03_anomaly_detection.json")
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

    # ==================== 3.5 MODELOS PREDICTIVOS CLÍNICOS ====================
    def clinical_predictive_models(self):
        """Modelos ML: 3 regresiones (LR, RF, GBT) + clasificación con matriz confusión"""
        print("\n🤖 3.5. MODELOS PREDICTIVOS CLÍNICOS (Riesgo de Recaída)")
        
        df_pacientes = self.data.get("pacientes")
        df_atencion = self.data.get("atencion")
        
        if df_pacientes is None or df_atencion is None or df_atencion.count() < 20:
            print("  ⚠️ Datos insuficientes para modelos predictivos clínicos")
            return None
        
        predictive_clinical = {
            'regression_models': {},
            'risk_classification': None
        }
        
        try:
            # ==================== PREPARACIÓN DE DATOS ====================
            # Crear dataset enriquecido: edad + número de atenciones
            def _safe_metric(val):
                """Convierte métrica a float redondeado, retorna None si es NaN"""
                return builtins.round(float(val), 4) if not math.isnan(val) else None
            
            pacientes_ml = df_pacientes.withColumn(
                "edad", floor(months_between(current_date(), to_date(col("fecnac"))) / 12)
            )
            
            atenciones_por_pac = df_atencion.groupBy("Id_exp").agg(
                count("*").alias("num_atenciones"),
                count(when(col("status") == "CERRADA", 1)).alias("atenciones_cerradas")
            )
            
            df_ml = pacientes_ml.join(atenciones_por_pac, "Id_exp", "left") \
                .select("Id_exp", "edad", "num_atenciones", "atenciones_cerradas") \
                .na.drop() \
                .filter((col("edad") > 0) & (col("num_atenciones") > 0))
            
            if df_ml.count() < 10:
                print("  ⚠️ Muestra muy pequeña para modelos predictivos")
                return None
            
            print("  📈 Entrenando modelos de regresión...")
            
            # Features engineering
            assembler = VectorAssembler(
                inputCols=["edad", "atenciones_cerradas"],
                outputCol="features_unscaled"
            )
            df_features = assembler.transform(df_ml)
            
            scaler = StandardScaler(
                inputCol="features_unscaled",
                outputCol="features",
                withStd=True,
                withMean=True
            )
            scaler_model = scaler.fit(df_features)
            df_scaled = scaler_model.transform(df_features)
            
            train_reg, test_reg = df_scaled.randomSplit([0.8, 0.2], seed=42)
            
            # Evaluadores para regresión
            eval_r2 = RegressionEvaluator(labelCol="num_atenciones", predictionCol="prediction", metricName="r2")
            eval_mae = RegressionEvaluator(labelCol="num_atenciones", predictionCol="prediction", metricName="mae")
            eval_rmse = RegressionEvaluator(labelCol="num_atenciones", predictionCol="prediction", metricName="rmse")
            
            # ==================== MODELO 1: REGRESIÓN LINEAL ====================
            print("  🔷 Entrenando Regresión Lineal...")
            lr = LinearRegression(featuresCol="features", labelCol="num_atenciones", regParam=0.1)
            lr_model = lr.fit(train_reg)
            lr_pred = lr_model.transform(test_reg)
            
            predictive_clinical['regression_models']['linear_regression'] = {
                'r2': _safe_metric(eval_r2.evaluate(lr_pred)),
                'mae': _safe_metric(eval_mae.evaluate(lr_pred)),
                'rmse': _safe_metric(eval_rmse.evaluate(lr_pred))
            }
            print(f"    ✅ LR: R²={predictive_clinical['regression_models']['linear_regression']['r2']:.4f}, "
                  f"MAE={predictive_clinical['regression_models']['linear_regression']['mae']:.4f}, "
                  f"RMSE={predictive_clinical['regression_models']['linear_regression']['rmse']:.4f}")
            
            # ==================== MODELO 2: BOSQUE ALEATORIO ====================
            print("  🔷 Entrenando Bosque Aleatorio...")
            rf = RandomForestRegressor(featuresCol="features", labelCol="num_atenciones", numTrees=50, seed=42)
            rf_model = rf.fit(train_reg)
            rf_pred = rf_model.transform(test_reg)
            
            predictive_clinical['regression_models']['random_forest'] = {
                'r2': _safe_metric(eval_r2.evaluate(rf_pred)),
                'mae': _safe_metric(eval_mae.evaluate(rf_pred)),
                'rmse': _safe_metric(eval_rmse.evaluate(rf_pred))
            }
            print(f"    ✅ RF: R²={predictive_clinical['regression_models']['random_forest']['r2']:.4f}, "
                  f"MAE={predictive_clinical['regression_models']['random_forest']['mae']:.4f}, "
                  f"RMSE={predictive_clinical['regression_models']['random_forest']['rmse']:.4f}")
            
            # ==================== MODELO 3: GRADIENT BOOSTING ====================
            print("  🔷 Entrenando Árbol Potenciado (GBT)...")
            gbt = GBTRegressor(featuresCol="features", labelCol="num_atenciones", maxIter=50, seed=42)
            gbt_model = gbt.fit(train_reg)
            gbt_pred = gbt_model.transform(test_reg)
            
            predictive_clinical['regression_models']['gradient_boosting'] = {
                'r2': _safe_metric(eval_r2.evaluate(gbt_pred)),
                'mae': _safe_metric(eval_mae.evaluate(gbt_pred)),
                'rmse': _safe_metric(eval_rmse.evaluate(gbt_pred))
            }
            print(f"    ✅ GBT: R²={predictive_clinical['regression_models']['gradient_boosting']['r2']:.4f}, "
                  f"MAE={predictive_clinical['regression_models']['gradient_boosting']['mae']:.4f}, "
                  f"RMSE={predictive_clinical['regression_models']['gradient_boosting']['rmse']:.4f}")
            
            # ==================== CLASIFICACIÓN: Riesgo Alto/Bajo ====================
            print("  🔴 Entrenando Clasificación Logística...")
            
            # Crear label: "riesgo_alto" si num_atenciones >= mediana
            mediana_row = df_ml.approxQuantile("num_atenciones", [0.5], 0.01)
            mediana_atenc = float(mediana_row[0]) if mediana_row else 2.0
            
            df_clasificacion = df_ml.withColumn(
                "label",
                when(col("num_atenciones") >= mediana_atenc, 1.0).otherwise(0.0)
            )
            
            # Features: edad + atenciones cerradas (reutilizar escalador)
            df_clf = assembler.transform(df_clasificacion)
            df_clf = scaler_model.transform(df_clf)
            
            train_clf, test_clf = df_clf.randomSplit([0.8, 0.2], seed=42)
            
            # Regresión Logística: predecir riesgo de recaída
            log_reg = LogisticRegression(
                featuresCol="features",
                labelCol="label",
                maxIter=20,
                regParam=0.1
            )
            log_model = log_reg.fit(train_clf)
            log_pred = log_model.transform(test_clf)
            
            # Métricas de clasificación
            eval_clf = MulticlassClassificationEvaluator(
                labelCol="label",
                predictionCol="prediction"
            )
            
            clf_accuracy = eval_clf.setMetricName("accuracy").evaluate(log_pred)
            clf_accuracy = builtins.round(float(clf_accuracy), 4) if not math.isnan(clf_accuracy) else None
            
            clf_precision = eval_clf.setMetricName("weightedPrecision").evaluate(log_pred)
            clf_precision = builtins.round(float(clf_precision), 4) if not math.isnan(clf_precision) else None
            
            clf_recall = eval_clf.setMetricName("weightedRecall").evaluate(log_pred)
            clf_recall = builtins.round(float(clf_recall), 4) if not math.isnan(clf_recall) else None
            
            clf_f1 = eval_clf.setMetricName("f1").evaluate(log_pred)
            clf_f1 = builtins.round(float(clf_f1), 4) if not math.isnan(clf_f1) else None
            
            # Matriz de confusión
            cm_data = (
                log_pred
                .select("label", "prediction")
                .groupBy("label", "prediction")
                .count()
                .collect()
            )
            
            cm = {"tp": 0, "fp": 0, "fn": 0, "tn": 0}
            for row in cm_data:
                real, pred, cnt = int(row["label"]), int(row["prediction"]), int(row["count"])
                if real == 1 and pred == 1:
                    cm["tp"] = cnt
                elif real == 0 and pred == 1:
                    cm["fp"] = cnt
                elif real == 1 and pred == 0:
                    cm["fn"] = cnt
                elif real == 0 and pred == 0:
                    cm["tn"] = cnt
            
            predictive_clinical['risk_classification'] = {
                'accuracy': clf_accuracy,
                'precision': clf_precision,
                'recall': clf_recall,
                'f1_score': clf_f1,
                'umbral_riesgo': builtins.round(mediana_atenc, 2),
                'riesgo_alto': f"Atenciones >= {builtins.round(mediana_atenc, 0)}",
                'riesgo_bajo': f"Atenciones < {builtins.round(mediana_atenc, 0)}",
                'confusion_matrix': cm,
                'total_test': int(test_clf.count())
            }
            
            print(f"  ✅ Clasificación: accuracy={clf_accuracy}, F1={clf_f1}")
            print(f"  ✅ Matriz confusión: TP={cm['tp']}, FP={cm['fp']}, FN={cm['fn']}, TN={cm['tn']}")
            
        except Exception as e:
            print(f"  ⚠️ Error en modelos clínicos: {e}")
            import traceback
            traceback.print_exc()
        
        self.results['clinical_predictive'] = predictive_clinical
        self._save_json(predictive_clinical, "clinical_03_predictive_models.json")
        
        return predictive_clinical

    # ==================== 4. SEGMENTACIÓN DE PACIENTES ====================
    def segment_patients(self):
        print("\n📊 4. SEGMENTACIÓN DE PACIENTES")
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
        self._save_json(result, "clinical_04_patient_segmentation.json")
        print(f"  ✅ Segmentos creados: {len(segmentos)}")
        return result

    # ==================== 5. INTELIGENCIA CLÍNICA ====================
    def clinical_intelligence(self):
        print("\n🧠 5. INTELIGENCIA CLÍNICA")
        
        recomendaciones = []
        hallazgos = []
        correlaciones = []
        
        # Análisis de Recaída Ocular
        ocular_relapse = self.results.get('readmission_prediction', {})
        if ocular_relapse:
            riesgo_alto_ocular = ocular_relapse.get('riesgo_alto', 0)
            promedio_examenes = ocular_relapse.get('promedio_examenes_oculares', 0)
            pacientes_oculares = ocular_relapse.get('total_pacientes_con_examen_ocular', 0)
            
            if riesgo_alto_ocular > 0:
                hallazgos.append({
                    "patron": "Alto Riesgo de Recaída Ocular",
                    "descripcion": f"{riesgo_alto_ocular} pacientes con alto riesgo por patrón de exámenes oftalmológicos"
                })
                recomendaciones.append("🔴 Priorizar revisión oftalmológica para pacientes con riesgo alto de recaída")
                recomendaciones.append("🔴 Programar seguimiento por retina, glaucoma o córnea según perfil de estudios")
            
            if pacientes_oculares > 0 and promedio_examenes >= 2:
                correlaciones.append({
                    "condicion": "Exámenes oftalmológicos recurrentes",
                    "riesgo_asociado": "Posible recaída o progresión ocular",
                    "recomendacion": "Revisar historial de OCT, tonometría, fondo de ojo y campimetría antes de la próxima consulta"
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
        self._save_json(result, "clinical_05_clinical_intelligence.json")
        print("  ✅ Inteligencia clínica generada")
        return result

    # ==================== 6. VISUALIZACIONES ====================
    def generate_clinical_visualizations(self):
        print("\n📊 Generando visualizaciones...")
        viz_dir = self.results_dir / "clinical_visualizations"
        viz_dir.mkdir(exist_ok=True)
        
        viz_data = {"graficos_generados": []}
        
        try:
            # Gráfico 1: Riesgo de Recaída Ocular
            readmission = self.results.get('readmission_prediction', {})
            if readmission:
                fig, ax = plt.subplots(figsize=(10, 6))
                riesgos_oculares = ['BAJO', 'MEDIO', 'ALTO']
                valores_oculares = [
                    int(readmission.get('riesgo_bajo', 0)),
                    int(readmission.get('riesgo_medio', 0)),
                    int(readmission.get('riesgo_alto', 0))
                ]
                colores_oculares = ['#48bb78', '#ed8936', '#f56565']

                bars = ax.bar(
                    riesgos_oculares,
                    valores_oculares,
                    color=colores_oculares,
                    edgecolor='black',
                    linewidth=1.5
                )

                ax.set_ylabel('Número de Pacientes', fontsize=12, fontweight='bold')
                ax.set_title('Riesgo de Recaída Ocular', fontsize=14, fontweight='bold')

                max_ocular = builtins.max(valores_oculares) if valores_oculares else 0
                ax.set_ylim(0, max_ocular + 2)

                for bar in bars:
                    height = bar.get_height()
                    if height > 0:
                        ax.text(
                            bar.get_x() + bar.get_width() / 2.,
                            height,
                            f'{int(height)}',
                            ha='center',
                            va='bottom',
                            fontweight='bold'
                        )

                plt.tight_layout()
                filepath = viz_dir / "01_ocular_relapse_risk.png"
                plt.savefig(filepath, dpi=150, bbox_inches='tight')
                plt.close()

                viz_data['graficos_generados'].append(str(filepath))
                print(f"  ✅ Gráfico recaída ocular: {filepath.name}")
        except Exception as e:
            print(f"  ⚠️ Error generando gráfico de recaída ocular: {e}")
        
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
        
       
        self.results['clinical_visualizations'] = viz_data
        self._save_json(viz_data, "clinical_06_visualizations_metadata.json")
        print("  ✅ Visualizaciones generadas exitosamente")
        return viz_data

    # ==================== EJECUCIÓN COMPLETA ====================
    def run_complete_analysis(self):
        print("\n" + "="*60)
        print("🏥 ANÁLISIS CLÍNICO HOSPITALARIO")
        print("="*60)

        self.load_clinical_data()
        self.predict_readmissions()
        self.analyze_occupancy()
        self.detect_anomalies()
        self.clinical_predictive_models()  # ← NUEVO: Modelos ML de riesgo
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
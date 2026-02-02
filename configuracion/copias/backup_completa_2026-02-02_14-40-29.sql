-- RESPALDO COMPLETA - 2026-02-02_14-40-29

CREATE TABLE `atencion` (
  `id_atencion` int(11) NOT NULL AUTO_INCREMENT,
  `Id_exp` int(11) NOT NULL,
  `area` enum('Hospitalizado','Urgencias','Ambulatorio') NOT NULL,
  `id_cama` int(11) DEFAULT NULL,
  `motivo` text DEFAULT NULL,
  `especialidad` text DEFAULT NULL,
  `alergias` text DEFAULT NULL,
  `fecha_ing` timestamp NOT NULL DEFAULT current_timestamp(),
  `status` enum('ABIERTA','CERRADA') NOT NULL DEFAULT 'ABIERTA',
  PRIMARY KEY (`id_atencion`),
  KEY `Id_exp` (`Id_exp`),
  KEY `id_cama` (`id_cama`),
  CONSTRAINT `atencion_ibfk_1` FOREIGN KEY (`Id_exp`) REFERENCES `pacientes` (`Id_exp`),
  CONSTRAINT `atencion_ibfk_2` FOREIGN KEY (`id_cama`) REFERENCES `camas` (`id_cama`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

INSERT INTO `atencion` (id_atencion, Id_exp, area, id_cama, motivo, especialidad, alergias, fecha_ing, status) VALUES (1,12,'Hospitalizado',1,'Consulta general','Medicina general','SI','2026-01-18 11:32:24','CERRADA');
INSERT INTO `atencion` (id_atencion, Id_exp, area, id_cama, motivo, especialidad, alergias, fecha_ing, status) VALUES (2,14,'Hospitalizado',2,'Urgencia','Medicina general','NO','2026-01-18 11:37:42','ABIERTA');
INSERT INTO `atencion` (id_atencion, Id_exp, area, id_cama, motivo, especialidad, alergias, fecha_ing, status) VALUES (3,15,'Urgencias',3,'Consulta general','Cardiología','NO','2026-01-18 11:39:16','ABIERTA');
CREATE TABLE `atencion_medicos` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `id_atencion` int(11) NOT NULL,
  `id_medico` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `id_atencion` (`id_atencion`),
  KEY `id_medico` (`id_medico`),
  CONSTRAINT `atencion_medicos_ibfk_1` FOREIGN KEY (`id_atencion`) REFERENCES `atencion` (`id_atencion`),
  CONSTRAINT `atencion_medicos_ibfk_2` FOREIGN KEY (`id_medico`) REFERENCES `users` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=9 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

INSERT INTO `atencion_medicos` (id, id_atencion, id_medico) VALUES (1,2,3);
INSERT INTO `atencion_medicos` (id, id_atencion, id_medico) VALUES (2,3,4);
INSERT INTO `atencion_medicos` (id, id_atencion, id_medico) VALUES (4,1,3);
INSERT INTO `atencion_medicos` (id, id_atencion, id_medico) VALUES (5,1,3);
INSERT INTO `atencion_medicos` (id, id_atencion, id_medico) VALUES (6,1,3);
INSERT INTO `atencion_medicos` (id, id_atencion, id_medico) VALUES (7,1,3);
INSERT INTO `atencion_medicos` (id, id_atencion, id_medico) VALUES (8,1,3);
CREATE TABLE `camas` (
  `id_cama` int(11) NOT NULL AUTO_INCREMENT,
  `area` enum('Hospitalizado','Urgencias') NOT NULL,
  `numero` varchar(10) NOT NULL,
  `ocupada` tinyint(1) DEFAULT 0,
  PRIMARY KEY (`id_cama`)
) ENGINE=InnoDB AUTO_INCREMENT=7 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

INSERT INTO `camas` (id_cama, area, numero, ocupada) VALUES (1,'Hospitalizado','H-101',1);
INSERT INTO `camas` (id_cama, area, numero, ocupada) VALUES (2,'Hospitalizado','H-102',1);
INSERT INTO `camas` (id_cama, area, numero, ocupada) VALUES (3,'Urgencias','U-01',1);
INSERT INTO `camas` (id_cama, area, numero, ocupada) VALUES (4,'Urgencias','U-02',0);
INSERT INTO `camas` (id_cama, area, numero, ocupada) VALUES (5,'Hospitalizado','H-103',0);
INSERT INTO `camas` (id_cama, area, numero, ocupada) VALUES (6,'Urgencias','U-03',0);
CREATE TABLE `catalogo_examenes_gabinete` (
  `id_catalogo` int(11) NOT NULL AUTO_INCREMENT,
  `nombre` varchar(150) NOT NULL,
  PRIMARY KEY (`id_catalogo`)
) ENGINE=InnoDB AUTO_INCREMENT=16 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

INSERT INTO `catalogo_examenes_gabinete` (id_catalogo, nombre) VALUES (1,'Agudeza visual');
INSERT INTO `catalogo_examenes_gabinete` (id_catalogo, nombre) VALUES (2,'Refracción');
INSERT INTO `catalogo_examenes_gabinete` (id_catalogo, nombre) VALUES (3,'Tonometría');
INSERT INTO `catalogo_examenes_gabinete` (id_catalogo, nombre) VALUES (4,'Biomicroscopía');
INSERT INTO `catalogo_examenes_gabinete` (id_catalogo, nombre) VALUES (5,'Fondo de ojo');
INSERT INTO `catalogo_examenes_gabinete` (id_catalogo, nombre) VALUES (6,'Campimetría');
INSERT INTO `catalogo_examenes_gabinete` (id_catalogo, nombre) VALUES (7,'OCT de mácula');
INSERT INTO `catalogo_examenes_gabinete` (id_catalogo, nombre) VALUES (8,'OCT de nervio óptico');
INSERT INTO `catalogo_examenes_gabinete` (id_catalogo, nombre) VALUES (9,'Paquimetría');
INSERT INTO `catalogo_examenes_gabinete` (id_catalogo, nombre) VALUES (10,'Topografía corneal');
INSERT INTO `catalogo_examenes_gabinete` (id_catalogo, nombre) VALUES (11,'Ultrasonido ocular');
INSERT INTO `catalogo_examenes_gabinete` (id_catalogo, nombre) VALUES (12,'Angiografía fluoresceínica');
INSERT INTO `catalogo_examenes_gabinete` (id_catalogo, nombre) VALUES (13,'Retinografía');
INSERT INTO `catalogo_examenes_gabinete` (id_catalogo, nombre) VALUES (14,'Gonioscopía');
INSERT INTO `catalogo_examenes_gabinete` (id_catalogo, nombre) VALUES (15,'Queratometría');
CREATE TABLE `catalogo_examenes_laboratorio` (
  `id_catalogo` int(11) NOT NULL AUTO_INCREMENT,
  `nombre` varchar(150) NOT NULL,
  PRIMARY KEY (`id_catalogo`)
) ENGINE=InnoDB AUTO_INCREMENT=11 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

INSERT INTO `catalogo_examenes_laboratorio` (id_catalogo, nombre) VALUES (1,'Biometría Hemática');
INSERT INTO `catalogo_examenes_laboratorio` (id_catalogo, nombre) VALUES (2,'Química Sanguínea');
INSERT INTO `catalogo_examenes_laboratorio` (id_catalogo, nombre) VALUES (3,'Glucosa');
INSERT INTO `catalogo_examenes_laboratorio` (id_catalogo, nombre) VALUES (4,'Urea');
INSERT INTO `catalogo_examenes_laboratorio` (id_catalogo, nombre) VALUES (5,'Creatinina');
INSERT INTO `catalogo_examenes_laboratorio` (id_catalogo, nombre) VALUES (6,'Perfil Lipídico');
INSERT INTO `catalogo_examenes_laboratorio` (id_catalogo, nombre) VALUES (7,'Examen General de Orina');
INSERT INTO `catalogo_examenes_laboratorio` (id_catalogo, nombre) VALUES (8,'Tiempo de Protrombina');
INSERT INTO `catalogo_examenes_laboratorio` (id_catalogo, nombre) VALUES (9,'Grupo y RH');
INSERT INTO `catalogo_examenes_laboratorio` (id_catalogo, nombre) VALUES (10,'Hemoglobina Glicosilada');
CREATE TABLE `cat_servicios` (
  `id_serv` int(11) NOT NULL DEFAULT 0,
  `serv_cve` varchar(15) CHARACTER SET utf8 COLLATE utf8_general_ci NOT NULL,
  `serv_desc` varchar(150) CHARACTER SET utf8 COLLATE utf8_general_ci NOT NULL,
  `serv_costo` decimal(10,2) NOT NULL DEFAULT 0.00,
  `serv_costo2` decimal(10,2) NOT NULL DEFAULT 0.00,
  `serv_costo3` decimal(10,2) NOT NULL DEFAULT 0.00,
  `serv_costo4` decimal(10,2) NOT NULL DEFAULT 0.00,
  `serv_costo5` decimal(10,2) NOT NULL DEFAULT 0.00,
  `serv_costo6` decimal(10,2) NOT NULL DEFAULT 0.00,
  `serv_costo7` decimal(10,2) NOT NULL DEFAULT 0.00,
  `serv_costo8` decimal(10,2) NOT NULL DEFAULT 0.00,
  `serv_umed` varchar(20) CHARACTER SET utf8 COLLATE utf8_general_ci NOT NULL,
  `serv_activo` varchar(2) CHARACTER SET utf8 COLLATE utf8_general_ci NOT NULL DEFAULT 'SI',
  `tipo` varchar(50) CHARACTER SET utf8 COLLATE utf8_general_ci DEFAULT NULL,
  `tip_insumo` varchar(350) CHARACTER SET utf8 COLLATE utf8_general_ci NOT NULL,
  `proveedor` varchar(350) CHARACTER SET utf8 COLLATE utf8_general_ci NOT NULL,
  `grupo` varchar(350) CHARACTER SET utf8 COLLATE utf8_general_ci NOT NULL,
  `codigo_sat` varchar(50) CHARACTER SET utf8 COLLATE utf8_general_ci NOT NULL,
  `c_cveuni` varchar(100) CHARACTER SET utf8 COLLATE utf8_general_ci NOT NULL,
  `c_nombre` varchar(100) CHARACTER SET utf8 COLLATE utf8_general_ci NOT NULL,
  `iva` decimal(5,2) DEFAULT 0.16
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

INSERT INTO `cat_servicios` (id_serv, serv_cve, serv_desc, serv_costo, serv_costo2, serv_costo3, serv_costo4, serv_costo5, serv_costo6, serv_costo7, serv_costo8, serv_umed, serv_activo, tipo, tip_insumo, proveedor, grupo, codigo_sat, c_cveuni, c_nombre, iva) VALUES (1,'S0001','CONSULTA OFTALMOLOGICA',1000.00,1000.00,0.00,0.00,0.00,0.00,0.00,0.00,'CONSULTA','SI','3','CONSULTA OFTALMOLOGICA','INEO','SERVICIOS HOSPITALARIOS','85101502','E48','SERVICIO',0.16);
INSERT INTO `cat_servicios` (id_serv, serv_cve, serv_desc, serv_costo, serv_costo2, serv_costo3, serv_costo4, serv_costo5, serv_costo6, serv_costo7, serv_costo8, serv_umed, serv_activo, tipo, tip_insumo, proveedor, grupo, codigo_sat, c_cveuni, c_nombre, iva) VALUES (2,'S0002','APLICACIÓN INTRAVITREA WETLIA ( NO INCLUYE MEDICAMENTO)',1000.00,1000.00,0.00,0.00,0.00,0.00,0.00,0.00,'CONSULTA','SI','3','CONSULTA OFTALMOLOGICA','INEO','SERVICIOS HOSPITALARIOS','85101502','E48','SERVICIO',0.16);
INSERT INTO `cat_servicios` (id_serv, serv_cve, serv_desc, serv_costo, serv_costo2, serv_costo3, serv_costo4, serv_costo5, serv_costo6, serv_costo7, serv_costo8, serv_umed, serv_activo, tipo, tip_insumo, proveedor, grupo, codigo_sat, c_cveuni, c_nombre, iva) VALUES (3,'S0003','APLICACIÓN INTRAVITREA WETLIA (INCLUYE MEDICAMENTO)',13000.00,8000.00,0.00,0.00,0.00,0.00,0.00,0.00,'CONSULTA','SI','3','CONSULTA OFTALMOLOGICA','INEO','SERVICIOS HOSPITALARIOS','85101502','E48','SERVICIO',0.16);
INSERT INTO `cat_servicios` (id_serv, serv_cve, serv_desc, serv_costo, serv_costo2, serv_costo3, serv_costo4, serv_costo5, serv_costo6, serv_costo7, serv_costo8, serv_umed, serv_activo, tipo, tip_insumo, proveedor, grupo, codigo_sat, c_cveuni, c_nombre, iva) VALUES (4,'S0004','INYECCION ANTIANGIOGENICA (NO INCLUYE MEDICAMENTO)',1000.00,1000.00,0.00,0.00,0.00,0.00,0.00,0.00,'CONSULTA','SI','3','CONSULTA OFTALMOLOGICA','INEO','SERVICIOS HOSPITALARIOS','85101502','E48','SERVICIO',0.16);
INSERT INTO `cat_servicios` (id_serv, serv_cve, serv_desc, serv_costo, serv_costo2, serv_costo3, serv_costo4, serv_costo5, serv_costo6, serv_costo7, serv_costo8, serv_umed, serv_activo, tipo, tip_insumo, proveedor, grupo, codigo_sat, c_cveuni, c_nombre, iva) VALUES (5,'S0005','INYECCION ANTIANGIOGENICA (SI INCLUYE MEDICAMENTO)',6500.00,2000.00,0.00,0.00,0.00,0.00,0.00,0.00,'CONSULTA','SI','3','CONSULTA OFTALMOLOGICA','INEO','SERVICIOS HOSPITALARIOS','85101502','E48','SERVICIO',0.16);
INSERT INTO `cat_servicios` (id_serv, serv_cve, serv_desc, serv_costo, serv_costo2, serv_costo3, serv_costo4, serv_costo5, serv_costo6, serv_costo7, serv_costo8, serv_umed, serv_activo, tipo, tip_insumo, proveedor, grupo, codigo_sat, c_cveuni, c_nombre, iva) VALUES (6,'S0006','APLICACIÓN DE TOXINA (CONSULTORIO)',5500.00,1500.00,0.00,0.00,0.00,0.00,0.00,0.00,'CONSULTA','SI','3','CONSULTA OFTALMOLOGICA','INEO','SERVICIOS HOSPITALARIOS','85101502','E48','SERVICIO',0.16);
INSERT INTO `cat_servicios` (id_serv, serv_cve, serv_desc, serv_costo, serv_costo2, serv_costo3, serv_costo4, serv_costo5, serv_costo6, serv_costo7, serv_costo8, serv_umed, serv_activo, tipo, tip_insumo, proveedor, grupo, codigo_sat, c_cveuni, c_nombre, iva) VALUES (7,'S0007','APLICACIÓN DE TOXINA CON SEDACION (QUIROFANO)',20000.00,5000.00,0.00,0.00,0.00,0.00,0.00,0.00,'CONSULTA','SI','3','CONSULTA OFTALMOLOGICA','INEO','SERVICIOS HOSPITALARIOS','85101502','E48','SERVICIO',0.16);
INSERT INTO `cat_servicios` (id_serv, serv_cve, serv_desc, serv_costo, serv_costo2, serv_costo3, serv_costo4, serv_costo5, serv_costo6, serv_costo7, serv_costo8, serv_umed, serv_activo, tipo, tip_insumo, proveedor, grupo, codigo_sat, c_cveuni, c_nombre, iva) VALUES (8,'S0008','APLICACIÓN DE TOXINA SIN SEDACION (QUIROFANO)',6000.00,1500.00,0.00,0.00,0.00,0.00,0.00,0.00,'CONSULTA','SI','3','CONSULTA OFTALMOLOGICA','INEO','SERVICIOS HOSPITALARIOS','85101502','E48','SERVICIO',0.16);
INSERT INTO `cat_servicios` (id_serv, serv_cve, serv_desc, serv_costo, serv_costo2, serv_costo3, serv_costo4, serv_costo5, serv_costo6, serv_costo7, serv_costo8, serv_umed, serv_activo, tipo, tip_insumo, proveedor, grupo, codigo_sat, c_cveuni, c_nombre, iva) VALUES (9,'S0009','CHALAZION',6000.00,1500.00,0.00,0.00,0.00,0.00,0.00,0.00,'CONSULTA','SI','3','CONSULTA OFTALMOLOGICA','INEO','SERVICIOS HOSPITALARIOS','85101502','E48','SERVICIO',0.16);
INSERT INTO `cat_servicios` (id_serv, serv_cve, serv_desc, serv_costo, serv_costo2, serv_costo3, serv_costo4, serv_costo5, serv_costo6, serv_costo7, serv_costo8, serv_umed, serv_activo, tipo, tip_insumo, proveedor, grupo, codigo_sat, c_cveuni, c_nombre, iva) VALUES (10,'S0010','CHALAZION / ANESTESIA (SEDACION)',8000.00,2500.00,0.00,0.00,0.00,0.00,0.00,0.00,'CONSULTA','SI','3','CONSULTA OFTALMOLOGICA','INEO','SERVICIOS HOSPITALARIOS','85101502','E48','SERVICIO',0.16);
INSERT INTO `cat_servicios` (id_serv, serv_cve, serv_desc, serv_costo, serv_costo2, serv_costo3, serv_costo4, serv_costo5, serv_costo6, serv_costo7, serv_costo8, serv_umed, serv_activo, tipo, tip_insumo, proveedor, grupo, codigo_sat, c_cveuni, c_nombre, iva) VALUES (11,'S0011','PTERIGION (CON AUTOINJERTO )  UN OJO',15000.00,3600.00,0.00,0.00,0.00,0.00,0.00,0.00,'CONSULTA','SI','3','CONSULTA OFTALMOLOGICA','INEO','SERVICIOS HOSPITALARIOS','85101502','E48','SERVICIO',0.16);
INSERT INTO `cat_servicios` (id_serv, serv_cve, serv_desc, serv_costo, serv_costo2, serv_costo3, serv_costo4, serv_costo5, serv_costo6, serv_costo7, serv_costo8, serv_umed, serv_activo, tipo, tip_insumo, proveedor, grupo, codigo_sat, c_cveuni, c_nombre, iva) VALUES (12,'S0012','PTERIGION (SIN AUTOINJERTO )  UN OJO',13000.00,3200.00,0.00,0.00,0.00,0.00,0.00,0.00,'CONSULTA','SI','3','CONSULTA OFTALMOLOGICA','INEO','SERVICIOS HOSPITALARIOS','85101502','E48','SERVICIO',0.16);
INSERT INTO `cat_servicios` (id_serv, serv_cve, serv_desc, serv_costo, serv_costo2, serv_costo3, serv_costo4, serv_costo5, serv_costo6, serv_costo7, serv_costo8, serv_umed, serv_activo, tipo, tip_insumo, proveedor, grupo, codigo_sat, c_cveuni, c_nombre, iva) VALUES (13,'S0013','EXPLORACION BAJO SEDACION',15500.00,4600.00,0.00,0.00,0.00,0.00,0.00,0.00,'CONSULTA','SI','3','CONSULTA OFTALMOLOGICA','INEO','SERVICIOS HOSPITALARIOS','85101502','E48','SERVICIO',0.16);
INSERT INTO `cat_servicios` (id_serv, serv_cve, serv_desc, serv_costo, serv_costo2, serv_costo3, serv_costo4, serv_costo5, serv_costo6, serv_costo7, serv_costo8, serv_umed, serv_activo, tipo, tip_insumo, proveedor, grupo, codigo_sat, c_cveuni, c_nombre, iva) VALUES (14,'S0014','MICROCIRUGIA DEL SEGMENTO ANTERIOR CATARATA',0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,'SERVICIO','SI','3','MICROCIRUGIA DEL SEGMENTO ANTERIOR CATARATA','INEO','SERVICIOS HOSPITALARIOS','85101502','E48','SERVICIO',0.16);
INSERT INTO `cat_servicios` (id_serv, serv_cve, serv_desc, serv_costo, serv_costo2, serv_costo3, serv_costo4, serv_costo5, serv_costo6, serv_costo7, serv_costo8, serv_umed, serv_activo, tipo, tip_insumo, proveedor, grupo, codigo_sat, c_cveuni, c_nombre, iva) VALUES (15,'S0015','EXTRACCION EXTRACAPSULAR CATARATA',25000.00,4000.00,0.00,0.00,0.00,0.00,0.00,0.00,'SERVICIO','SI','3','MICROCIRUGIA DEL SEGMENTO ANTERIOR CATARATA','INEO','SERVICIOS HOSPITALARIOS','85101502','E48','SERVICIO',0.16);
INSERT INTO `cat_servicios` (id_serv, serv_cve, serv_desc, serv_costo, serv_costo2, serv_costo3, serv_costo4, serv_costo5, serv_costo6, serv_costo7, serv_costo8, serv_umed, serv_activo, tipo, tip_insumo, proveedor, grupo, codigo_sat, c_cveuni, c_nombre, iva) VALUES (16,'S0016','FACOEMULSIFICACION  (POR OJO )',33000.00,6000.00,0.00,0.00,0.00,0.00,0.00,0.00,'SERVICIO','SI','3','MICROCIRUGIA DEL SEGMENTO ANTERIOR CATARATA','INEO','SERVICIOS HOSPITALARIOS','85101502','E48','SERVICIO',0.16);
INSERT INTO `cat_servicios` (id_serv, serv_cve, serv_desc, serv_costo, serv_costo2, serv_costo3, serv_costo4, serv_costo5, serv_costo6, serv_costo7, serv_costo8, serv_umed, serv_activo, tipo, tip_insumo, proveedor, grupo, codigo_sat, c_cveuni, c_nombre, iva) VALUES (17,'S0017','FACO CON LENTE INTRAOCULAR MONOFOCAL  (POR OJO )',0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,'SERVICIO','SI','3','MICROCIRUGIA DEL SEGMENTO ANTERIOR CATARATA','INEO','SERVICIOS HOSPITALARIOS','85101502','E48','SERVICIO',0.16);
INSERT INTO `cat_servicios` (id_serv, serv_cve, serv_desc, serv_costo, serv_costo2, serv_costo3, serv_costo4, serv_costo5, serv_costo6, serv_costo7, serv_costo8, serv_umed, serv_activo, tipo, tip_insumo, proveedor, grupo, codigo_sat, c_cveuni, c_nombre, iva) VALUES (18,'S0018','FACO CON LENTE INTRAOCULAR MONOFOCAL TORICO  (POR OJO )',0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,'SERVICIO','SI','3','MICROCIRUGIA DEL SEGMENTO ANTERIOR CATARATA','INEO','SERVICIOS HOSPITALARIOS','85101502','E48','SERVICIO',0.16);
INSERT INTO `cat_servicios` (id_serv, serv_cve, serv_desc, serv_costo, serv_costo2, serv_costo3, serv_costo4, serv_costo5, serv_costo6, serv_costo7, serv_costo8, serv_umed, serv_activo, tipo, tip_insumo, proveedor, grupo, codigo_sat, c_cveuni, c_nombre, iva) VALUES (19,'S0019','FACOEMULSIFICACION  CON LENTE TRIFOCAL  (POR OJO )',0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,'SERVICIO','SI','3','MICROCIRUGIA DEL SEGMENTO ANTERIOR CATARATA','INEO','SERVICIOS HOSPITALARIOS','85101502','E48','SERVICIO',0.16);
INSERT INTO `cat_servicios` (id_serv, serv_cve, serv_desc, serv_costo, serv_costo2, serv_costo3, serv_costo4, serv_costo5, serv_costo6, serv_costo7, serv_costo8, serv_umed, serv_activo, tipo, tip_insumo, proveedor, grupo, codigo_sat, c_cveuni, c_nombre, iva) VALUES (20,'S0020','FACOEMULSIFICACION CON LENTE MULTIFOCAL TORICO  (POR OJO )',60000.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,'SERVICIO','SI','3','MICROCIRUGIA DEL SEGMENTO ANTERIOR CATARATA','INEO','SERVICIOS HOSPITALARIOS','85101502','E48','SERVICIO',0.16);
INSERT INTO `cat_servicios` (id_serv, serv_cve, serv_desc, serv_costo, serv_costo2, serv_costo3, serv_costo4, serv_costo5, serv_costo6, serv_costo7, serv_costo8, serv_umed, serv_activo, tipo, tip_insumo, proveedor, grupo, codigo_sat, c_cveuni, c_nombre, iva) VALUES (21,'S0021','RETINA Y VITREO',0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,'SERVICIO','SI','3','RETINA Y VITREO','INEO','SERVICIOS HOSPITALARIOS','85101502','E48','SERVICIO',0.16);
INSERT INTO `cat_servicios` (id_serv, serv_cve, serv_desc, serv_costo, serv_costo2, serv_costo3, serv_costo4, serv_costo5, serv_costo6, serv_costo7, serv_costo8, serv_umed, serv_activo, tipo, tip_insumo, proveedor, grupo, codigo_sat, c_cveuni, c_nombre, iva) VALUES (22,'S0022','FACO + VITRECTOMIA',55000.00,13000.00,0.00,0.00,0.00,0.00,0.00,0.00,'SERVICIO','SI','3','RETINA Y VITREO','INEO','SERVICIOS HOSPITALARIOS','85101502','E48','SERVICIO',0.16);
INSERT INTO `cat_servicios` (id_serv, serv_cve, serv_desc, serv_costo, serv_costo2, serv_costo3, serv_costo4, serv_costo5, serv_costo6, serv_costo7, serv_costo8, serv_umed, serv_activo, tipo, tip_insumo, proveedor, grupo, codigo_sat, c_cveuni, c_nombre, iva) VALUES (23,'S0023','VITRECTOMIA  (POR OJO )',45000.00,11000.00,0.00,0.00,0.00,0.00,0.00,0.00,'SERVICIO','SI','3','RETINA Y VITREO','INEO','SERVICIOS HOSPITALARIOS','85101502','E48','SERVICIO',0.16);
INSERT INTO `cat_servicios` (id_serv, serv_cve, serv_desc, serv_costo, serv_costo2, serv_costo3, serv_costo4, serv_costo5, serv_costo6, serv_costo7, serv_costo8, serv_umed, serv_activo, tipo, tip_insumo, proveedor, grupo, codigo_sat, c_cveuni, c_nombre, iva) VALUES (24,'S0024','VITRECTOMIA + SILICON',0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,'SERVICIO','SI','3','RETINA Y VITREO','INEO','SERVICIOS HOSPITALARIOS','85101502','E48','SERVICIO',0.16);
INSERT INTO `cat_servicios` (id_serv, serv_cve, serv_desc, serv_costo, serv_costo2, serv_costo3, serv_costo4, serv_costo5, serv_costo6, serv_costo7, serv_costo8, serv_umed, serv_activo, tipo, tip_insumo, proveedor, grupo, codigo_sat, c_cveuni, c_nombre, iva) VALUES (25,'S0025','VITRECTOMIA ANTERIOR',33000.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,'SERVICIO','SI','3','RETINA Y VITREO','INEO','SERVICIOS HOSPITALARIOS','85101502','E48','SERVICIO',0.16);
INSERT INTO `cat_servicios` (id_serv, serv_cve, serv_desc, serv_costo, serv_costo2, serv_costo3, serv_costo4, serv_costo5, serv_costo6, serv_costo7, serv_costo8, serv_umed, serv_activo, tipo, tip_insumo, proveedor, grupo, codigo_sat, c_cveuni, c_nombre, iva) VALUES (26,'S0026','VITRECTOMIA POSTERIOR + ENDOFOTO',33000.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,'SERVICIO','SI','3','RETINA Y VITREO','INEO','SERVICIOS HOSPITALARIOS','85101502','E48','SERVICIO',0.16);
INSERT INTO `cat_servicios` (id_serv, serv_cve, serv_desc, serv_costo, serv_costo2, serv_costo3, serv_costo4, serv_costo5, serv_costo6, serv_costo7, serv_costo8, serv_umed, serv_activo, tipo, tip_insumo, proveedor, grupo, codigo_sat, c_cveuni, c_nombre, iva) VALUES (27,'S0027','CERCLAJE',0.00,3000.00,0.00,0.00,0.00,0.00,0.00,0.00,'SERVICIO','SI','3','RETINA Y VITREO','INEO','SERVICIOS HOSPITALARIOS','85101502','E48','SERVICIO',0.16);
INSERT INTO `cat_servicios` (id_serv, serv_cve, serv_desc, serv_costo, serv_costo2, serv_costo3, serv_costo4, serv_costo5, serv_costo6, serv_costo7, serv_costo8, serv_umed, serv_activo, tipo, tip_insumo, proveedor, grupo, codigo_sat, c_cveuni, c_nombre, iva) VALUES (28,'S0028','RETIRO DE SILICON',0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,'SERVICIO','SI','3','RETINA Y VITREO','INEO','SERVICIOS HOSPITALARIOS','85101502','E48','SERVICIO',0.16);
INSERT INTO `cat_servicios` (id_serv, serv_cve, serv_desc, serv_costo, serv_costo2, serv_costo3, serv_costo4, serv_costo5, serv_costo6, serv_costo7, serv_costo8, serv_umed, serv_activo, tipo, tip_insumo, proveedor, grupo, codigo_sat, c_cveuni, c_nombre, iva) VALUES (29,'S0029','RETINOPEXIA',0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,'SERVICIO','SI','3','RETINA Y VITREO','INEO','SERVICIOS HOSPITALARIOS','85101502','E48','SERVICIO',0.16);
INSERT INTO `cat_servicios` (id_serv, serv_cve, serv_desc, serv_costo, serv_costo2, serv_costo3, serv_costo4, serv_costo5, serv_costo6, serv_costo7, serv_costo8, serv_umed, serv_activo, tipo, tip_insumo, proveedor, grupo, codigo_sat, c_cveuni, c_nombre, iva) VALUES (30,'S0030','OCULOPLASTIA PARPADOS Y ORBITA',30000.00,4200.00,0.00,0.00,0.00,0.00,0.00,0.00,'SERVICIO','SI','3','RETINA Y VITREO','INEO','SERVICIOS HOSPITALARIOS','85101502','E48','SERVICIO',0.16);
INSERT INTO `cat_servicios` (id_serv, serv_cve, serv_desc, serv_costo, serv_costo2, serv_costo3, serv_costo4, serv_costo5, serv_costo6, serv_costo7, serv_costo8, serv_umed, serv_activo, tipo, tip_insumo, proveedor, grupo, codigo_sat, c_cveuni, c_nombre, iva) VALUES (31,'S0031','BLEFAROPLASTIA  ( 2 PARPADOS)',35000.00,4400.00,0.00,0.00,0.00,0.00,0.00,0.00,'SERVICIO','SI','3','RETINA Y VITREO','INEO','SERVICIOS HOSPITALARIOS','85101502','E48','SERVICIO',0.16);
INSERT INTO `cat_servicios` (id_serv, serv_cve, serv_desc, serv_costo, serv_costo2, serv_costo3, serv_costo4, serv_costo5, serv_costo6, serv_costo7, serv_costo8, serv_umed, serv_activo, tipo, tip_insumo, proveedor, grupo, codigo_sat, c_cveuni, c_nombre, iva) VALUES (32,'S0032','BLEFAROPLASTIA  ( 4 PARPADOS)',0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,'SERVICIO','SI','3','RETINA Y VITREO','INEO','SERVICIOS HOSPITALARIOS','85101502','E48','SERVICIO',0.16);
INSERT INTO `cat_servicios` (id_serv, serv_cve, serv_desc, serv_costo, serv_costo2, serv_costo3, serv_costo4, serv_costo5, serv_costo6, serv_costo7, serv_costo8, serv_umed, serv_activo, tipo, tip_insumo, proveedor, grupo, codigo_sat, c_cveuni, c_nombre, iva) VALUES (33,'S0033','BIOPSIA CONJUNTIVA',0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,'SERVICIO','SI','3','RETINA Y VITREO','INEO','SERVICIOS HOSPITALARIOS','85101502','E48','SERVICIO',0.16);
INSERT INTO `cat_servicios` (id_serv, serv_cve, serv_desc, serv_costo, serv_costo2, serv_costo3, serv_costo4, serv_costo5, serv_costo6, serv_costo7, serv_costo8, serv_umed, serv_activo, tipo, tip_insumo, proveedor, grupo, codigo_sat, c_cveuni, c_nombre, iva) VALUES (34,'S0034','BIOPSIA EXCISIONAL',0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,'SERVICIO','SI','3','RETINA Y VITREO','INEO','SERVICIOS HOSPITALARIOS','85101502','E48','SERVICIO',0.16);
INSERT INTO `cat_servicios` (id_serv, serv_cve, serv_desc, serv_costo, serv_costo2, serv_costo3, serv_costo4, serv_costo5, serv_costo6, serv_costo7, serv_costo8, serv_umed, serv_activo, tipo, tip_insumo, proveedor, grupo, codigo_sat, c_cveuni, c_nombre, iva) VALUES (35,'S0035','DACRIOINTUBACION CERRADA',30000.00,4000.00,0.00,0.00,0.00,0.00,0.00,0.00,'SERVICIO','SI','3','RETINA Y VITREO','INEO','SERVICIOS HOSPITALARIOS','85101502','E48','SERVICIO',0.16);
INSERT INTO `cat_servicios` (id_serv, serv_cve, serv_desc, serv_costo, serv_costo2, serv_costo3, serv_costo4, serv_costo5, serv_costo6, serv_costo7, serv_costo8, serv_umed, serv_activo, tipo, tip_insumo, proveedor, grupo, codigo_sat, c_cveuni, c_nombre, iva) VALUES (36,'S0036','DACRIOCISTORRINOSTOMIA',35000.00,5000.00,0.00,0.00,0.00,0.00,0.00,0.00,'SERVICIO','SI','3','RETINA Y VITREO','INEO','SERVICIOS HOSPITALARIOS','85101502','E48','SERVICIO',0.16);
INSERT INTO `cat_servicios` (id_serv, serv_cve, serv_desc, serv_costo, serv_costo2, serv_costo3, serv_costo4, serv_costo5, serv_costo6, serv_costo7, serv_costo8, serv_umed, serv_activo, tipo, tip_insumo, proveedor, grupo, codigo_sat, c_cveuni, c_nombre, iva) VALUES (37,'S0037','ENTROPION',0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,'SERVICIO','SI','3','RETINA Y VITREO','INEO','SERVICIOS HOSPITALARIOS','85101502','E48','SERVICIO',0.16);
INSERT INTO `cat_servicios` (id_serv, serv_cve, serv_desc, serv_costo, serv_costo2, serv_costo3, serv_costo4, serv_costo5, serv_costo6, serv_costo7, serv_costo8, serv_umed, serv_activo, tipo, tip_insumo, proveedor, grupo, codigo_sat, c_cveuni, c_nombre, iva) VALUES (38,'S0038','ENTROPION BILATERAL',0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,'SERVICIO','SI','3','RETINA Y VITREO','INEO','SERVICIOS HOSPITALARIOS','85101502','E48','SERVICIO',0.16);
INSERT INTO `cat_servicios` (id_serv, serv_cve, serv_desc, serv_costo, serv_costo2, serv_costo3, serv_costo4, serv_costo5, serv_costo6, serv_costo7, serv_costo8, serv_umed, serv_activo, tipo, tip_insumo, proveedor, grupo, codigo_sat, c_cveuni, c_nombre, iva) VALUES (39,'S0039','EVISCERACION',0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,'SERVICIO','SI','3','RETINA Y VITREO','INEO','SERVICIOS HOSPITALARIOS','85101502','E48','SERVICIO',0.16);
INSERT INTO `cat_servicios` (id_serv, serv_cve, serv_desc, serv_costo, serv_costo2, serv_costo3, serv_costo4, serv_costo5, serv_costo6, serv_costo7, serv_costo8, serv_umed, serv_activo, tipo, tip_insumo, proveedor, grupo, codigo_sat, c_cveuni, c_nombre, iva) VALUES (40,'S0040','ENUCLEACION',0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,'SERVICIO','SI','3','RETINA Y VITREO','INEO','SERVICIOS HOSPITALARIOS','85101502','E48','SERVICIO',0.16);
INSERT INTO `cat_servicios` (id_serv, serv_cve, serv_desc, serv_costo, serv_costo2, serv_costo3, serv_costo4, serv_costo5, serv_costo6, serv_costo7, serv_costo8, serv_umed, serv_activo, tipo, tip_insumo, proveedor, grupo, codigo_sat, c_cveuni, c_nombre, iva) VALUES (41,'S0041','PTOSIS',0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,'SERVICIO','SI','3','OCULOPLASTIA PARPADOS Y ORBITA','INEO','SERVICIOS HOSPITALARIOS','85101502','E48','SERVICIO',0.16);
INSERT INTO `cat_servicios` (id_serv, serv_cve, serv_desc, serv_costo, serv_costo2, serv_costo3, serv_costo4, serv_costo5, serv_costo6, serv_costo7, serv_costo8, serv_umed, serv_activo, tipo, tip_insumo, proveedor, grupo, codigo_sat, c_cveuni, c_nombre, iva) VALUES (42,'S0042','SONDEO DE VIAS LAGRIMALES',0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,'SERVICIO','SI','3','OCULOPLASTIA PARPADOS Y ORBITA','INEO','SERVICIOS HOSPITALARIOS','85101502','E48','SERVICIO',0.16);
INSERT INTO `cat_servicios` (id_serv, serv_cve, serv_desc, serv_costo, serv_costo2, serv_costo3, serv_costo4, serv_costo5, serv_costo6, serv_costo7, serv_costo8, serv_umed, serv_activo, tipo, tip_insumo, proveedor, grupo, codigo_sat, c_cveuni, c_nombre, iva) VALUES (43,'S0043','CORNEA',0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,'SERVICIO','SI','3','CORNEA','INEO','SERVICIOS HOSPITALARIOS','85101502','E48','SERVICIO',0.16);
INSERT INTO `cat_servicios` (id_serv, serv_cve, serv_desc, serv_costo, serv_costo2, serv_costo3, serv_costo4, serv_costo5, serv_costo6, serv_costo7, serv_costo8, serv_umed, serv_activo, tipo, tip_insumo, proveedor, grupo, codigo_sat, c_cveuni, c_nombre, iva) VALUES (44,'S0044','CIRUGIA REFRACTIVA PRK O TRAS PRK AMBOS OJOS ',25000.00,7000.00,0.00,0.00,0.00,0.00,0.00,0.00,'SERVICIO','SI','3','CORNEA','INEO','SERVICIOS HOSPITALARIOS','85101502','E48','SERVICIO',0.16);
INSERT INTO `cat_servicios` (id_serv, serv_cve, serv_desc, serv_costo, serv_costo2, serv_costo3, serv_costo4, serv_costo5, serv_costo6, serv_costo7, serv_costo8, serv_umed, serv_activo, tipo, tip_insumo, proveedor, grupo, codigo_sat, c_cveuni, c_nombre, iva) VALUES (45,'S0045','CIRUGIA REFRACTIVA PRK O TRAS PRK UN OJO ',15000.00,7000.00,0.00,0.00,0.00,0.00,0.00,0.00,'SERVICIO','SI','3','CORNEA','INEO','SERVICIOS HOSPITALARIOS','85101502','E48','SERVICIO',0.16);
INSERT INTO `cat_servicios` (id_serv, serv_cve, serv_desc, serv_costo, serv_costo2, serv_costo3, serv_costo4, serv_costo5, serv_costo6, serv_costo7, serv_costo8, serv_umed, serv_activo, tipo, tip_insumo, proveedor, grupo, codigo_sat, c_cveuni, c_nombre, iva) VALUES (46,'S0046','CROSSLINKING AMBOS OJOS ',28000.00,12000.00,0.00,0.00,0.00,0.00,0.00,0.00,'SERVICIO','SI','3','CORNEA','INEO','SERVICIOS HOSPITALARIOS','85101502','E48','SERVICIO',0.16);
INSERT INTO `cat_servicios` (id_serv, serv_cve, serv_desc, serv_costo, serv_costo2, serv_costo3, serv_costo4, serv_costo5, serv_costo6, serv_costo7, serv_costo8, serv_umed, serv_activo, tipo, tip_insumo, proveedor, grupo, codigo_sat, c_cveuni, c_nombre, iva) VALUES (47,'S0047','CROSSLINKING UN OJO ',18000.00,6000.00,0.00,0.00,0.00,0.00,0.00,0.00,'SERVICIO','SI','3','CORNEA','INEO','SERVICIOS HOSPITALARIOS','85101502','E48','SERVICIO',0.16);
INSERT INTO `cat_servicios` (id_serv, serv_cve, serv_desc, serv_costo, serv_costo2, serv_costo3, serv_costo4, serv_costo5, serv_costo6, serv_costo7, serv_costo8, serv_umed, serv_activo, tipo, tip_insumo, proveedor, grupo, codigo_sat, c_cveuni, c_nombre, iva) VALUES (48,'S0048','CIRUGIA LASIK (AMBOS OJOS )',25000.00,8000.00,0.00,0.00,0.00,0.00,0.00,0.00,'SERVICIO','SI','3','CORNEA','INEO','SERVICIOS HOSPITALARIOS','85101502','E48','SERVICIO',0.16);
INSERT INTO `cat_servicios` (id_serv, serv_cve, serv_desc, serv_costo, serv_costo2, serv_costo3, serv_costo4, serv_costo5, serv_costo6, serv_costo7, serv_costo8, serv_umed, serv_activo, tipo, tip_insumo, proveedor, grupo, codigo_sat, c_cveuni, c_nombre, iva) VALUES (49,'S0049','CIRUGIA LASIK (UN OJO )',18000.00,8000.00,0.00,0.00,0.00,0.00,0.00,0.00,'SERVICIO','SI','3','CORNEA','INEO','SERVICIOS HOSPITALARIOS','85101502','E48','SERVICIO',0.16);
INSERT INTO `cat_servicios` (id_serv, serv_cve, serv_desc, serv_costo, serv_costo2, serv_costo3, serv_costo4, serv_costo5, serv_costo6, serv_costo7, serv_costo8, serv_umed, serv_activo, tipo, tip_insumo, proveedor, grupo, codigo_sat, c_cveuni, c_nombre, iva) VALUES (50,'S0050','HERIDA CORNEAL/SUJETO A TIEMPOS ',6500.00,2200.00,0.00,0.00,0.00,0.00,0.00,0.00,'SERVICIO','SI','3','CORNEA','INEO','SERVICIOS HOSPITALARIOS','85101502','E48','SERVICIO',0.16);
INSERT INTO `cat_servicios` (id_serv, serv_cve, serv_desc, serv_costo, serv_costo2, serv_costo3, serv_costo4, serv_costo5, serv_costo6, serv_costo7, serv_costo8, serv_umed, serv_activo, tipo, tip_insumo, proveedor, grupo, codigo_sat, c_cveuni, c_nombre, iva) VALUES (51,'S0051','FEMTOSEGUNDO LASIK',30000.00,13000.00,0.00,0.00,0.00,0.00,0.00,0.00,'SERVICIO','SI','3','CORNEA','INEO','SERVICIOS HOSPITALARIOS','85101502','E48','SERVICIO',0.16);
INSERT INTO `cat_servicios` (id_serv, serv_cve, serv_desc, serv_costo, serv_costo2, serv_costo3, serv_costo4, serv_costo5, serv_costo6, serv_costo7, serv_costo8, serv_umed, serv_activo, tipo, tip_insumo, proveedor, grupo, codigo_sat, c_cveuni, c_nombre, iva) VALUES (52,'S0052','TRASPLANTE DE CORNEA ',115000.00,55000.00,0.00,0.00,0.00,0.00,0.00,0.00,'SERVICIO','SI','3','CORNEA','INEO','SERVICIOS HOSPITALARIOS','85101502','E48','SERVICIO',0.16);
INSERT INTO `cat_servicios` (id_serv, serv_cve, serv_desc, serv_costo, serv_costo2, serv_costo3, serv_costo4, serv_costo5, serv_costo6, serv_costo7, serv_costo8, serv_umed, serv_activo, tipo, tip_insumo, proveedor, grupo, codigo_sat, c_cveuni, c_nombre, iva) VALUES (53,'S0053','ESTRABISMO',0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,'SERVICIO','SI','3','ESTRABISMO','INEO','SERVICIOS HOSPITALARIOS','85101502','E48','SERVICIO',0.16);
INSERT INTO `cat_servicios` (id_serv, serv_cve, serv_desc, serv_costo, serv_costo2, serv_costo3, serv_costo4, serv_costo5, serv_costo6, serv_costo7, serv_costo8, serv_umed, serv_activo, tipo, tip_insumo, proveedor, grupo, codigo_sat, c_cveuni, c_nombre, iva) VALUES (54,'S0054','CORRECCION DE ESTRABISMO',35000.00,3500.00,0.00,0.00,0.00,0.00,0.00,0.00,'SERVICIO','SI','3','ESTRABISMO','INEO','SERVICIOS HOSPITALARIOS','85101502','E48','SERVICIO',0.16);
INSERT INTO `cat_servicios` (id_serv, serv_cve, serv_desc, serv_costo, serv_costo2, serv_costo3, serv_costo4, serv_costo5, serv_costo6, serv_costo7, serv_costo8, serv_umed, serv_activo, tipo, tip_insumo, proveedor, grupo, codigo_sat, c_cveuni, c_nombre, iva) VALUES (55,'S0055','GLAUCOMA',0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,'SERVICIO','SI','3','GLAUCOMA','INEO','SERVICIOS HOSPITALARIOS','85101502','E48','SERVICIO',0.16);
INSERT INTO `cat_servicios` (id_serv, serv_cve, serv_desc, serv_costo, serv_costo2, serv_costo3, serv_costo4, serv_costo5, serv_costo6, serv_costo7, serv_costo8, serv_umed, serv_activo, tipo, tip_insumo, proveedor, grupo, codigo_sat, c_cveuni, c_nombre, iva) VALUES (56,'S0056','COLOCACION DE VALVULA AMHED',28000.00,2800.00,0.00,0.00,0.00,0.00,0.00,0.00,'SERVICIO','SI','3','GLAUCOMA','INEO','SERVICIOS HOSPITALARIOS','85101502','E48','SERVICIO',0.16);
INSERT INTO `cat_servicios` (id_serv, serv_cve, serv_desc, serv_costo, serv_costo2, serv_costo3, serv_costo4, serv_costo5, serv_costo6, serv_costo7, serv_costo8, serv_umed, serv_activo, tipo, tip_insumo, proveedor, grupo, codigo_sat, c_cveuni, c_nombre, iva) VALUES (57,'S0057','TRABECULETOMIA',6000.00,3000.00,0.00,0.00,0.00,0.00,0.00,0.00,'SERVICIO','SI','3','GLAUCOMA','INEO','SERVICIOS HOSPITALARIOS','85101502','E48','SERVICIO',0.16);
INSERT INTO `cat_servicios` (id_serv, serv_cve, serv_desc, serv_costo, serv_costo2, serv_costo3, serv_costo4, serv_costo5, serv_costo6, serv_costo7, serv_costo8, serv_umed, serv_activo, tipo, tip_insumo, proveedor, grupo, codigo_sat, c_cveuni, c_nombre, iva) VALUES (58,'S0058','TRABE+MITOMICINA',0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,'SERVICIO','SI','3','GLAUCOMA','INEO','SERVICIOS HOSPITALARIOS','85101502','E48','SERVICIO',0.16);
INSERT INTO `cat_servicios` (id_serv, serv_cve, serv_desc, serv_costo, serv_costo2, serv_costo3, serv_costo4, serv_costo5, serv_costo6, serv_costo7, serv_costo8, serv_umed, serv_activo, tipo, tip_insumo, proveedor, grupo, codigo_sat, c_cveuni, c_nombre, iva) VALUES (59,'S0059','HORA EXTRA DE QUIROFANO ',0.00,1300.00,0.00,0.00,0.00,0.00,0.00,0.00,'SERVICIO','SI','3','GLAUCOMA','INEO','SERVICIOS HOSPITALARIOS','85101502','E48','SERVICIO',0.16);
INSERT INTO `cat_servicios` (id_serv, serv_cve, serv_desc, serv_costo, serv_costo2, serv_costo3, serv_costo4, serv_costo5, serv_costo6, serv_costo7, serv_costo8, serv_umed, serv_activo, tipo, tip_insumo, proveedor, grupo, codigo_sat, c_cveuni, c_nombre, iva) VALUES (60,'S0060','CICLO CRIO TERAPIA ',1700.00,1700.00,0.00,0.00,0.00,0.00,0.00,0.00,'SERVICIO','SI','3','GLAUCOMA','INEO','SERVICIOS HOSPITALARIOS','85101502','E48','SERVICIO',0.16);
INSERT INTO `cat_servicios` (id_serv, serv_cve, serv_desc, serv_costo, serv_costo2, serv_costo3, serv_costo4, serv_costo5, serv_costo6, serv_costo7, serv_costo8, serv_umed, serv_activo, tipo, tip_insumo, proveedor, grupo, codigo_sat, c_cveuni, c_nombre, iva) VALUES (61,'S0061','MAQUINA DE ANESTESIA ',3000.00,3000.00,0.00,0.00,0.00,0.00,0.00,0.00,'SERVICIO','SI','3','GLAUCOMA','INEO','SERVICIOS HOSPITALARIOS','85101502','E48','SERVICIO',0.16);
INSERT INTO `cat_servicios` (id_serv, serv_cve, serv_desc, serv_costo, serv_costo2, serv_costo3, serv_costo4, serv_costo5, serv_costo6, serv_costo7, serv_costo8, serv_umed, serv_activo, tipo, tip_insumo, proveedor, grupo, codigo_sat, c_cveuni, c_nombre, iva) VALUES (62,'S0062','HONORARIOS ANESTESIOLOGO (SEDACIÓN)',3000.00,3000.00,0.00,0.00,0.00,0.00,0.00,0.00,'SERVICIO','SI','3','GLAUCOMA','INEO','SERVICIOS HOSPITALARIOS','85101502','E48','SERVICIO',0.16);
INSERT INTO `cat_servicios` (id_serv, serv_cve, serv_desc, serv_costo, serv_costo2, serv_costo3, serv_costo4, serv_costo5, serv_costo6, serv_costo7, serv_costo8, serv_umed, serv_activo, tipo, tip_insumo, proveedor, grupo, codigo_sat, c_cveuni, c_nombre, iva) VALUES (63,'S0063','HONORARIOS ANESTESIOLOGO (GENERAL)',5000.00,5000.00,0.00,0.00,0.00,0.00,0.00,0.00,'SERVICIO','SI','3','GLAUCOMA','INEO','SERVICIOS HOSPITALARIOS','85101502','E48','SERVICIO',0.16);
INSERT INTO `cat_servicios` (id_serv, serv_cve, serv_desc, serv_costo, serv_costo2, serv_costo3, serv_costo4, serv_costo5, serv_costo6, serv_costo7, serv_costo8, serv_umed, serv_activo, tipo, tip_insumo, proveedor, grupo, codigo_sat, c_cveuni, c_nombre, iva) VALUES (64,'S0064',' LASER',0.00,0.00,0.00,4000.00,0.00,0.00,0.00,0.00,'SERVICIO','SI','3','SERVICIOS HOSPITALARIOS','INEO','SERVICIOS HOSPITALARIOS','85101502','E48','SERVICIO',0.16);
INSERT INTO `cat_servicios` (id_serv, serv_cve, serv_desc, serv_costo, serv_costo2, serv_costo3, serv_costo4, serv_costo5, serv_costo6, serv_costo7, serv_costo8, serv_umed, serv_activo, tipo, tip_insumo, proveedor, grupo, codigo_sat, c_cveuni, c_nombre, iva) VALUES (65,'S0065','CAPSULOTOMIA (LASER YAG) UNO O DOS OJOS ',5000.00,1500.00,0.00,0.00,0.00,0.00,0.00,0.00,'SERVICIO','SI','3','LASER','INEO','SERVICIOS HOSPITALARIOS','85101502','E48','SERVICIO',0.16);
INSERT INTO `cat_servicios` (id_serv, serv_cve, serv_desc, serv_costo, serv_costo2, serv_costo3, serv_costo4, serv_costo5, serv_costo6, serv_costo7, serv_costo8, serv_umed, serv_activo, tipo, tip_insumo, proveedor, grupo, codigo_sat, c_cveuni, c_nombre, iva) VALUES (66,'S0066','IRIDOTOMIA (LASER YAG) UNO O DOS OJOS ',5000.00,1500.00,0.00,0.00,0.00,0.00,0.00,0.00,'SERVICIO','SI','3','LASER','INEO','SERVICIOS HOSPITALARIOS','85101502','E48','SERVICIO',0.16);
INSERT INTO `cat_servicios` (id_serv, serv_cve, serv_desc, serv_costo, serv_costo2, serv_costo3, serv_costo4, serv_costo5, serv_costo6, serv_costo7, serv_costo8, serv_umed, serv_activo, tipo, tip_insumo, proveedor, grupo, codigo_sat, c_cveuni, c_nombre, iva) VALUES (67,'S0067','FOTOCOAGULACION (LASER ARGON() UN  OJO ',5000.00,1500.00,0.00,0.00,0.00,0.00,0.00,0.00,'SERVICIO','SI','3','LASER','INEO','SERVICIOS HOSPITALARIOS','85101502','E48','SERVICIO',0.16);
INSERT INTO `cat_servicios` (id_serv, serv_cve, serv_desc, serv_costo, serv_costo2, serv_costo3, serv_costo4, serv_costo5, serv_costo6, serv_costo7, serv_costo8, serv_umed, serv_activo, tipo, tip_insumo, proveedor, grupo, codigo_sat, c_cveuni, c_nombre, iva) VALUES (68,'S0068','FOTOCOAGULACION (LASER ARGON() AMBOS OJO ',6500.00,1500.00,0.00,0.00,0.00,0.00,0.00,0.00,'SERVICIO','SI','3','LASER','INEO','SERVICIOS HOSPITALARIOS','85101502','E48','SERVICIO',0.16);
INSERT INTO `cat_servicios` (id_serv, serv_cve, serv_desc, serv_costo, serv_costo2, serv_costo3, serv_costo4, serv_costo5, serv_costo6, serv_costo7, serv_costo8, serv_umed, serv_activo, tipo, tip_insumo, proveedor, grupo, codigo_sat, c_cveuni, c_nombre, iva) VALUES (69,'S0069','CÁLCULO DEL OJO INMERSIÓN (UN OJO)',2000.00,1000.00,0.00,0.00,0.00,0.00,0.00,0.00,'ESTUDIO','SI','3','GABINETE','INEO','IMAGENOLOGIA','85121801','E48','SERVICIO',0.16);
INSERT INTO `cat_servicios` (id_serv, serv_cve, serv_desc, serv_costo, serv_costo2, serv_costo3, serv_costo4, serv_costo5, serv_costo6, serv_costo7, serv_costo8, serv_umed, serv_activo, tipo, tip_insumo, proveedor, grupo, codigo_sat, c_cveuni, c_nombre, iva) VALUES (70,'S0070','CÁLCULO DEL OJO INMERSIÓN (AMBOS OJOS)',2000.00,1000.00,0.00,0.00,0.00,0.00,0.00,0.00,'ESTUDIO','SI','3','GABINETE','INEO','IMAGENOLOGIA','85121801','E48','SERVICIO',0.16);
INSERT INTO `cat_servicios` (id_serv, serv_cve, serv_desc, serv_costo, serv_costo2, serv_costo3, serv_costo4, serv_costo5, serv_costo6, serv_costo7, serv_costo8, serv_umed, serv_activo, tipo, tip_insumo, proveedor, grupo, codigo_sat, c_cveuni, c_nombre, iva) VALUES (71,'S0071','CÁLCULO DEL IOL MASTER (LENSTAR)',2000.00,1000.00,0.00,0.00,0.00,0.00,0.00,0.00,'ESTUDIO','SI','3','GABINETE','INEO','IMAGENOLOGIA','85121801','E48','SERVICIO',0.16);
INSERT INTO `cat_servicios` (id_serv, serv_cve, serv_desc, serv_costo, serv_costo2, serv_costo3, serv_costo4, serv_costo5, serv_costo6, serv_costo7, serv_costo8, serv_umed, serv_activo, tipo, tip_insumo, proveedor, grupo, codigo_sat, c_cveuni, c_nombre, iva) VALUES (72,'S0072','CAMPOS VISUALES DE HUMPHREY (1 O 2 OJOS)',1500.00,1000.00,0.00,0.00,0.00,0.00,0.00,0.00,'ESTUDIO','SI','3','GABINETE','INEO','IMAGENOLOGIA','85121801','E48','SERVICIO',0.16);
INSERT INTO `cat_servicios` (id_serv, serv_cve, serv_desc, serv_costo, serv_costo2, serv_costo3, serv_costo4, serv_costo5, serv_costo6, serv_costo7, serv_costo8, serv_umed, serv_activo, tipo, tip_insumo, proveedor, grupo, codigo_sat, c_cveuni, c_nombre, iva) VALUES (73,'S0073','TOPOGRAFÍA CORNEAL',1200.00,1000.00,0.00,0.00,0.00,0.00,0.00,0.00,'ESTUDIO','SI','3','GABINETE','INEO','IMAGENOLOGIA','85121801','E48','SERVICIO',0.16);
INSERT INTO `cat_servicios` (id_serv, serv_cve, serv_desc, serv_costo, serv_costo2, serv_costo3, serv_costo4, serv_costo5, serv_costo6, serv_costo7, serv_costo8, serv_umed, serv_activo, tipo, tip_insumo, proveedor, grupo, codigo_sat, c_cveuni, c_nombre, iva) VALUES (74,'S0074','OCT DE NERVIO ÓPTICO (1 O 2 OJOS)',1200.00,1000.00,0.00,0.00,0.00,0.00,0.00,0.00,'ESTUDIO','SI','3','GABINETE','INEO','IMAGENOLOGIA','85121801','E48','SERVICIO',0.16);
INSERT INTO `cat_servicios` (id_serv, serv_cve, serv_desc, serv_costo, serv_costo2, serv_costo3, serv_costo4, serv_costo5, serv_costo6, serv_costo7, serv_costo8, serv_umed, serv_activo, tipo, tip_insumo, proveedor, grupo, codigo_sat, c_cveuni, c_nombre, iva) VALUES (75,'S0075','OCT DE MÁCULA',1400.00,1000.00,0.00,0.00,0.00,0.00,0.00,0.00,'ESTUDIO','SI','3','GABINETE','INEO','IMAGENOLOGIA','85121801','E48','SERVICIO',0.16);
INSERT INTO `cat_servicios` (id_serv, serv_cve, serv_desc, serv_costo, serv_costo2, serv_costo3, serv_costo4, serv_costo5, serv_costo6, serv_costo7, serv_costo8, serv_umed, serv_activo, tipo, tip_insumo, proveedor, grupo, codigo_sat, c_cveuni, c_nombre, iva) VALUES (76,'S0076','ANGIOGRAFÍA DE RETINA CON FLUORESCENCIA (1 O 2 OJOS)',2200.00,1000.00,0.00,0.00,0.00,0.00,0.00,0.00,'ESTUDIO','SI','3','GABINETE','INEO','IMAGENOLOGIA','85121801','E48','SERVICIO',0.16);
INSERT INTO `cat_servicios` (id_serv, serv_cve, serv_desc, serv_costo, serv_costo2, serv_costo3, serv_costo4, serv_costo5, serv_costo6, serv_costo7, serv_costo8, serv_umed, serv_activo, tipo, tip_insumo, proveedor, grupo, codigo_sat, c_cveuni, c_nombre, iva) VALUES (77,'S0077','PAQUIMETRÍA ULTRASÓNICA',500.00,1000.00,0.00,0.00,0.00,0.00,0.00,0.00,'ESTUDIO','SI','3','GABINETE','INEO','IMAGENOLOGIA','85121801','E48','SERVICIO',0.16);
INSERT INTO `cat_servicios` (id_serv, serv_cve, serv_desc, serv_costo, serv_costo2, serv_costo3, serv_costo4, serv_costo5, serv_costo6, serv_costo7, serv_costo8, serv_umed, serv_activo, tipo, tip_insumo, proveedor, grupo, codigo_sat, c_cveuni, c_nombre, iva) VALUES (78,'S0078','MICROSCOPÍA ESPECULAR (AMBOS OJOS)',700.00,1000.00,0.00,0.00,0.00,0.00,0.00,0.00,'ESTUDIO','SI','3','GABINETE','INEO','IMAGENOLOGIA','85121801','E48','SERVICIO',0.16);
INSERT INTO `cat_servicios` (id_serv, serv_cve, serv_desc, serv_costo, serv_costo2, serv_costo3, serv_costo4, serv_costo5, serv_costo6, serv_costo7, serv_costo8, serv_umed, serv_activo, tipo, tip_insumo, proveedor, grupo, codigo_sat, c_cveuni, c_nombre, iva) VALUES (79,'S0079','MICROSCOPÍA ESPECULAR (UN OJO)',500.00,1000.00,0.00,0.00,0.00,0.00,0.00,0.00,'ESTUDIO','SI','3','GABINETE','INEO','IMAGENOLOGIA','85121801','E48','SERVICIO',0.16);
INSERT INTO `cat_servicios` (id_serv, serv_cve, serv_desc, serv_costo, serv_costo2, serv_costo3, serv_costo4, serv_costo5, serv_costo6, serv_costo7, serv_costo8, serv_umed, serv_activo, tipo, tip_insumo, proveedor, grupo, codigo_sat, c_cveuni, c_nombre, iva) VALUES (80,'S0080','ULTRASONIDO ECO MODO A (UN OJO) CÁLCULO DE LENTE',1000.00,1000.00,0.00,0.00,0.00,0.00,0.00,0.00,'ESTUDIO','SI','3','GABINETE','INEO','IMAGENOLOGIA','85121801','E48','SERVICIO',0.16);
INSERT INTO `cat_servicios` (id_serv, serv_cve, serv_desc, serv_costo, serv_costo2, serv_costo3, serv_costo4, serv_costo5, serv_costo6, serv_costo7, serv_costo8, serv_umed, serv_activo, tipo, tip_insumo, proveedor, grupo, codigo_sat, c_cveuni, c_nombre, iva) VALUES (81,'S0081','ULTRASONIDO ECO MODO A (AMBOS OJOS) CÁLCULO DE LENTE',1500.00,1000.00,0.00,0.00,0.00,0.00,0.00,0.00,'ESTUDIO','SI','3','GABINETE','INEO','IMAGENOLOGIA','85121801','E48','SERVICIO',0.16);
INSERT INTO `cat_servicios` (id_serv, serv_cve, serv_desc, serv_costo, serv_costo2, serv_costo3, serv_costo4, serv_costo5, serv_costo6, serv_costo7, serv_costo8, serv_umed, serv_activo, tipo, tip_insumo, proveedor, grupo, codigo_sat, c_cveuni, c_nombre, iva) VALUES (82,'S0082','ULTRASONIDO ECO MODO B (UN OJO)',1600.00,1000.00,0.00,0.00,0.00,0.00,0.00,0.00,'ESTUDIO','SI','3','GABINETE','INEO','IMAGENOLOGIA','85121801','E48','SERVICIO',0.16);
INSERT INTO `cat_servicios` (id_serv, serv_cve, serv_desc, serv_costo, serv_costo2, serv_costo3, serv_costo4, serv_costo5, serv_costo6, serv_costo7, serv_costo8, serv_umed, serv_activo, tipo, tip_insumo, proveedor, grupo, codigo_sat, c_cveuni, c_nombre, iva) VALUES (83,'S0083','ULTRASONIDO ECO MODO B (AMBOS OJOS)',1600.00,1000.00,0.00,0.00,0.00,0.00,0.00,0.00,'ESTUDIO','SI','3','GABINETE','INEO','IMAGENOLOGIA','85121801','E48','SERVICIO',0.16);
INSERT INTO `cat_servicios` (id_serv, serv_cve, serv_desc, serv_costo, serv_costo2, serv_costo3, serv_costo4, serv_costo5, serv_costo6, serv_costo7, serv_costo8, serv_umed, serv_activo, tipo, tip_insumo, proveedor, grupo, codigo_sat, c_cveuni, c_nombre, iva) VALUES (84,'S0084','ULTRASONIDO ECO MODO A Y B (UN OJO)',1600.00,1000.00,0.00,0.00,0.00,0.00,0.00,0.00,'ESTUDIO','SI','3','GABINETE','INEO','IMAGENOLOGIA','85121801','E48','SERVICIO',0.16);
INSERT INTO `cat_servicios` (id_serv, serv_cve, serv_desc, serv_costo, serv_costo2, serv_costo3, serv_costo4, serv_costo5, serv_costo6, serv_costo7, serv_costo8, serv_umed, serv_activo, tipo, tip_insumo, proveedor, grupo, codigo_sat, c_cveuni, c_nombre, iva) VALUES (85,'S0085','ULTRASONIDO ECO MODO A Y B (AMBOS OJOS)',2500.00,1000.00,0.00,0.00,0.00,0.00,0.00,0.00,'ESTUDIO','SI','3','GABINETE','INEO','IMAGENOLOGIA','85121801','E48','SERVICIO',0.16);
INSERT INTO `cat_servicios` (id_serv, serv_cve, serv_desc, serv_costo, serv_costo2, serv_costo3, serv_costo4, serv_costo5, serv_costo6, serv_costo7, serv_costo8, serv_umed, serv_activo, tipo, tip_insumo, proveedor, grupo, codigo_sat, c_cveuni, c_nombre, iva) VALUES (86,'S0086','FOTOGRAFÍA DE FONDO (UN OJO)',500.00,1000.00,0.00,0.00,0.00,0.00,0.00,0.00,'ESTUDIO','SI','3','GABINETE','INEO','IMAGENOLOGIA','85121801','E48','SERVICIO',0.16);
INSERT INTO `cat_servicios` (id_serv, serv_cve, serv_desc, serv_costo, serv_costo2, serv_costo3, serv_costo4, serv_costo5, serv_costo6, serv_costo7, serv_costo8, serv_umed, serv_activo, tipo, tip_insumo, proveedor, grupo, codigo_sat, c_cveuni, c_nombre, iva) VALUES (87,'S0087','HORA QUIROFANO',1400.00,1000.00,0.00,0.00,0.00,0.00,0.00,1500.00,'HORA','SI','4','CEYE','INEO','SERVICIOS HOSPITALARIOS','85101502','E48','SERVICIO',0.16);
INSERT INTO `cat_servicios` (id_serv, serv_cve, serv_desc, serv_costo, serv_costo2, serv_costo3, serv_costo4, serv_costo5, serv_costo6, serv_costo7, serv_costo8, serv_umed, serv_activo, tipo, tip_insumo, proveedor, grupo, codigo_sat, c_cveuni, c_nombre, iva) VALUES (88,'','Pinzas colibri',450.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,'Instrumental / equip','SI','4','CEYE','INEO','SERVICIOS HOSPITALARIOS','85101502','E48','SERVICIO',0.16);
INSERT INTO `cat_servicios` (id_serv, serv_cve, serv_desc, serv_costo, serv_costo2, serv_costo3, serv_costo4, serv_costo5, serv_costo6, serv_costo7, serv_costo8, serv_umed, serv_activo, tipo, tip_insumo, proveedor, grupo, codigo_sat, c_cveuni, c_nombre, iva) VALUES (89,'','Blefaros',450.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,'Instrumental / equip','SI','4','CEYE','INEO','SERVICIOS HOSPITALARIOS','85101502','E48','SERVICIO',0.16);
INSERT INTO `cat_servicios` (id_serv, serv_cve, serv_desc, serv_costo, serv_costo2, serv_costo3, serv_costo4, serv_costo5, serv_costo6, serv_costo7, serv_costo8, serv_umed, serv_activo, tipo, tip_insumo, proveedor, grupo, codigo_sat, c_cveuni, c_nombre, iva) VALUES (90,'','Tijeras de Weskott',450.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,'Instrumental / equip','SI','4','CEYE','INEO','SERVICIOS HOSPITALARIOS','85101502','E48','SERVICIO',0.16);
INSERT INTO `cat_servicios` (id_serv, serv_cve, serv_desc, serv_costo, serv_costo2, serv_costo3, serv_costo4, serv_costo5, serv_costo6, serv_costo7, serv_costo8, serv_umed, serv_activo, tipo, tip_insumo, proveedor, grupo, codigo_sat, c_cveuni, c_nombre, iva) VALUES (91,'','Pinzas rectas finas',450.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,'Instrumental / equip','SI','4','CEYE','INEO','SERVICIOS HOSPITALARIOS','85101502','E48','SERVICIO',0.16);
INSERT INTO `cat_servicios` (id_serv, serv_cve, serv_desc, serv_costo, serv_costo2, serv_costo3, serv_costo4, serv_costo5, serv_costo6, serv_costo7, serv_costo8, serv_umed, serv_activo, tipo, tip_insumo, proveedor, grupo, codigo_sat, c_cveuni, c_nombre, iva) VALUES (92,'','Desmarres palo de golf',450.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,'Instrumental / equip','SI','4','CEYE','INEO','SERVICIOS HOSPITALARIOS','85101502','E48','SERVICIO',0.16);
INSERT INTO `cat_servicios` (id_serv, serv_cve, serv_desc, serv_costo, serv_costo2, serv_costo3, serv_costo4, serv_costo5, serv_costo6, serv_costo7, serv_costo8, serv_umed, serv_activo, tipo, tip_insumo, proveedor, grupo, codigo_sat, c_cveuni, c_nombre, iva) VALUES (93,'','Marcador estéril',300.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,'Instrumental / equip','SI','4','CEYE','INEO','SERVICIOS HOSPITALARIOS','85101502','E48','SERVICIO',0.16);
INSERT INTO `cat_servicios` (id_serv, serv_cve, serv_desc, serv_costo, serv_costo2, serv_costo3, serv_costo4, serv_costo5, serv_costo6, serv_costo7, serv_costo8, serv_umed, serv_activo, tipo, tip_insumo, proveedor, grupo, codigo_sat, c_cveuni, c_nombre, iva) VALUES (94,'','Cauterio o diatermia',600.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,'Instrumental / equip','SI','4','CEYE','INEO','SERVICIOS HOSPITALARIOS','85101502','E48','SERVICIO',0.16);
INSERT INTO `cat_servicios` (id_serv, serv_cve, serv_desc, serv_costo, serv_costo2, serv_costo3, serv_costo4, serv_costo5, serv_costo6, serv_costo7, serv_costo8, serv_umed, serv_activo, tipo, tip_insumo, proveedor, grupo, codigo_sat, c_cveuni, c_nombre, iva) VALUES (95,'','Vitrectomo',1667.00,0.00,0.00,0.00,0.00,0.00,0.00,1900.00,'Quirófano','SI','4','CEYE','INEO','SERVICIOS HOSPITALARIOS','85101502','E48','SERVICIO',0.16);
INSERT INTO `cat_servicios` (id_serv, serv_cve, serv_desc, serv_costo, serv_costo2, serv_costo3, serv_costo4, serv_costo5, serv_costo6, serv_costo7, serv_costo8, serv_umed, serv_activo, tipo, tip_insumo, proveedor, grupo, codigo_sat, c_cveuni, c_nombre, iva) VALUES (96,'','Endoiluminador',980.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,'Quirófano','SI','4','CEYE','INEO','SERVICIOS HOSPITALARIOS','85101502','E48','SERVICIO',0.16);
INSERT INTO `cat_servicios` (id_serv, serv_cve, serv_desc, serv_costo, serv_costo2, serv_costo3, serv_costo4, serv_costo5, serv_costo6, serv_costo7, serv_costo8, serv_umed, serv_activo, tipo, tip_insumo, proveedor, grupo, codigo_sat, c_cveuni, c_nombre, iva) VALUES (97,'','Microscopio quirurgico',499.00,0.00,0.00,0.00,0.00,0.00,0.00,921.00,'Quirófano','SI','4','CEYE','INEO','SERVICIOS HOSPITALARIOS','85101502','E48','SERVICIO',0.16);
INSERT INTO `cat_servicios` (id_serv, serv_cve, serv_desc, serv_costo, serv_costo2, serv_costo3, serv_costo4, serv_costo5, serv_costo6, serv_costo7, serv_costo8, serv_umed, serv_activo, tipo, tip_insumo, proveedor, grupo, codigo_sat, c_cveuni, c_nombre, iva) VALUES (98,'S0098','CIRUGÍA PROGRAMADA',1901.00,1902.00,1903.00,1904.00,1905.00,1906.00,1907.00,1908.00,'CONSULTA','SI','3','SERVICIOS HOSPITALARIOS','1','SERVICIOS HOSPITALARIOS','edwef','E483','SERVICIO',0.16);
INSERT INTO `cat_servicios` (id_serv, serv_cve, serv_desc, serv_costo, serv_costo2, serv_costo3, serv_costo4, serv_costo5, serv_costo6, serv_costo7, serv_costo8, serv_umed, serv_activo, tipo, tip_insumo, proveedor, grupo, codigo_sat, c_cveuni, c_nombre, iva) VALUES (99,'S0099','CIRUGÍA DE URGENCIA',1801.00,1802.00,1803.00,1804.00,1805.00,1806.00,1807.00,1808.00,'CONSULTA','SI','3','SERVICIOS HOSPITALARIOS','1','SERVICIOS HOSPITALARIOS','50210','E79','SERVICIO',0.16);
CREATE TABLE `cuenta_paciente` (
  `id_cargo` int(11) NOT NULL AUTO_INCREMENT,
  `id_atencion` int(11) NOT NULL,
  `fecha` datetime NOT NULL,
  `descripcion` varchar(150) DEFAULT NULL,
  `cantidad` int(11) DEFAULT 1,
  `precio` decimal(10,2) DEFAULT NULL,
  `subtotal` decimal(10,2) DEFAULT NULL,
  PRIMARY KEY (`id_cargo`),
  KEY `id_atencion` (`id_atencion`),
  CONSTRAINT `cuenta_paciente_ibfk_1` FOREIGN KEY (`id_atencion`) REFERENCES `atencion` (`id_atencion`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE `depositos_pserv` (
  `id_depserv` int(10) NOT NULL DEFAULT 0,
  `id_pac` int(10) NOT NULL,
  `deposito` double(10,2) NOT NULL,
  `tipo_pago` varchar(30) CHARACTER SET utf8 COLLATE utf8_general_ci NOT NULL,
  `id_usua` int(10) NOT NULL,
  `fecha` datetime NOT NULL,
  `responsable` varchar(100) CHARACTER SET utf8 COLLATE utf8_general_ci NOT NULL,
  `total` double(10,2) NOT NULL,
  `tipo` varchar(50) CHARACTER SET utf8 COLLATE utf8_general_ci NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE `diagnosticos` (
  `id_diagnostico` int(11) NOT NULL AUTO_INCREMENT,
  `id_atencion` int(11) NOT NULL,
  `diagnostico_principal` varchar(255) NOT NULL,
  `diagnosticos_secundarios` text DEFAULT NULL,
  `observaciones` text DEFAULT NULL,
  `fecha_registro` datetime DEFAULT current_timestamp(),
  PRIMARY KEY (`id_diagnostico`),
  KEY `fk_diag_atencion` (`id_atencion`),
  CONSTRAINT `fk_diag_atencion` FOREIGN KEY (`id_atencion`) REFERENCES `atencion` (`id_atencion`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

INSERT INTO `diagnosticos` (id_diagnostico, id_atencion, diagnostico_principal, diagnosticos_secundarios, observaciones, fecha_registro) VALUES (1,3,'Hola cara de bola ','diagnóstico wodjeo','observaciones prueba nueva ','2026-01-26 13:57:25');
CREATE TABLE `diagnosticos_historial` (
  `id_historial` int(11) NOT NULL AUTO_INCREMENT,
  `id_atencion` int(11) NOT NULL,
  `diagnostico_principal` text NOT NULL,
  `diagnosticos_secundarios` text DEFAULT NULL,
  `observaciones` text DEFAULT NULL,
  `id_medico` int(11) NOT NULL,
  `fecha_registro` datetime DEFAULT current_timestamp(),
  PRIMARY KEY (`id_historial`),
  KEY `id_atencion` (`id_atencion`),
  KEY `id_medico` (`id_medico`),
  CONSTRAINT `diagnosticos_historial_ibfk_1` FOREIGN KEY (`id_atencion`) REFERENCES `atencion` (`id_atencion`),
  CONSTRAINT `diagnosticos_historial_ibfk_2` FOREIGN KEY (`id_medico`) REFERENCES `users` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

INSERT INTO `diagnosticos_historial` (id_historial, id_atencion, diagnostico_principal, diagnosticos_secundarios, observaciones, id_medico, fecha_registro) VALUES (1,3,'Hola ','Hola dos ','observaciones ',1,'2026-01-26 14:30:47');
INSERT INTO `diagnosticos_historial` (id_historial, id_atencion, diagnostico_principal, diagnosticos_secundarios, observaciones, id_medico, fecha_registro) VALUES (2,3,'Hola 2','Hola dos ','observaciones ',1,'2026-01-26 14:30:52');
INSERT INTO `diagnosticos_historial` (id_historial, id_atencion, diagnostico_principal, diagnosticos_secundarios, observaciones, id_medico, fecha_registro) VALUES (3,3,'Hola 2','Hola dos ','observaciones 123',1,'2026-01-26 14:31:06');
INSERT INTO `diagnosticos_historial` (id_historial, id_atencion, diagnostico_principal, diagnosticos_secundarios, observaciones, id_medico, fecha_registro) VALUES (4,3,'Hola cara de bola ','diagnóstico secundarios 2 ','observaciones prueba nueva ',1,'2026-01-26 15:19:45');
INSERT INTO `diagnosticos_historial` (id_historial, id_atencion, diagnostico_principal, diagnosticos_secundarios, observaciones, id_medico, fecha_registro) VALUES (5,3,'Hola cara de bola ','diagnóstico wodjeo','observaciones prueba nueva ',1,'2026-01-31 21:04:15');
CREATE TABLE `examenes_gabinete` (
  `id_examen` int(11) NOT NULL AUTO_INCREMENT,
  `id_atencion` int(11) NOT NULL,
  `id_medico` int(11) NOT NULL,
  `fecha` datetime DEFAULT current_timestamp(),
  `observaciones` text DEFAULT NULL,
  PRIMARY KEY (`id_examen`),
  KEY `id_atencion` (`id_atencion`),
  KEY `id_medico` (`id_medico`),
  CONSTRAINT `examenes_gabinete_ibfk_1` FOREIGN KEY (`id_atencion`) REFERENCES `atencion` (`id_atencion`),
  CONSTRAINT `examenes_gabinete_ibfk_2` FOREIGN KEY (`id_medico`) REFERENCES `users` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=7 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

INSERT INTO `examenes_gabinete` (id_examen, id_atencion, id_medico, fecha, observaciones) VALUES (2,3,1,'2026-01-25 21:26:12','');
INSERT INTO `examenes_gabinete` (id_examen, id_atencion, id_medico, fecha, observaciones) VALUES (3,3,1,'2026-01-25 21:26:25','');
INSERT INTO `examenes_gabinete` (id_examen, id_atencion, id_medico, fecha, observaciones) VALUES (4,3,1,'2026-01-25 21:28:24','');
INSERT INTO `examenes_gabinete` (id_examen, id_atencion, id_medico, fecha, observaciones) VALUES (5,3,1,'2026-01-25 22:01:43','');
INSERT INTO `examenes_gabinete` (id_examen, id_atencion, id_medico, fecha, observaciones) VALUES (6,3,1,'2026-01-31 21:04:40','');
CREATE TABLE `examenes_gabinete_det` (
  `id_det` int(11) NOT NULL AUTO_INCREMENT,
  `id_examen` int(11) NOT NULL,
  `nombre_examen` varchar(150) NOT NULL,
  `estado` enum('PENDIENTE','REALIZADO','CANCELADO') DEFAULT 'PENDIENTE',
  `fecha_realizado` datetime DEFAULT NULL,
  `archivo_resultado` varchar(255) DEFAULT NULL,
  `observaciones` text DEFAULT NULL,
  PRIMARY KEY (`id_det`),
  KEY `id_examen` (`id_examen`),
  CONSTRAINT `examenes_gabinete_det_ibfk_1` FOREIGN KEY (`id_examen`) REFERENCES `examenes_gabinete` (`id_examen`)
) ENGINE=InnoDB AUTO_INCREMENT=38 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

INSERT INTO `examenes_gabinete_det` (id_det, id_examen, nombre_examen, estado, fecha_realizado, archivo_resultado, observaciones) VALUES (25,2,'Fondo de ojo','PENDIENTE',NULL,NULL,NULL);
INSERT INTO `examenes_gabinete_det` (id_det, id_examen, nombre_examen, estado, fecha_realizado, archivo_resultado, observaciones) VALUES (26,2,'Retinografía','PENDIENTE',NULL,NULL,NULL);
INSERT INTO `examenes_gabinete_det` (id_det, id_examen, nombre_examen, estado, fecha_realizado, archivo_resultado, observaciones) VALUES (27,3,'Campimetría','PENDIENTE',NULL,NULL,NULL);
INSERT INTO `examenes_gabinete_det` (id_det, id_examen, nombre_examen, estado, fecha_realizado, archivo_resultado, observaciones) VALUES (28,3,'Fondo de ojo','PENDIENTE',NULL,NULL,NULL);
INSERT INTO `examenes_gabinete_det` (id_det, id_examen, nombre_examen, estado, fecha_realizado, archivo_resultado, observaciones) VALUES (29,3,'Queratometría','PENDIENTE',NULL,NULL,NULL);
INSERT INTO `examenes_gabinete_det` (id_det, id_examen, nombre_examen, estado, fecha_realizado, archivo_resultado, observaciones) VALUES (30,3,'Refracción','PENDIENTE',NULL,NULL,NULL);
INSERT INTO `examenes_gabinete_det` (id_det, id_examen, nombre_examen, estado, fecha_realizado, archivo_resultado, observaciones) VALUES (31,4,'Fondo de ojo','PENDIENTE',NULL,NULL,NULL);
INSERT INTO `examenes_gabinete_det` (id_det, id_examen, nombre_examen, estado, fecha_realizado, archivo_resultado, observaciones) VALUES (32,4,'Retinografía','PENDIENTE',NULL,NULL,NULL);
INSERT INTO `examenes_gabinete_det` (id_det, id_examen, nombre_examen, estado, fecha_realizado, archivo_resultado, observaciones) VALUES (33,5,'Fondo de ojo','PENDIENTE',NULL,NULL,NULL);
INSERT INTO `examenes_gabinete_det` (id_det, id_examen, nombre_examen, estado, fecha_realizado, archivo_resultado, observaciones) VALUES (34,5,'Refracción','PENDIENTE',NULL,NULL,NULL);
INSERT INTO `examenes_gabinete_det` (id_det, id_examen, nombre_examen, estado, fecha_realizado, archivo_resultado, observaciones) VALUES (35,6,'Campimetría','REALIZADO','2026-02-01 00:39:26','Banner_1.jpg','');
INSERT INTO `examenes_gabinete_det` (id_det, id_examen, nombre_examen, estado, fecha_realizado, archivo_resultado, observaciones) VALUES (36,6,'OCT de mácula','REALIZADO','2026-02-01 00:39:26','Banner_1.jpg','');
INSERT INTO `examenes_gabinete_det` (id_det, id_examen, nombre_examen, estado, fecha_realizado, archivo_resultado, observaciones) VALUES (37,6,'Topografía corneal','REALIZADO','2026-02-01 00:39:26','Banner_1.jpg','');
CREATE TABLE `examenes_laboratorio` (
  `id_examen` int(11) NOT NULL AUTO_INCREMENT,
  `id_atencion` int(11) NOT NULL,
  `id_medico` int(11) NOT NULL,
  `fecha` datetime DEFAULT current_timestamp(),
  `observaciones` text DEFAULT NULL,
  `estado` enum('pendiente','realizado') DEFAULT 'pendiente',
  `fecha_realizado` datetime DEFAULT NULL,
  `archivo_resultado` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`id_examen`),
  KEY `id_atencion` (`id_atencion`),
  KEY `id_medico` (`id_medico`),
  CONSTRAINT `examenes_laboratorio_ibfk_1` FOREIGN KEY (`id_atencion`) REFERENCES `atencion` (`id_atencion`),
  CONSTRAINT `examenes_laboratorio_ibfk_2` FOREIGN KEY (`id_medico`) REFERENCES `users` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

INSERT INTO `examenes_laboratorio` (id_examen, id_atencion, id_medico, fecha, observaciones, estado, fecha_realizado, archivo_resultado) VALUES (1,3,1,'2026-01-25 21:43:42','','pendiente',NULL,NULL);
INSERT INTO `examenes_laboratorio` (id_examen, id_atencion, id_medico, fecha, observaciones, estado, fecha_realizado, archivo_resultado) VALUES (2,3,1,'2026-01-25 21:57:38','','pendiente',NULL,NULL);
INSERT INTO `examenes_laboratorio` (id_examen, id_atencion, id_medico, fecha, observaciones, estado, fecha_realizado, archivo_resultado) VALUES (3,3,1,'2026-01-25 22:01:19','prueba','realizado','2026-02-02 01:15:50','Banner_1.jpg');
INSERT INTO `examenes_laboratorio` (id_examen, id_atencion, id_medico, fecha, observaciones, estado, fecha_realizado, archivo_resultado) VALUES (4,3,1,'2026-01-31 21:04:34','','realizado','2026-02-01 00:39:10','LISTA_DESAYUNOS_TERCERO_B.pdf');
CREATE TABLE `examenes_laboratorio_det` (
  `id_det` int(11) NOT NULL AUTO_INCREMENT,
  `id_examen` int(11) NOT NULL,
  `id_catalogo` int(11) NOT NULL,
  PRIMARY KEY (`id_det`),
  KEY `id_examen` (`id_examen`),
  KEY `id_catalogo` (`id_catalogo`),
  CONSTRAINT `examenes_laboratorio_det_ibfk_1` FOREIGN KEY (`id_examen`) REFERENCES `examenes_laboratorio` (`id_examen`),
  CONSTRAINT `examenes_laboratorio_det_ibfk_2` FOREIGN KEY (`id_catalogo`) REFERENCES `catalogo_examenes_laboratorio` (`id_catalogo`)
) ENGINE=InnoDB AUTO_INCREMENT=9 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

INSERT INTO `examenes_laboratorio_det` (id_det, id_examen, id_catalogo) VALUES (1,1,7);
INSERT INTO `examenes_laboratorio_det` (id_det, id_examen, id_catalogo) VALUES (2,1,2);
INSERT INTO `examenes_laboratorio_det` (id_det, id_examen, id_catalogo) VALUES (3,2,9);
INSERT INTO `examenes_laboratorio_det` (id_det, id_examen, id_catalogo) VALUES (4,2,8);
INSERT INTO `examenes_laboratorio_det` (id_det, id_examen, id_catalogo) VALUES (5,3,7);
INSERT INTO `examenes_laboratorio_det` (id_det, id_examen, id_catalogo) VALUES (6,3,2);
INSERT INTO `examenes_laboratorio_det` (id_det, id_examen, id_catalogo) VALUES (7,4,9);
INSERT INTO `examenes_laboratorio_det` (id_det, id_examen, id_catalogo) VALUES (8,4,10);
CREATE TABLE `expedientes` (
  `id_expediente` int(11) NOT NULL AUTO_INCREMENT,
  `id_exp` int(11) NOT NULL,
  `id_atencion` int(11) NOT NULL,
  `fecha_alta` datetime NOT NULL,
  `usuario_alta` int(11) DEFAULT NULL,
  PRIMARY KEY (`id_expediente`),
  KEY `id_exp` (`id_exp`),
  KEY `id_atencion` (`id_atencion`),
  CONSTRAINT `expedientes_ibfk_1` FOREIGN KEY (`id_exp`) REFERENCES `pacientes` (`Id_exp`),
  CONSTRAINT `expedientes_ibfk_2` FOREIGN KEY (`id_atencion`) REFERENCES `atencion` (`id_atencion`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

INSERT INTO `expedientes` (id_expediente, id_exp, id_atencion, fecha_alta, usuario_alta) VALUES (1,12,1,'2026-01-19 13:28:37',1);
CREATE TABLE `familiares` (
  `id_familiar` int(11) NOT NULL AUTO_INCREMENT,
  `Id_exp` int(11) DEFAULT NULL,
  `nombre` varchar(100) NOT NULL,
  `parentesco` varchar(50) DEFAULT NULL,
  `telefono` varchar(20) DEFAULT NULL,
  PRIMARY KEY (`id_familiar`),
  KEY `Id_exp` (`Id_exp`),
  CONSTRAINT `familiares_ibfk_1` FOREIGN KEY (`Id_exp`) REFERENCES `pacientes` (`Id_exp`)
) ENGINE=InnoDB AUTO_INCREMENT=7 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

INSERT INTO `familiares` (id_familiar, Id_exp, nombre, parentesco, telefono) VALUES (4,12,'Alejandro Lara Uribe','Padre','7226086837');
INSERT INTO `familiares` (id_familiar, Id_exp, nombre, parentesco, telefono) VALUES (5,14,'Alejandro Lara Uribe','Padre','7226086837');
INSERT INTO `familiares` (id_familiar, Id_exp, nombre, parentesco, telefono) VALUES (6,15,'Alejandro Lara Uribe','Padre','7226086837');
CREATE TABLE `historia_clinica` (
  `id_hc` int(11) NOT NULL AUTO_INCREMENT,
  `id_exp` int(11) NOT NULL,
  `motivo_consulta` text DEFAULT NULL,
  `sintomatologia` text DEFAULT NULL,
  `sintomatologia_otros` text DEFAULT NULL,
  `heredo` text DEFAULT NULL,
  `heredo_otros` text DEFAULT NULL,
  `nopat` text DEFAULT NULL,
  `nopat_otros` text DEFAULT NULL,
  `pat_enfermedades` text DEFAULT NULL,
  `pat_medicamentos` text DEFAULT NULL,
  `pat_alergias` text DEFAULT NULL,
  `pat_oculares` text DEFAULT NULL,
  `pat_cirugias` text DEFAULT NULL,
  `fecha_registro` datetime DEFAULT current_timestamp(),
  PRIMARY KEY (`id_hc`),
  KEY `id_exp` (`id_exp`),
  CONSTRAINT `historia_clinica_ibfk_1` FOREIGN KEY (`id_exp`) REFERENCES `pacientes` (`Id_exp`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

INSERT INTO `historia_clinica` (id_hc, id_exp, motivo_consulta, sintomatologia, sintomatologia_otros, heredo, heredo_otros, nopat, nopat_otros, pat_enfermedades, pat_medicamentos, pat_alergias, pat_oculares, pat_cirugias, fecha_registro) VALUES (1,15,'Prueba','Lagrimeo','wjkdne','Diabetes','ioende','Sedentarismo','wjkdneo','no','wdne','wjdn4e','wde4io','widn4','2026-01-25 20:27:33');
INSERT INTO `historia_clinica` (id_hc, id_exp, motivo_consulta, sintomatologia, sintomatologia_otros, heredo, heredo_otros, nopat, nopat_otros, pat_enfermedades, pat_medicamentos, pat_alergias, pat_oculares, pat_cirugias, fecha_registro) VALUES (2,15,'sidne3','','wkjdne','','','Alcohol','','','wdne','no','','','2026-01-25 20:29:53');
INSERT INTO `historia_clinica` (id_hc, id_exp, motivo_consulta, sintomatologia, sintomatologia_otros, heredo, heredo_otros, nopat, nopat_otros, pat_enfermedades, pat_medicamentos, pat_alergias, pat_oculares, pat_cirugias, fecha_registro) VALUES (3,15,'wjsne','Ojo rojo,Fotofobia','wdje','','','','','','','','','','2026-01-25 21:13:14');
INSERT INTO `historia_clinica` (id_hc, id_exp, motivo_consulta, sintomatologia, sintomatologia_otros, heredo, heredo_otros, nopat, nopat_otros, pat_enfermedades, pat_medicamentos, pat_alergias, pat_oculares, pat_cirugias, fecha_registro) VALUES (4,15,'wwkdnek','Visión borrosa,Fotofobia','wdnlke','','','','','','','','','','2026-01-31 21:03:37');
CREATE TABLE `item` (
  `item_id` int(11) NOT NULL DEFAULT 0,
  `item_code` varchar(35) CHARACTER SET utf8 COLLATE utf8_general_ci NOT NULL,
  `item_name` varchar(100) CHARACTER SET utf8 COLLATE utf8_general_ci NOT NULL,
  `item_grams` varchar(250) CHARACTER SET utf8 COLLATE utf8_general_ci NOT NULL,
  `item_cost` double(10,2) NOT NULL,
  `item_price` double(10,2) NOT NULL,
  `item_price2` double(10,2) NOT NULL,
  `item_price3` double(10,2) NOT NULL,
  `item_price4` double(10,2) NOT NULL,
  `item_type_id` int(11) NOT NULL,
  `controlado` varchar(2) CHARACTER SET utf8 COLLATE utf8_general_ci NOT NULL,
  `item_min` int(10) NOT NULL DEFAULT 0,
  `item_max` int(10) NOT NULL DEFAULT 0,
  `tip_insumo` varchar(350) CHARACTER SET utf8 COLLATE utf8_general_ci NOT NULL,
  `item_brand` varchar(350) CHARACTER SET utf8 COLLATE utf8_general_ci NOT NULL,
  `grupo` varchar(350) CHARACTER SET utf8 COLLATE utf8_general_ci NOT NULL,
  `codigo_sat` varchar(50) CHARACTER SET utf8 COLLATE utf8_general_ci NOT NULL,
  `c_cveuni` varchar(100) CHARACTER SET utf8 COLLATE utf8_general_ci NOT NULL,
  `c_nombre` varchar(100) CHARACTER SET utf8 COLLATE utf8_general_ci NOT NULL,
  `activo` varchar(2) CHARACTER SET utf8 COLLATE utf8_general_ci NOT NULL DEFAULT 'SI'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE `notas_medicas` (
  `id_nota` int(11) NOT NULL AUTO_INCREMENT,
  `id_atencion` int(11) NOT NULL,
  `subjetivo` text DEFAULT NULL,
  `objetivo` text DEFAULT NULL,
  `analisis` text DEFAULT NULL,
  `plan` text DEFAULT NULL,
  `fecha_registro` timestamp NOT NULL DEFAULT current_timestamp(),
  `id_medico` int(11) DEFAULT NULL,
  PRIMARY KEY (`id_nota`),
  KEY `id_atencion` (`id_atencion`),
  CONSTRAINT `notas_medicas_ibfk_1` FOREIGN KEY (`id_atencion`) REFERENCES `atencion` (`id_atencion`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

INSERT INTO `notas_medicas` (id_nota, id_atencion, subjetivo, objetivo, analisis, plan, fecha_registro, id_medico) VALUES (1,3,'wdne','wjkdne','wkldnme','wklndel','2026-01-26 14:53:29',1);
INSERT INTO `notas_medicas` (id_nota, id_atencion, subjetivo, objetivo, analisis, plan, fecha_registro, id_medico) VALUES (2,3,'Hola ','objetivo ','análisis ','plan ','2026-01-26 15:16:35',1);
INSERT INTO `notas_medicas` (id_nota, id_atencion, subjetivo, objetivo, analisis, plan, fecha_registro, id_medico) VALUES (3,3,'wkldme','wkldnwl','análisis ','wkldnw','2026-01-31 21:04:07',1);
CREATE TABLE `pacientes` (
  `Id_exp` int(11) NOT NULL AUTO_INCREMENT,
  `papell` varchar(50) DEFAULT NULL,
  `sapell` varchar(50) DEFAULT NULL,
  `nom_pac` varchar(50) DEFAULT NULL,
  `fecnac` date DEFAULT NULL,
  `tel` varchar(20) DEFAULT NULL,
  `curp` char(18) DEFAULT NULL,
  PRIMARY KEY (`Id_exp`),
  UNIQUE KEY `curp` (`curp`)
) ENGINE=InnoDB AUTO_INCREMENT=16 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

INSERT INTO `pacientes` (Id_exp, papell, sapell, nom_pac, fecnac, tel, curp) VALUES (12,'LARA','URIBE','JOEL ALEJANDRO','2004-01-02','7226086837','LARJ040102HMCRDLA1');
INSERT INTO `pacientes` (Id_exp, papell, sapell, nom_pac, fecnac, tel, curp) VALUES (14,'LARA','RODRIGUEZ','JOEL ALEJANDRO','2000-02-02','7226086837','LARJ040102HMCRDLA8');
INSERT INTO `pacientes` (Id_exp, papell, sapell, nom_pac, fecnac, tel, curp) VALUES (15,'LARA','RODRIGUEZ','JOEL ALEJANDRO','2000-02-02','7226086837','LURA031024MMCGYRA2');
CREATE TABLE `pagos_paciente` (
  `id_pago` int(11) NOT NULL AUTO_INCREMENT,
  `id_atencion` int(11) NOT NULL,
  `fecha` datetime NOT NULL,
  `forma_pago` varchar(50) DEFAULT NULL,
  `detalle` varchar(100) DEFAULT NULL,
  `monto` decimal(10,2) DEFAULT NULL,
  PRIMARY KEY (`id_pago`),
  KEY `id_atencion` (`id_atencion`),
  CONSTRAINT `pagos_paciente_ibfk_1` FOREIGN KEY (`id_atencion`) REFERENCES `atencion` (`id_atencion`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE `pago_serv` (
  `pago_id` int(10) NOT NULL DEFAULT 0,
  `id_pac` int(10) NOT NULL DEFAULT 0,
  `nombre` varchar(100) CHARACTER SET latin1 COLLATE latin1_swedish_ci NOT NULL DEFAULT '0',
  `id_serv` varchar(20) CHARACTER SET latin1 COLLATE latin1_swedish_ci NOT NULL DEFAULT '0',
  `servicio` varchar(255) CHARACTER SET latin1 COLLATE latin1_swedish_ci NOT NULL DEFAULT '0',
  `cantidad` int(10) NOT NULL DEFAULT 0,
  `precio` double(10,2) NOT NULL DEFAULT 0.00,
  `fecha` datetime NOT NULL,
  `activo` varchar(2) CHARACTER SET latin1 COLLATE latin1_swedish_ci NOT NULL DEFAULT 'SI',
  `usuario` int(10) NOT NULL,
  `tipo` varchar(50) CHARACTER SET utf8 COLLATE utf8_general_ci NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE `presupuesto` (
  `id_presupuesto` int(11) NOT NULL AUTO_INCREMENT,
  `fecha` timestamp NOT NULL DEFAULT current_timestamp(),
  `id_pac` int(11) NOT NULL,
  `nombre` varchar(100) NOT NULL,
  `id_serv` varchar(20) NOT NULL,
  `servicio` varchar(255) NOT NULL,
  `cantidad` int(11) NOT NULL,
  PRIMARY KEY (`id_presupuesto`)
) ENGINE=InnoDB AUTO_INCREMENT=7 DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;

INSERT INTO `presupuesto` (id_presupuesto, fecha, id_pac, nombre, id_serv, servicio, cantidad) VALUES (5,'2026-01-29 13:08:34',1,'PRUEBA','3','APLICACIÓN INTRAVITREA WETLIA (INCLUYE MEDICAMENTO)',1);
INSERT INTO `presupuesto` (id_presupuesto, fecha, id_pac, nombre, id_serv, servicio, cantidad) VALUES (6,'2026-01-29 13:08:42',1,'PRUEBA','8','APLICACIÓN DE TOXINA SIN SEDACION (QUIROFANO)',1);
CREATE TABLE `recetas` (
  `id_receta` int(11) NOT NULL AUTO_INCREMENT,
  `id_atencion` int(11) NOT NULL,
  `medicamento` varchar(255) DEFAULT NULL,
  `dosis` varchar(100) DEFAULT NULL,
  `frecuencia` varchar(100) DEFAULT NULL,
  `duracion` varchar(100) DEFAULT NULL,
  `indicaciones` text DEFAULT NULL,
  `fecha_registro` timestamp NOT NULL DEFAULT current_timestamp(),
  `id_medico` int(11) DEFAULT NULL,
  PRIMARY KEY (`id_receta`),
  KEY `id_atencion` (`id_atencion`),
  CONSTRAINT `recetas_ibfk_1` FOREIGN KEY (`id_atencion`) REFERENCES `atencion` (`id_atencion`)
) ENGINE=InnoDB AUTO_INCREMENT=8 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

INSERT INTO `recetas` (id_receta, id_atencion, medicamento, dosis, frecuencia, duracion, indicaciones, fecha_registro, id_medico) VALUES (1,3,'lknlk','22','1/5hs','3 dias','qksnlw','2026-01-26 22:23:52',1);
INSERT INTO `recetas` (id_receta, id_atencion, medicamento, dosis, frecuencia, duracion, indicaciones, fecha_registro, id_medico) VALUES (2,3,'timotol','.5%','cada 12 horas','3 dias','iawdnie','2026-01-29 13:03:06',1);
INSERT INTO `recetas` (id_receta, id_atencion, medicamento, dosis, frecuencia, duracion, indicaciones, fecha_registro, id_medico) VALUES (3,3,'2wede','.5%','cada 12 horas','3 dias','wlkdne','2026-01-29 13:03:06',1);
INSERT INTO `recetas` (id_receta, id_atencion, medicamento, dosis, frecuencia, duracion, indicaciones, fecha_registro, id_medico) VALUES (4,3,'medicamento ','dosis ','frecuencia ','duración ','indicaciones ','2026-01-30 15:10:59',1);
INSERT INTO `recetas` (id_receta, id_atencion, medicamento, dosis, frecuencia, duracion, indicaciones, fecha_registro, id_medico) VALUES (5,3,'medi ','dosis ','frecuencia ','duración ','indicaciones ','2026-01-30 17:01:24',1);
INSERT INTO `recetas` (id_receta, id_atencion, medicamento, dosis, frecuencia, duracion, indicaciones, fecha_registro, id_medico) VALUES (6,3,'timotol','5 mg ','cada dos horas ','tres días ','indicaciones ','2026-01-30 17:01:24',1);
INSERT INTO `recetas` (id_receta, id_atencion, medicamento, dosis, frecuencia, duracion, indicaciones, fecha_registro, id_medico) VALUES (7,3,'wkldneof','wkldnwe','wkldmw','wkldnlw','wkldnmew','2026-01-31 21:04:27',1);
CREATE TABLE `signos_vitales` (
  `id_signos` int(11) NOT NULL AUTO_INCREMENT,
  `id_atencion` int(11) NOT NULL,
  `ta` varchar(20) DEFAULT NULL,
  `fc` int(11) DEFAULT NULL,
  `fr` int(11) DEFAULT NULL,
  `temp` decimal(4,1) DEFAULT NULL,
  `spo2` int(11) DEFAULT NULL,
  `peso` decimal(5,2) DEFAULT NULL,
  `talla` decimal(5,2) DEFAULT NULL,
  `fecha_registro` timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id_signos`),
  KEY `id_atencion` (`id_atencion`),
  CONSTRAINT `signos_vitales_ibfk_1` FOREIGN KEY (`id_atencion`) REFERENCES `atencion` (`id_atencion`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

INSERT INTO `signos_vitales` (id_signos, id_atencion, ta, fc, fr, temp, spo2, peso, talla, fecha_registro) VALUES (1,3,'120/80',12,89,36.0,12,69.00,1.69,'2026-01-26 15:00:46');
INSERT INTO `signos_vitales` (id_signos, id_atencion, ta, fc, fr, temp, spo2, peso, talla, fecha_registro) VALUES (2,3,'120/80',12,12,36.0,98,69.00,1.69,'2026-01-26 15:02:49');
INSERT INTO `signos_vitales` (id_signos, id_atencion, ta, fc, fr, temp, spo2, peso, talla, fecha_registro) VALUES (3,3,'120/80',12,89,36.0,12,69.00,1.69,'2026-01-31 21:03:55');
CREATE TABLE `users` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `username` varchar(50) NOT NULL,
  `password` varchar(255) NOT NULL,
  `role` enum('admin','medico','enfermero','administrativo') NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `img_perfil` varchar(255) DEFAULT 'default_profile.jpg',
  `papell` varchar(100) DEFAULT 'Apellido',
  PRIMARY KEY (`id`),
  UNIQUE KEY `username` (`username`)
) ENGINE=InnoDB AUTO_INCREMENT=8 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

INSERT INTO `users` (id, username, password, role, created_at, img_perfil, papell) VALUES (1,'admin','$2b$12$m0ZkBHbNEqjZUKsQ4ma8wOg3JHVCncTnycsAEYQ7UlB2teD0zSfDG','admin','2026-01-17 14:16:16','default_profile.jpg','Lara');
INSERT INTO `users` (id, username, password, role, created_at, img_perfil, papell) VALUES (2,'dr_john_doe','$2b$12$m0ZkBHbNEqjZUKsQ4ma8wOg3JHVCncTnycsAEYQ7UlB2teD0zSfDG','medico','2026-01-18 11:20:59','default_profile.jpg','Doe');
INSERT INTO `users` (id, username, password, role, created_at, img_perfil, papell) VALUES (3,'dr_jane_smith','$2b$12$m0ZkBHbNEqjZUKsQ4ma8wOg3JHVCncTnycsAEYQ7UlB2teD0zSfDG','medico','2026-01-18 11:20:59','default_profile.jpg','Smith');
INSERT INTO `users` (id, username, password, role, created_at, img_perfil, papell) VALUES (4,'dr_michael_johnson','$2b$12$m0ZkBHbNEqjZUKsQ4ma8wOg3JHVCncTnycsAEYQ7UlB2teD0zSfDG','medico','2026-01-18 11:20:59','default_profile.jpg','Johnson');
INSERT INTO `users` (id, username, password, role, created_at, img_perfil, papell) VALUES (5,'dr_emily_davis','$2b$12$m0ZkBHbNEqjZUKsQ4ma8wOg3JHVCncTnycsAEYQ7UlB2teD0zSfDG','medico','2026-01-18 11:20:59','default_profile.jpg','Davis');
INSERT INTO `users` (id, username, password, role, created_at, img_perfil, papell) VALUES (6,'dr_robert_brown','$2b$12$m0ZkBHbNEqjZUKsQ4ma8wOg3JHVCncTnycsAEYQ7UlB2teD0zSfDG','medico','2026-01-18 11:20:59','default_profile.jpg','Brown');
INSERT INTO `users` (id, username, password, role, created_at, img_perfil, papell) VALUES (7,'JOEL','123456','admin','2026-02-02 01:35:06','default_profile.jpg','Apellido');

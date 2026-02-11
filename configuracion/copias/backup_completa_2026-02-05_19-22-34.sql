-- RESPALDO COMPLETA - 2026-02-05_19-22-34

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
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

INSERT INTO `atencion` (id_atencion, Id_exp, area, id_cama, motivo, especialidad, alergias, fecha_ing, status) VALUES (1,12,'Hospitalizado',1,'Consulta general','Medicina general','SI','2026-01-18 11:32:24','CERRADA');
INSERT INTO `atencion` (id_atencion, Id_exp, area, id_cama, motivo, especialidad, alergias, fecha_ing, status) VALUES (2,14,'Hospitalizado',2,'Urgencia','Medicina general','NO','2026-01-18 11:37:42','ABIERTA');
INSERT INTO `atencion` (id_atencion, Id_exp, area, id_cama, motivo, especialidad, alergias, fecha_ing, status) VALUES (3,15,'Urgencias',3,'Consulta general','Cardiología','NO','2026-01-18 11:39:16','CERRADA');
INSERT INTO `atencion` (id_atencion, Id_exp, area, id_cama, motivo, especialidad, alergias, fecha_ing, status) VALUES (4,16,'Hospitalizado',4,'Consulta general','Medicina general','NINGUNA','2026-02-04 19:10:31','ABIERTA');
CREATE TABLE `atencion_medicos` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `id_atencion` int(11) NOT NULL,
  `id_medico` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `id_atencion` (`id_atencion`),
  KEY `id_medico` (`id_medico`),
  CONSTRAINT `atencion_medicos_ibfk_1` FOREIGN KEY (`id_atencion`) REFERENCES `atencion` (`id_atencion`),
  CONSTRAINT `atencion_medicos_ibfk_2` FOREIGN KEY (`id_medico`) REFERENCES `users` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=15 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

INSERT INTO `atencion_medicos` (id, id_atencion, id_medico) VALUES (1,2,3);
INSERT INTO `atencion_medicos` (id, id_atencion, id_medico) VALUES (4,1,3);
INSERT INTO `atencion_medicos` (id, id_atencion, id_medico) VALUES (5,1,3);
INSERT INTO `atencion_medicos` (id, id_atencion, id_medico) VALUES (6,1,3);
INSERT INTO `atencion_medicos` (id, id_atencion, id_medico) VALUES (7,1,3);
INSERT INTO `atencion_medicos` (id, id_atencion, id_medico) VALUES (8,1,3);
INSERT INTO `atencion_medicos` (id, id_atencion, id_medico) VALUES (9,3,4);
INSERT INTO `atencion_medicos` (id, id_atencion, id_medico) VALUES (10,3,4);
INSERT INTO `atencion_medicos` (id, id_atencion, id_medico) VALUES (11,3,4);
INSERT INTO `atencion_medicos` (id, id_atencion, id_medico) VALUES (12,3,4);
INSERT INTO `atencion_medicos` (id, id_atencion, id_medico) VALUES (13,3,4);
INSERT INTO `atencion_medicos` (id, id_atencion, id_medico) VALUES (14,4,3);

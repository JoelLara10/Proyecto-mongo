-- Backup generado por la aplicación
SET FOREIGN_KEY_CHECKS=0;

DROP TABLE IF EXISTS `catalogo_examenes_laboratorio`;
CREATE TABLE `catalogo_examenes_laboratorio` (
  `id_catalogo` int(11) NOT NULL AUTO_INCREMENT,
  `nombre` varchar(150) NOT NULL,
  PRIMARY KEY (`id_catalogo`)
) ENGINE=InnoDB AUTO_INCREMENT=11 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

DROP TABLE IF EXISTS `diagnosticos`;
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

INSERT INTO `catalogo_examenes_laboratorio` (`id_catalogo`, `nombre`) VALUES (1, 'Biometría Hemática');
INSERT INTO `catalogo_examenes_laboratorio` (`id_catalogo`, `nombre`) VALUES (2, 'Química Sanguínea');
INSERT INTO `catalogo_examenes_laboratorio` (`id_catalogo`, `nombre`) VALUES (3, 'Glucosa');
INSERT INTO `catalogo_examenes_laboratorio` (`id_catalogo`, `nombre`) VALUES (4, 'Urea');
INSERT INTO `catalogo_examenes_laboratorio` (`id_catalogo`, `nombre`) VALUES (5, 'Creatinina');
INSERT INTO `catalogo_examenes_laboratorio` (`id_catalogo`, `nombre`) VALUES (6, 'Perfil Lipídico');
INSERT INTO `catalogo_examenes_laboratorio` (`id_catalogo`, `nombre`) VALUES (7, 'Examen General de Orina');
INSERT INTO `catalogo_examenes_laboratorio` (`id_catalogo`, `nombre`) VALUES (8, 'Tiempo de Protrombina');
INSERT INTO `catalogo_examenes_laboratorio` (`id_catalogo`, `nombre`) VALUES (9, 'Grupo y RH');
INSERT INTO `catalogo_examenes_laboratorio` (`id_catalogo`, `nombre`) VALUES (10, 'Hemoglobina Glicosilada');

INSERT INTO `diagnosticos` (`id_diagnostico`, `id_atencion`, `diagnostico_principal`, `diagnosticos_secundarios`, `observaciones`, `fecha_registro`) VALUES (1, 3, 'Hola cara de bola ', 'diagnóstico wodjeo', 'observaciones prueba nueva ', '2026-01-26 13:57:25');

SET FOREIGN_KEY_CHECKS=1;

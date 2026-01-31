/*
SQLyog Ultimate v11.11 (64 bit)
MySQL - 5.5.5-10.4.32-MariaDB : Database - ineo_db
*********************************************************************
*/


/*!40101 SET NAMES utf8 */;

/*!40101 SET SQL_MODE=''*/;

/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;
CREATE DATABASE /*!32312 IF NOT EXISTS*/`ineo_db` /*!40100 DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci */;

USE `ineo_db`;

/*Table structure for table `atencion` */

DROP TABLE IF EXISTS `atencion`;

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

/*Data for the table `atencion` */

LOCK TABLES `atencion` WRITE;

insert  into `atencion`(`id_atencion`,`Id_exp`,`area`,`id_cama`,`motivo`,`especialidad`,`alergias`,`fecha_ing`,`status`) values (1,12,'Hospitalizado',1,'Consulta general','Medicina general','SI','2026-01-18 11:32:24','CERRADA'),(2,14,'Hospitalizado',2,'Urgencia','Medicina general','NO','2026-01-18 11:37:42','ABIERTA'),(3,15,'Urgencias',3,'Consulta general','Cardiología','NO','2026-01-18 11:39:16','ABIERTA');

UNLOCK TABLES;

/*Table structure for table `atencion_medicos` */

DROP TABLE IF EXISTS `atencion_medicos`;

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

/*Data for the table `atencion_medicos` */

LOCK TABLES `atencion_medicos` WRITE;

insert  into `atencion_medicos`(`id`,`id_atencion`,`id_medico`) values (1,2,3),(2,3,4),(4,1,3),(5,1,3),(6,1,3),(7,1,3),(8,1,3);

UNLOCK TABLES;

/*Table structure for table `camas` */

DROP TABLE IF EXISTS `camas`;

CREATE TABLE `camas` (
  `id_cama` int(11) NOT NULL AUTO_INCREMENT,
  `area` enum('Hospitalizado','Urgencias') NOT NULL,
  `numero` varchar(10) NOT NULL,
  `ocupada` tinyint(1) DEFAULT 0,
  PRIMARY KEY (`id_cama`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

/*Data for the table `camas` */

LOCK TABLES `camas` WRITE;

insert  into `camas`(`id_cama`,`area`,`numero`,`ocupada`) values (1,'Hospitalizado','H-101',1),(2,'Hospitalizado','H-102',1),(3,'Urgencias','U-01',1),(4,'Urgencias','U-02',0);

UNLOCK TABLES;

/*Table structure for table `cuenta_paciente` */

DROP TABLE IF EXISTS `cuenta_paciente`;

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

/*Data for the table `cuenta_paciente` */

LOCK TABLES `cuenta_paciente` WRITE;

UNLOCK TABLES;

/*Table structure for table `expedientes` */

DROP TABLE IF EXISTS `expedientes`;

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

/*Data for the table `expedientes` */

LOCK TABLES `expedientes` WRITE;

insert  into `expedientes`(`id_expediente`,`id_exp`,`id_atencion`,`fecha_alta`,`usuario_alta`) values (1,12,1,'2026-01-19 13:28:37',1);

UNLOCK TABLES;

/*Table structure for table `familiares` */

DROP TABLE IF EXISTS `familiares`;

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

/*Data for the table `familiares` */

LOCK TABLES `familiares` WRITE;

insert  into `familiares`(`id_familiar`,`Id_exp`,`nombre`,`parentesco`,`telefono`) values (4,12,'Alejandro Lara Uribe','Padre','7226086837'),(5,14,'Alejandro Lara Uribe','Padre','7226086837'),(6,15,'Alejandro Lara Uribe','Padre','7226086837');

UNLOCK TABLES;

/*Table structure for table `pacientes` */

DROP TABLE IF EXISTS `pacientes`;

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

/*Data for the table `pacientes` */

LOCK TABLES `pacientes` WRITE;

insert  into `pacientes`(`Id_exp`,`papell`,`sapell`,`nom_pac`,`fecnac`,`tel`,`curp`) values (12,'LARA','URIBE','JOEL ALEJANDRO','2004-01-02','7226086837','LARJ040102HMCRDLA1'),(14,'LARA','RODRIGUEZ','JOEL ALEJANDRO','2000-02-02','7226086837','LARJ040102HMCRDLA8'),(15,'LARA','RODRIGUEZ','JOEL ALEJANDRO','2000-02-02','7226086837','LURA031024MMCGYRA2');

UNLOCK TABLES;

/*Table structure for table `pagos_paciente` */

DROP TABLE IF EXISTS `pagos_paciente`;

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

/*Data for the table `pagos_paciente` */

LOCK TABLES `pagos_paciente` WRITE;

UNLOCK TABLES;

/*Table structure for table `users` */

DROP TABLE IF EXISTS `users`;

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
) ENGINE=InnoDB AUTO_INCREMENT=7 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

/*Data for the table `users` */

LOCK TABLES `users` WRITE;

insert  into `users`(`id`,`username`,`password`,`role`,`created_at`,`img_perfil`,`papell`) values (1,'admin','$2b$12$m0ZkBHbNEqjZUKsQ4ma8wOg3JHVCncTnycsAEYQ7UlB2teD0zSfDG','admin','2026-01-17 14:16:16','default_profile.jpg','Apellido'),(2,'dr_john_doe','$2b$12$m0ZkBHbNEqjZUKsQ4ma8wOg3JHVCncTnycsAEYQ7UlB2teD0zSfDG','medico','2026-01-18 11:20:59','default_profile.jpg','Doe'),(3,'dr_jane_smith','$2b$12$m0ZkBHbNEqjZUKsQ4ma8wOg3JHVCncTnycsAEYQ7UlB2teD0zSfDG','medico','2026-01-18 11:20:59','default_profile.jpg','Smith'),(4,'dr_michael_johnson','$2b$12$m0ZkBHbNEqjZUKsQ4ma8wOg3JHVCncTnycsAEYQ7UlB2teD0zSfDG','medico','2026-01-18 11:20:59','default_profile.jpg','Johnson'),(5,'dr_emily_davis','$2b$12$m0ZkBHbNEqjZUKsQ4ma8wOg3JHVCncTnycsAEYQ7UlB2teD0zSfDG','medico','2026-01-18 11:20:59','default_profile.jpg','Davis'),(6,'dr_robert_brown','$2b$12$m0ZkBHbNEqjZUKsQ4ma8wOg3JHVCncTnycsAEYQ7UlB2teD0zSfDG','medico','2026-01-18 11:20:59','default_profile.jpg','Brown');

UNLOCK TABLES;


/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

# Despliegue de microservicios Spring Boot

## Construccion de la imagen

Un microservicio Spring Boot se empaqueta como un JAR ejecutable y se lleva a una imagen de contenedor. La recomendacion es usar una construccion en dos etapas: una primera etapa con el JDK completo que compila el proyecto, y una segunda etapa que parte de una imagen JRE minima y solo copia el artefacto resultante. Esto reduce el tamano final de la imagen y baja la superficie de ataque, porque el compilador y las herramientas de build no viajan a produccion.

Spring Boot tambien permite descomponer el JAR en capas (layered jars): dependencias, dependencias snapshot, recursos de la aplicacion y clases propias. Como las dependencias cambian mucho menos seguido que el codigo propio, separarlas en capas distintas hace que el cache de capas del contenedor se reutilice y las construcciones posteriores sean mucho mas rapidas.

## Configuracion externalizada

La configuracion nunca se hornea dentro de la imagen. La misma imagen debe poder correr en desarrollo, en staging y en produccion cambiando unicamente variables de entorno. Spring Boot resuelve la configuracion con un orden de precedencia donde las variables de entorno pisan a los archivos application.yml empaquetados.

Los perfiles de Spring (spring.profiles.active) permiten tener bloques de configuracion por ambiente dentro del mismo archivo. Los datos sensibles como contrasenas de base de datos o claves de API se inyectan como secretos del orquestador, nunca como texto plano en el repositorio ni en la imagen.

## Endpoints de Actuator y sondas de salud

Spring Boot Actuator expone endpoints operativos bajo la ruta /actuator. Los dos mas importantes para un despliegue son /actuator/health/liveness y /actuator/health/readiness.

La sonda de liveness responde si el proceso esta vivo. Si falla, el orquestador reinicia el contenedor, porque asume que quedo en un estado irrecuperable. La sonda de readiness responde si el servicio esta en condiciones de recibir trafico. Si falla, el orquestador deja de enviarle pedidos pero no lo reinicia. Confundir ambas es un error frecuente: poner una dependencia externa como base de datos dentro de la sonda de liveness provoca reinicios en cadena cuando esa dependencia se degrada momentaneamente.

## Apagado ordenado

Un microservicio que recibe la senal de terminacion no debe cortar de golpe. Spring Boot soporta apagado ordenado mediante server.shutdown=graceful, que deja de aceptar conexiones nuevas y da un plazo para terminar las que estan en curso. Ese plazo se configura con spring.lifecycle.timeout-per-shutdown-phase. Sin apagado ordenado, cada despliegue genera errores visibles para el usuario final.

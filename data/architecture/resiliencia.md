Patrones de resiliencia en microservicios

Por que hace falta

En un monolito una llamada entre modulos es una llamada de metodo: o funciona o lanza una
excepcion, y tarda microsegundos. En una arquitectura de microservicios esa misma llamada
cruza la red, y la red introduce modos de falla que antes no existian: el destino puede estar
caido, puede estar lento, o la respuesta puede perderse. Un servicio que no contempla esos
modos de falla propaga la degradacion hacia arriba y termina arrastrando a todo el sistema.

Timeouts

Un timeout es el limite de tiempo que se esta dispuesto a esperar por una respuesta. Es el
patron mas basico y el mas olvidado. Sin timeout explicito, una llamada a un servicio lento
mantiene ocupado el hilo que la ejecuta por tiempo indefinido. Con suficientes llamadas en ese
estado el pool de hilos se agota y el servicio deja de responder, aunque su propio codigo este
perfectamente sano.

El valor del timeout se elige a partir de los percentiles de latencia observados del servicio
destino, no de un numero redondo arbitrario. Un timeout mas corto que el percentil 99 normal
va a cortar llamadas que hubieran funcionado.

Reintentos

Un reintento vuelve a enviar el pedido cuando fallo. Solo tiene sentido para fallas
transitorias, como una perdida de conexion momentanea, y solo sobre operaciones que se pueden
repetir sin efectos duplicados.

El reintento inmediato es contraproducente: si el destino esta saturado, reintentar al instante
suma carga justo cuando menos la tolera. La estrategia correcta es espera exponencial con
jitter, donde cada intento espera mas que el anterior y se le agrega una componente aleatoria
para que instancias distintas no reintenten todas en el mismo instante. La cantidad de intentos
se mantiene baja, tipicamente tres.

Circuit breaker

El circuit breaker, o cortacircuitos, corta las llamadas a un destino que viene fallando de
forma sostenida. Tiene tres estados. En estado cerrado las llamadas pasan normalmente y se
lleva la cuenta de fallas. Cuando la tasa de fallas supera un umbral en una ventana de
observacion, pasa a estado abierto: las llamadas fallan de inmediato sin llegar a salir a la
red. Despues de un tiempo de espera pasa a semiabierto y deja pasar unas pocas llamadas de
prueba; si tienen exito vuelve a cerrado, y si fallan vuelve a abierto.

El valor del patron es doble: el llamador deja de gastar hilos y tiempo en llamadas condenadas
al fracaso, y el destino recibe un respiro que le permite recuperarse en vez de seguir
recibiendo carga mientras esta caido.

Bulkhead

El bulkhead, o mamparo, toma el nombre de los compartimientos estancos de un barco: si uno se
inunda, los demas siguen secos. Aplicado a un servicio, significa asignar pools de recursos
separados por dependencia en vez de un pool unico compartido. Si el servicio A y el servicio B
comparten el mismo pool de hilos y A se pone lento, agota el pool y las llamadas a B tambien
se caen, aunque B este perfecto. Con pools separados la degradacion de A queda contenida.

Degradacion controlada

Cuando una dependencia no responde, no siempre corresponde devolver un error. Muchas veces hay
una respuesta parcial aceptable: un valor por defecto, un dato de cache aunque este vencido, o
una version reducida de la funcionalidad. Esto se conoce como fallback y es lo que diferencia
un sistema que se degrada de uno que se cae.

Implementacion en Spring Boot

En el ecosistema Spring la biblioteca de referencia es Resilience4j, que provee timeouts,
reintentos, circuit breaker, bulkhead y limitadores de tasa como componentes configurables y
combinables. Reemplazo a Hystrix, que quedo sin mantenimiento activo.


Rate limiting

Un limitador de tasa restringe cuantas llamadas por segundo acepta un servicio. Protege al que recibe, a diferencia del circuit breaker que protege al que llama.

Comunicacion asincronica entre microservicios

Sincronico contra asincronico

En la comunicacion sincronica el servicio que llama queda esperando la respuesta antes de
continuar. Es simple de razonar, pero acopla la disponibilidad de los dos servicios: si el
destino esta caido, el origen tambien falla. Y acopla la latencia: el tiempo de respuesta del
origen es la suma de los tiempos de toda la cadena que invoca.

En la comunicacion asincronica el origen deposita un mensaje en un intermediario y sigue
trabajando. El destino lo consume cuando puede. Si el destino esta caido, los mensajes se
acumulan y se procesan cuando vuelve. Esto desacopla disponibilidad y latencia, a cambio de
perder la respuesta inmediata y de tener que convivir con consistencia eventual.

Colas contra eventos

Son dos modelos distintos y se eligen por intencion, no por herramienta.

Una cola de trabajo transporta un comando dirigido a un consumidor: hay un emisor que quiere
que algo se haga, y cada mensaje lo procesa un solo consumidor. El emisor sabe que espera que
ocurra. RabbitMQ es representativo de este modelo.

Un flujo de eventos transporta hechos ya ocurridos, en pasado, y cualquier cantidad de
consumidores puede leerlos de forma independiente. El emisor publica que algo paso y no sabe
ni le importa quien escucha. Agregar un consumidor nuevo no requiere tocar al emisor. Kafka es
representativo de este modelo.

Garantias de entrega

Existen tres niveles. Como mucho una vez (at-most-once) puede perder mensajes y casi nunca es
aceptable. Al menos una vez (at-least-once) garantiza que el mensaje llega, pero puede llegar
duplicado. Exactamente una vez (exactly-once) es muy costoso y en sistemas distribuidos reales
suele ser una ilusion parcial.

Lo que se usa en la practica es al menos una vez. La consecuencia directa es que el consumidor
tiene que estar preparado para recibir el mismo mensaje mas de una vez.

Idempotencia

Una operacion es idempotente cuando ejecutarla varias veces produce el mismo resultado que
ejecutarla una sola vez. Es la propiedad que vuelve seguros tanto los reintentos como la
entrega al menos una vez.

La forma habitual de lograrla es que cada mensaje lleve un identificador unico y que el
consumidor registre los identificadores ya procesados, descartando los repetidos. Tambien
sirve disenar las operaciones para que sean naturalmente idempotentes: fijar un estado a un
valor concreto es idempotente, incrementar un contador no lo es.

Orden de los mensajes

El orden global entre todos los mensajes no esta garantizado y normalmente no hace falta. Lo
que si suele hacer falta es orden dentro de una misma entidad. En Kafka esto se resuelve con
la clave de particion: todos los mensajes que comparten clave caen en la misma particion y se
consumen en orden. Usar como clave el identificador de la entidad, por ejemplo el numero de
pedido, garantiza el orden de los eventos de ese pedido sin sacrificar paralelismo entre
pedidos distintos.

Mensajes que fallan siempre

Un mensaje que falla de forma sistematica y se reintenta sin limite bloquea el consumo del
resto. La solucion es un limite de reintentos y, superado ese limite, mover el mensaje a una
cola de mensajes muertos (dead letter queue) para analizarlo aparte sin frenar el flujo
principal.

Contratos y evolucion

El formato del mensaje es un contrato entre servicios que se despliegan por separado. Los
cambios tienen que ser compatibles hacia atras: agregar campos opcionales es seguro, quitar
campos o cambiar su significado rompe a los consumidores que todavia no se actualizaron.

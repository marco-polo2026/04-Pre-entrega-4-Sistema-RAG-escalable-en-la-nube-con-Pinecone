# Versionado de APIs en microservicios

## Por que hace falta versionar

Un microservicio expone una API que consumen otros equipos, con sus propios ciclos de
despliegue. No existe un momento en el que todos los consumidores se actualicen a la vez.
Por eso cualquier cambio en la API convive un tiempo con la version anterior, y el
versionado es lo que hace posible esa convivencia.

## Cambios compatibles e incompatibles

Un cambio es compatible hacia atras cuando un consumidor que no se entero de nada sigue
funcionando igual. Agregar un campo opcional a la respuesta, agregar un endpoint nuevo o
aceptar un parametro opcional adicional son cambios compatibles.

Un cambio es incompatible cuando rompe a los consumidores existentes. Quitar un campo,
renombrarlo, cambiar su tipo, volver obligatorio un parametro que era opcional o modificar
el significado de un valor son cambios incompatibles. La regla practica es que solo los
cambios incompatibles justifican una version nueva.

## Estrategias de versionado

La version en la ruta, del estilo /v1/pedidos, es la mas explicita y la mas facil de rutear
en un gateway, a costa de duplicar rutas. La version en un encabezado mantiene la URL
estable pero vuelve el contrato menos visible y mas dificil de probar desde un navegador.

En la practica, la version en la ruta es la opcion mas comun en APIs internas entre
microservicios, porque el costo de que sea explicita es menor que el de que sea invisible.

## Depreciacion ordenada

Publicar la version nueva no alcanza: hay que retirar la vieja. Un proceso ordenado anuncia
la fecha de retiro, marca la version vieja como deprecada en la documentacion y en los
encabezados de respuesta, mide que consumidores siguen usandola, y recien despues la apaga.

Apagar una version sin medir quien la consume es la forma mas comun de romper produccion un
viernes.

## Contratos verificables

Que el contrato este documentado no garantiza que el codigo lo cumpla. Las pruebas de
contrato verifican automaticamente que el proveedor siga respetando lo que los consumidores
esperan, y corren en el pipeline de cada despliegue. Sin eso, la unica verificacion real
ocurre en produccion.

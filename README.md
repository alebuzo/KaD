# KaD
Proyecto Final para el curso de Arquitectura Orientada a Servicios I Semestre 2026

## Integrantes
Katharina Alfaro Solís

Alexa Carmona Buzo

Daymer Vargas Vargas

## Tema
Implementación de un Modelo Zero Trust en una Arquitectura de Microservicios utilizando el Servicio de Pago del Ejemplo "Microservices Demo" de Google Cloud: Online Boutique

## Importancia en relación al tema de microservicios y arquitectura orientada a servicios
El uso de microservicios y arquitectura orientada a servicios hace que las aplicaciones estén constituidas de múltiples componentes independientes que interactúan
entre sí a través de APIs y canales de comunicación internos. Este tipo de estructuras, ofrece ventajas en escalabilidad y agilidad, sin embargo, también
introduce desafíos en materia de seguridad, ya que se aumenta la superficie de ataque y la complejidad para gestionar de forma adecuada las interacciones
entre microservicios.

La implementación de un modelo Zero Trust en el contexto brindado resulta fundamental para garantizar que cada interacción entre microservicios sea segura,
autenticada y autorizada, sin confiar en ningún componente interno. De forma que aplicar Zero Trust permite reducir riesgos y asegurar que solo los servicios y
usuarios autorizados puedan acceder a recursos específicos bajo condiciones controladas y verificadas en tiempo real.

Este proyecto, basado en el servicio de pago del repositorio "microservices-demo" de Google Cloud, busca demostrar cómo integrar eficazmente los principios de
Zero Trust en una arquitectura de microservicios, fortaleciendo así la seguridad, la confidencialidad y la integridad del sistema de pagos.

## Descripción de la implementación

### Uso de Online Boutique como base
Para el desarrollo del proyecto se plantea utilizar el sistema de Online Boutique, una aplicación de comercio electrónico basada en microservicios, donde cada uno de ellos cumple un papel importante en el proceso de compra y visualización de elementos, tales como catálogo de productos, carrito de compras, pagos, conversión de moneda, entre otros. Entre ellos se comunican mediante llamadas gRPC (Google Remote Procedure Call), un framework de comunicación de alto rendimiento desarrollado por Google que permite invocar funciones entre servicios de forma remota como si fueran llamadas locales.  
 
En este contexto, servicios como `paymentservice`, `checkoutservice` y `cartservice` son especialmente críticos, ya que manejan transacciones, orquestación de compras y datos sensibles del usuario. El proyecto propone fortalecer este entorno mediante la implementación de un modelo Zero Trust, donde cada interacción entre servicios sea autenticada, autorizada y monitoreada, evitando accesos indebidos y movimientos laterales dentro del sistema. 
 
Los servicios se comunican de la siguiente manera, el Frontend es la cara visible para el usuario, cuando necesita mostrar productos llama a `productcatalog`, si requiere mostrar precios en otra moneda consulta a `currency`, y para mostrar contenido adicional invoca a `recommendation` y `ad`. Cuando el usuario agrega algo al carrito, el frontend llama a cart, el cual persiste esa información en Redis cache. Al momento de realizar una compra, el frontend transfiere el control a `checkout`, quien orquesta todo el proceso llamando a `cart` para recuperar los artículos seleccionados, a `currency` para la conversión de precios, a `shipping` para calcular el costo de envío, a `payment` para procesar el pago, y finalmente a email para enviar la confirmación de la orden. Por su parte, el `loadgenerator` es un servicio auxiliar que simula usuarios reales realizando peticiones al frontend, utilizado únicamente con fines de pruebas de carga.

<img width="3556" height="1954" alt="image" src="https://github.com/user-attachments/assets/175bbfa4-eab0-4ffb-beab-594d64ab47f4" />
Imagen Obtenida del Repositorio a utilizar: https://github.com/GoogleCloudPlatform/microservices-demo

### Implementación de Zero Trust



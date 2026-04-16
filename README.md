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

## Descripción de la aplicación

### Uso de Online Boutique como base
Para el desarrollo del proyecto se plantea utilizar el sistema de Online Boutique, una aplicación de comercio electrónico basada en microservicios, donde cada uno de ellos cumple un papel importante en el proceso de compra y visualización de elementos, tales como catálogo de productos, carrito de compras, pagos, conversión de moneda, entre otros. Entre ellos se comunican mediante llamadas gRPC (Google Remote Procedure Call), un framework de comunicación de alto rendimiento desarrollado por Google que permite invocar funciones entre servicios de forma remota como si fueran llamadas locales.  
 
En este contexto, servicios como `paymentservice`, `checkoutservice` y `cartservice` son especialmente críticos, ya que manejan transacciones, orquestación de compras y datos sensibles del usuario. El proyecto propone fortalecer este entorno mediante la implementación de un modelo Zero Trust, donde cada interacción entre servicios sea autenticada, autorizada y monitoreada, evitando accesos indebidos y movimientos laterales dentro del sistema. 
 
Los servicios se comunican de la siguiente manera, el Frontend es la cara visible para el usuario, cuando necesita mostrar productos llama a `productcatalog`, si requiere mostrar precios en otra moneda consulta a `currency`, y para mostrar contenido adicional invoca a `recommendation` y `ad`. Cuando el usuario agrega algo al carrito, el frontend llama a cart, el cual persiste esa información en Redis cache. Al momento de realizar una compra, el frontend transfiere el control a `checkout`, quien orquesta todo el proceso llamando a `cart` para recuperar los artículos seleccionados, a `currency` para la conversión de precios, a `shipping` para calcular el costo de envío, a `payment` para procesar el pago, y finalmente a email para enviar la confirmación de la orden. Por su parte, el `loadgenerator` es un servicio auxiliar que simula usuarios reales realizando peticiones al frontend, utilizado únicamente con fines de pruebas de carga.

<img width="3556" height="1954" alt="image" src="https://github.com/user-attachments/assets/175bbfa4-eab0-4ffb-beab-594d64ab47f4" />
Imagen Obtenida del Repositorio a utilizar: https://github.com/GoogleCloudPlatform/microservices-demo

### Descripción de servicios

| Nombre del Servicio | Descripción |
|---|---|
| Frontend | Servicio encargado de la interfaz web del sistema. Recibe las solicitudes del usuario y coordina llamadas a los demás microservicios para construir la experiencia completa. |
| CartService | Servicio encargado de gestionar el carrito de compras del usuario, permitiendo agregar, eliminar y consultar productos seleccionados. |
| PaymentService | Servicio encargado de procesar los pagos de las órdenes, simulando transacciones financieras dentro del sistema. |
| ProductCatalogService | Servicio encargado de proporcionar la información de los productos disponibles, incluyendo descripciones, precios y detalles. |
| RecommendationService | Servicio encargado de generar recomendaciones de productos para el usuario basadas en su comportamiento o en el contenido del carrito. |
| ShippingService | Servicio encargado de calcular costos de envío y simular la logística de entrega de los productos. |
| CurrencyService | Servicio encargado de realizar conversiones de moneda para mostrar precios en diferentes divisas según la ubicación del usuario. |
| EmailService | Servicio encargado de enviar confirmaciones de compra y notificaciones al usuario tras completar una transacción. |
| CheckoutService | Servicio encargado de orquestar el proceso completo de compra, coordinando la interacción entre carrito, pago, envío y otros servicios necesarios. |
| AdService | Servicio encargado de proporcionar anuncios o contenido promocional dentro de la plataforma. No es crítico para el flujo principal de compra. |

## Implementación de Zero Trust

### Estado de la aplicación

La aplicación fue diseñada con Istio en mente pero service mesh no está activado. El tráfico entre servicios no está encriptado ni autenticado, con HTTP/gRPC sin control de acceso.

- Todo el tráfico entre servicios no está cifrado y no tiene restricciones.
- El tráfico entre pods es en texto plano; no se verifica la identidad de las cargas de trabajo (no se aplica mTLS).
- Cualquier servicio puede llamar a cualquier otro servicio dentro del clúster.
- Cualquier pod puede llamar a cualquier endpoint externo.

### Plan de implementación
Para implementarlo sobre la arquitectura de Online Boutique, con especial énfasis en el flujo de pagos, se definen tres fases progresivas:

**Fase 1**: Activación de la infraestructura de Istio y NetworkPolicy (Fundación) Como base de toda la estrategia, se habilita la infraestructura de seguridad mediante Istio, seleccionado sobre alternativas como Google Cloud Service Mesh y Linkerd por ofrecer control total, amplia documentación comunitaria y compatibilidad con cualquier entorno Kubernetes.

**Fase 2**: Aplicación de mTLS estricto en toda la malla Se establece que todo el tráfico entre pods debe ser mutuamente autenticado y cifrado, eliminando cualquier posibilidad de comunicación en texto plano dentro del clúster. Esto es especialmente relevante para proteger las interacciones entre checkoutservice, paymentservice y cartservice, donde se maneja información sensible del usuario.

**Fase 3**: Control de acceso servicio a servicio con AuthorizationPolicies Se implementa un modelo de denegación por defecto con permisos explícitos, de forma que únicamente los servicios estrictamente necesarios puedan comunicarse con paymentservice. Esto aplica directamente los pilares de mínimo privilegio y nunca confiar de Zero Trust: incluso si un servicio es comprometido, cualquier llamada no autorizada hacia servicios críticos será rechazada por el destino.


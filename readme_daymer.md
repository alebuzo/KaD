# Implementación de Zero Trust - Documentación de Daymer Vargas

## Objetivo

Este documento registra el proceso paso a paso de la implementación de un modelo **Zero Trust** sobre la arquitectura de microservicios de Online Boutique, ejecutada localmente con **Minikube**. El enfoque inicial se centra en asegurar la comunicación entre `checkoutservice` y `emailservice`, donde solo checkout tiene permitido invocar a email.

## ¿Qué es Zero Trust?

Zero Trust es un modelo de seguridad que asume que **ningún componente dentro de la red es confiable por defecto**, sin importar si está dentro del perímetro del clúster. Cada comunicación entre servicios debe ser:

- **Autenticada**: Se verifica la identidad de quien hace la solicitud.
- **Autorizada**: Se valida que tenga permiso para acceder al recurso.
- **Cifrada**: El tráfico viaja encriptado, nunca en texto plano.

## ¿Qué es Istio?

Istio es un **service mesh** (malla de servicios) que se instala sobre Kubernetes. Funciona inyectando un proxy **Envoy** como sidecar en cada pod. Este proxy intercepta todo el tráfico de entrada y salida del pod, permitiendo:

- Cifrado automático con mTLS (mutual TLS)
- Control de acceso entre servicios (AuthorizationPolicies)
- Observabilidad del tráfico (métricas, trazas, logs)

Sin Istio, los pods se comunican directamente sin verificación. Con Istio, todo el tráfico pasa por el proxy Envoy que aplica las políticas de seguridad.

---

## Prerrequisitos

- Minikube instalado y corriendo
- kubectl configurado
- Aplicación Online Boutique desplegada

### Comandos para levantar la aplicación base

```bash
# Iniciar Minikube
minikube start

# Desplegar todos los microservicios de Online Boutique
kubectl apply -f ./release/kubernetes-manifests.yaml

# Verificar que los pods estén corriendo
kubectl get pods
```

### Acceder a la aplicación web (Frontend)

```bash
# Hacer port-forward del servicio frontend al puerto local 8080
kubectl port-forward svc/frontend 8080:80
```

Luego abrir en el navegador: `http://localhost:8080`

> ⚠️ **IMPORTANTE**: El comando `port-forward` debe mantenerse ejecutándose en un terminal separado. Si se cierra el terminal o se presiona `Ctrl+C`, el acceso a la aplicación se pierde. Cada vez que se quiera acceder al frontend, se debe volver a ejecutar este comando.

---

## Fase 1: Instalación de Istio y activación del Sidecar Envoy

### ¿Qué se logra en esta fase?

Se instala Istio en el clúster de Minikube y se habilita la inyección automática del proxy Envoy en todos los pods. Esto es la **fundación** sobre la cual se construyen las políticas de seguridad. Sin el sidecar Envoy, Istio no puede interceptar ni controlar el tráfico.

### Paso 1: Descargar Istio

```bash
curl -L https://istio.io/downloadIstio | sh -
```

**¿Qué hace?** Descarga la última versión estable de Istio, incluyendo el binario `istioctl` (herramienta de línea de comandos) y los manifiestos de instalación.

### Paso 2: Agregar istioctl al PATH

```bash
cd istio-*
export PATH=$PWD/bin:$PATH
```

**¿Qué hace?** Agrega el binario `istioctl` al PATH del sistema para poder ejecutarlo desde cualquier ubicación en el terminal.

### Paso 3: Verificar que istioctl funciona

```bash
istioctl version
```

**¿Qué hace?** Confirma que la herramienta de línea de comandos de Istio está correctamente instalada y accesible.

### Paso 4: Instalar Istio en el clúster

```bash
istioctl install --set profile=demo -y
```

**¿Qué hace?** Instala los componentes de Istio dentro del clúster de Kubernetes:
- **istiod**: El plano de control de Istio. Gestiona certificados, configuración y políticas.
- **istio-ingressgateway**: Gateway de entrada para tráfico externo.
- **istio-egressgateway**: Gateway de salida para tráfico hacia servicios externos.

El perfil `demo` incluye todos los componentes, ideal para desarrollo local y pruebas.

### Paso 5: Verificar la instalación de Istio

```bash
kubectl get pods -n istio-system
```

**¿Qué hace?** Lista los pods en el namespace `istio-system` donde vive Istio. Se espera ver:
```
NAME                                    READY   STATUS
istiod-xxxxxxxxx-xxxxx                  1/1     Running
istio-ingressgateway-xxxxxxxxx-xxxxx    1/1     Running
istio-egressgateway-xxxxxxxxx-xxxxx     1/1     Running
```

### Paso 6: Habilitar la inyección automática del sidecar

```bash
kubectl label namespace default istio-injection=enabled
```

**¿Qué hace?** Etiqueta el namespace `default` para que Istio **inyecte automáticamente** un contenedor sidecar (proxy Envoy) en cada pod que se cree o reinicie en ese namespace. Sin esta etiqueta, los pods se crean sin el proxy y quedan fuera de la malla de servicios.

### Paso 7: Reiniciar los deployments para inyectar el sidecar

```bash
kubectl rollout restart deployment
```

**¿Qué hace?** Reinicia todos los deployments del namespace. Al reiniciarse, los pods son recreados y como el namespace tiene la etiqueta `istio-injection=enabled`, Kubernetes automáticamente les inyecta el contenedor sidecar Envoy.

### Paso 8: Verificar que los pods tienen el sidecar inyectado

```bash
kubectl get pods
```

**¿Qué hace?** Muestra el estado de todos los pods. La columna `READY` debe mostrar **`2/2`** (2 contenedores listos de 2 totales):
- Contenedor 1: La aplicación del microservicio
- Contenedor 2: El proxy Envoy (sidecar de Istio)

**Resultado esperado:**
```
NAME                                     READY   STATUS
cartservice-xxxxx                        2/2     Running
checkoutservice-xxxxx                    2/2     Running
emailservice-xxxxx                       2/2     Running
frontend-xxxxx                           2/2     Running
paymentservice-xxxxx                     2/2     Running
productcatalogservice-xxxxx              2/2     Running
recommendationservice-xxxxx              2/2     Running
shippingservice-xxxxx                    2/2     Running
redis-cart-xxxxx                         2/2     Running
loadgenerator-xxxxx                      2/2     Running
adservice-xxxxx                          2/2     Running
currencyservice-xxxxx                    2/2     Running
```

### Estado después de Fase 1

```
✅ Fase 1: Instalar Istio + Sidecar Envoy inyectado
⬜ Fase 2: mTLS estricto
⬜ Fase 3: AuthorizationPolicies (checkout → email)
```

En este punto, Istio está instalado y cada pod tiene su proxy Envoy. Sin embargo, el tráfico aún puede ir en texto plano (modo PERMISSIVE por defecto). En la Fase 2 se forzará mTLS estricto.

---

## Fase 2: mTLS Estricto

### ¿Qué se logra en esta fase?

Se activa **mutual TLS (mTLS)** en modo estricto para todo el namespace `default`. Esto garantiza que:

- Todo el tráfico entre pods está **cifrado** (ya no viaja en texto plano).
- Ambos lados de la comunicación se **autentican mutuamente** con certificados X.509 emitidos automáticamente por Istio (a través de istiod).
- Cualquier intento de comunicación sin un certificado válido de la malla es **rechazado**.

Esto elimina la posibilidad de que un atacante intercepte tráfico entre servicios (ataques man-in-the-middle) o que un pod no autorizado se haga pasar por un servicio legítimo.

### ¿Qué es mTLS?

En TLS normal (como HTTPS), solo el **servidor** presenta un certificado para probar su identidad. En **mutual TLS (mTLS)**, **ambas partes** presentan certificados:

```
checkoutservice ──(certificado de checkout)──→ emailservice
checkoutservice ←──(certificado de email)─── emailservice
```

Istio maneja esto automáticamente: istiod actúa como una Autoridad Certificadora (CA) interna que emite y rota certificados para cada pod.

### Paso 1: Crear el archivo PeerAuthentication

Se creó el archivo `istio-manifests/peer-authentication.yaml`:

```yaml
apiVersion: security.istio.io/v1beta1
kind: PeerAuthentication
metadata:
  name: default
  namespace: default
spec:
  mtls:
    mode: STRICT
```

**Explicación del manifiesto:**
- `kind: PeerAuthentication`: Recurso de Istio que define cómo se autentica el tráfico entre peers (pods).
- `metadata.name: default`: Al nombrarlo "default" y estar en el namespace "default", aplica a **todos los pods** del namespace.
- `mtls.mode: STRICT`: Rechaza cualquier conexión que no use mTLS. La alternativa sería `PERMISSIVE` que acepta tanto tráfico plano como mTLS (modo por defecto de Istio).

### Paso 2: Aplicar la política

```bash
kubectl apply -f ./istio-manifests/peer-authentication.yaml
```

**¿Qué hace?** Aplica la política de PeerAuthentication al clúster. A partir de este momento, Istio exige que todo tráfico entre pods del namespace `default` sea mutuamente autenticado y cifrado.

### Paso 3: Verificar que la política está activa

```bash
kubectl get peerauthentication
```

**¿Qué hace?** Lista las políticas de PeerAuthentication aplicadas. Se espera ver:
```
NAME      MODE     AGE
default   STRICT   Xs
```

### Paso 4: Verificar que la aplicación sigue funcionando

```bash
kubectl port-forward svc/frontend 8080:80
```

**¿Qué hace?** Permite acceder al frontend en `http://localhost:8080`. La aplicación debe seguir funcionando normalmente, ya que todos los pods tienen el sidecar Envoy que maneja mTLS automáticamente.

### Paso 5: Confirmar que mTLS está activo en emailservice

```bash
istioctl x describe pod $(kubectl get pod -l app=emailservice -o jsonpath='{.items[0].metadata.name}')
```

**¿Qué hace?** Consulta a Istio el estado de seguridad del pod de emailservice. Debe reportar que el pod está aplicando mTLS.

### Estado después de Fase 2

```
✅ Fase 1: Instalar Istio + Sidecar Envoy inyectado
✅ Fase 2: mTLS estricto activado
⬜ Fase 3: AuthorizationPolicies (checkout → email)
```

En este punto, todo el tráfico entre pods está cifrado y autenticado. Sin embargo, **cualquier servicio** dentro de la malla aún puede comunicarse con cualquier otro. En la Fase 3 se restringirá quién puede hablar con quién.

---

## Fase 3: AuthorizationPolicies - Control de Acceso (checkout → email)

### ¿Qué se logra en esta fase?

Se implementa el principio de **mínimo privilegio**: solo `checkoutservice` puede comunicarse con `emailservice`. Cualquier otro servicio que intente contactar a emailservice será **denegado automáticamente**.

Esto es el corazón de Zero Trust: **nunca confiar, siempre verificar**. Aunque un servicio esté dentro del clúster y tenga mTLS activo, si no tiene permiso explícito, no puede comunicarse.

### ¿Cómo funciona?

Istio usa **AuthorizationPolicy** para definir reglas de acceso. Cuando NO existen políticas, todo está permitido. Pero cuando se aplica una política con `action: ALLOW` a un servicio, se activa un modo de **denegación implícita**: todo lo que no esté explícitamente permitido queda bloqueado.

```
ANTES (sin AuthorizationPolicy):
  frontend ──→ emailservice        ✅ permitido
  checkoutservice ──→ emailservice ✅ permitido
  adservice ──→ emailservice       ✅ permitido
  (cualquiera) ──→ emailservice    ✅ permitido

DESPUÉS (con AuthorizationPolicy):
  frontend ──→ emailservice        ❌ DENEGADO
  checkoutservice ──→ emailservice ✅ PERMITIDO
  adservice ──→ emailservice       ❌ DENEGADO
  (cualquiera) ──→ emailservice    ❌ DENEGADO
```

### ¿Cómo identifica Istio a cada servicio?

Istio identifica los servicios mediante su **Service Account** de Kubernetes. Cada pod tiene un service account asociado, y cuando mTLS está activo, Istio incluye la identidad del service account en el certificado. Así sabe exactamente quién está haciendo la solicitud.

El formato de la identidad (principal) es:
```
cluster.local/ns/<namespace>/sa/<service-account-name>
```

Para checkoutservice:
```
cluster.local/ns/default/sa/checkoutservice
```

### Paso 1: Crear el archivo AuthorizationPolicy

Se creó el archivo `istio-manifests/authz-emailservice.yaml`:

```yaml
apiVersion: security.istio.io/v1beta1
kind: AuthorizationPolicy
metadata:
  name: emailservice-allow-checkout-only
  namespace: default
spec:
  selector:
    matchLabels:
      app: emailservice
  action: ALLOW
  rules:
  - from:
    - source:
        principals: ["cluster.local/ns/default/sa/checkoutservice"]
```

**Explicación del manifiesto:**
- `selector.matchLabels.app: emailservice`: Esta política se aplica **solo** a los pods con label `app: emailservice`.
- `action: ALLOW`: Define una regla de permiso. Al existir una regla ALLOW, todo lo demás queda **implícitamente denegado**.
- `rules.from.source.principals`: Lista de identidades (service accounts) que tienen permiso de comunicarse con emailservice. Solo `checkoutservice` está en la lista.

### Paso 2: Aplicar la política

```bash
kubectl apply -f ./istio-manifests/authz-emailservice.yaml
```

**¿Qué hace?** Aplica la política de autorización. A partir de este momento, solo los pods con el service account `checkoutservice` pueden enviar tráfico a `emailservice`.

### Paso 3: Verificar que la política está activa

```bash
kubectl get authorizationpolicy
```

**¿Qué hace?** Lista las políticas de autorización aplicadas. Se espera ver:
```
NAME                               AGE
emailservice-allow-checkout-only   Xs
```

### Paso 4: Probar que el flujo legítimo funciona

Acceder al frontend y completar una compra:

```bash
kubectl port-forward svc/frontend 8080:80
```

1. Abrir `http://localhost:8080`
2. Agregar un producto al carrito
3. Hacer checkout (completar la compra)
4. La compra debe completarse exitosamente → checkout pudo llamar a email ✅

### Paso 5: Verificar que otros servicios NO pueden contactar a emailservice

```bash
# Intentar llamar a emailservice desde frontend (debería ser DENEGADO)
kubectl exec $(kubectl get pod -l app=frontend -o jsonpath='{.items[0].metadata.name}') -c server -- wget -qO- --timeout=3 http://emailservice:5000 2>&1 || echo "CONEXIÓN DENEGADA ✅"
```

**¿Qué hace?** Intenta hacer una solicitud HTTP desde el pod del frontend hacia emailservice. Como frontend no está en la lista de principals permitidos, Istio debería denegar la conexión con un error `RBAC: access denied`.

### Paso 6: Verificar logs de Istio (opcional)

```bash
# Ver logs del sidecar Envoy de emailservice
kubectl logs $(kubectl get pod -l app=emailservice -o jsonpath='{.items[0].metadata.name}') -c istio-proxy | tail -20
```

**¿Qué hace?** Muestra los logs del proxy Envoy de emailservice, donde se pueden ver las conexiones permitidas y denegadas.

### Estado después de Fase 3

```
✅ Fase 1: Instalar Istio + Sidecar Envoy inyectado
✅ Fase 2: mTLS estricto activado
✅ Fase 3: AuthorizationPolicy (solo checkout → email)
```

### Resumen de archivos creados para Zero Trust

```
istio-manifests/
├── peer-authentication.yaml       # Fase 2: mTLS estricto
└── authz-emailservice.yaml        # Fase 3: Solo checkout puede hablar con email
```

### Comandos para aplicar todo desde cero

```bash
# Fase 2
kubectl apply -f ./istio-manifests/peer-authentication.yaml

# Fase 3
kubectl apply -f ./istio-manifests/authz-emailservice.yaml
```

### Comandos para revertir (si algo falla)

```bash
# Eliminar la política de autorización
kubectl delete -f ./istio-manifests/authz-emailservice.yaml

# Eliminar mTLS estricto (vuelve a PERMISSIVE)
kubectl delete -f ./istio-manifests/peer-authentication.yaml
```

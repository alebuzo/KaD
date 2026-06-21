# Unauthorized Tester - Demostración de Zero Trust

Este microservicio está diseñado para **fallar intencionalmente**. Su propósito es demostrar que las políticas de Zero Trust (AuthorizationPolicies de Istio) funcionan correctamente.

## ¿Qué hace?

Intenta llamar a `paymentservice` usando gRPC, pero **NO tiene autorización** para hacerlo. Según la política de Zero Trust configurada, solo `checkoutservice` puede comunicarse con `paymentservice`.

## Resultado Esperado

Cuando este servicio intente llamar a `paymentservice`, Istio **DENEGARÁ** la conexión con un error `RBAC: access denied`.

## Cómo Probar

### Paso 1: Construir la imagen Docker en Minikube

```bash
# Configurar Docker para usar el daemon de Minikube
eval $(minikube docker-env)

# Construir la imagen
cd src/unauthorizedtester
docker build -t unauthorizedtester:latest .
```

### Paso 2: Desplegar en Kubernetes

```bash
# Aplicar el manifiesto
kubectl apply -f kubernetes-manifests/unauthorizedtester.yaml

# Verificar que el pod esté corriendo (debe mostrar 2/2 por el sidecar de Istio)
kubectl get pods -l app=unauthorizedtester
```

### Paso 3: Probar el bloqueo de Zero Trust

**Opción A: Usando port-forward**

```bash
# En un terminal, hacer port-forward
kubectl port-forward svc/unauthorizedtester 9090:8080

# En otro terminal, probar el endpoint
curl http://localhost:9090/test-payment
```

**Opción B: Ejecutando desde dentro del pod**

```bash
# Obtener el nombre del pod
POD_NAME=$(kubectl get pod -l app=unauthorizedtester -o jsonpath='{.items[0].metadata.name}')

# Ejecutar curl desde dentro del contenedor
kubectl exec $POD_NAME -c server -- wget -qO- http://localhost:8080/test-payment
```

### Resultado Esperado

```json
{
  "status": "blocked",
  "message": "Acceso DENEGADO por Istio - Zero Trust funcionando correctamente",
  "error": "RBAC: access denied",
  "errorCode": 7
}
```

### Paso 4: Verificar los logs

```bash
# Ver logs del servicio
kubectl logs -l app=unauthorizedtester -c server

# Ver logs del sidecar Istio (donde se ve el bloqueo)
kubectl logs -l app=unauthorizedtester -c istio-proxy | tail -20
```

## Comparación: Servicio Autorizado vs No Autorizado

| Servicio | Puede llamar a PaymentService | Motivo |
|----------|------------------------------|--------|
| checkoutservice | ✅ SÍ | Está en la lista de principals permitidos |
| unauthorizedtester | ❌ NO | No está en la lista de principals permitidos |
| frontend | ❌ NO | No está en la lista de principals permitidos |
| cualquier otro | ❌ NO | No está en la lista de principals permitidos |

## Política que bloquea el acceso

Archivo: `istio-manifests/authz-paymentservice.yaml`

```yaml
apiVersion: security.istio.io/v1beta1
kind: AuthorizationPolicy
metadata:
  name: paymentservice-allow-checkout-only
  namespace: default
spec:
  selector:
    matchLabels:
      app: paymentservice
  action: ALLOW
  rules:
  - from:
    - source:
        principals: ["cluster.local/ns/default/sa/checkoutservice"]
```

Solo el service account `checkoutservice` tiene permiso. El service account `unauthorizedtester` **no está en la lista**, por lo tanto es denegado.

## Limpieza

```bash
# Eliminar el deployment y servicio
kubectl delete -f kubernetes-manifests/unauthorizedtester.yaml
```

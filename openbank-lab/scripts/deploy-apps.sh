#!/usr/bin/env bash
set -euo pipefail

IMAGE="image-registry.openshift-image-registry.svc:5000/openbank-core/openbank-api:1.0"

deploy_api() {
    local API="$1"
    local NAMESPACE="$2"

    echo "Deploying ${API}-api in ${NAMESPACE}"

    oc apply -f - <<YAML
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ${API}-api
  namespace: ${NAMESPACE}
  labels:
    app: ${API}-api
    app.kubernetes.io/part-of: openbank
spec:
  replicas: 1
  selector:
    matchLabels:
      app: ${API}-api
  template:
    metadata:
      labels:
        app: ${API}-api
        app.kubernetes.io/part-of: openbank
        version: v1
    spec:
      containers:
        - name: api
          image: ${IMAGE}
          imagePullPolicy: Always
          env:
            - name: API_TYPE
              value: "${API}"
            - name: API_VERSION
              value: "1.0.0"
          ports:
            - name: http
              containerPort: 8080
          resources:
            requests:
              cpu: 50m
              memory: 128Mi
            limits:
              cpu: 500m
              memory: 256Mi
          readinessProbe:
            httpGet:
              path: /readyz
              port: http
            initialDelaySeconds: 5
            periodSeconds: 10
          livenessProbe:
            httpGet:
              path: /healthz
              port: http
            initialDelaySeconds: 10
            periodSeconds: 15
          securityContext:
            allowPrivilegeEscalation: false
            capabilities:
              drop:
                - ALL
            runAsNonRoot: true
            seccompProfile:
              type: RuntimeDefault
---
apiVersion: v1
kind: Service
metadata:
  name: ${API}-api
  namespace: ${NAMESPACE}
  labels:
    app: ${API}-api
    app.kubernetes.io/part-of: openbank
spec:
  selector:
    app: ${API}-api
  ports:
    - name: http
      port: 8080
      targetPort: http
  type: ClusterIP
YAML
}

for API in customers accounts payments fraud legacy unstable
do
    deploy_api "$API" openbank-core
done

for API in exchange premium
do
    deploy_api "$API" openbank-partners
done

echo "Waiting for deployments..."

for API in customers accounts payments fraud legacy unstable
do
    oc rollout status deployment/"${API}-api" \
        -n openbank-core --timeout=180s
done

for API in exchange premium
do
    oc rollout status deployment/"${API}-api" \
        -n openbank-partners --timeout=180s
done

echo "OPENBANK DEPLOYMENT COMPLETED"

oc get deployments -n openbank-core
oc get deployments -n openbank-partners

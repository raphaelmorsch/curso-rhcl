#!/usr/bin/env bash
set -euo pipefail

GATEWAY_NAME="openbank-gateway"
GATEWAY_NS="openbank-gateway"

GATEWAY_HOST="api-openbank.apps.cluster-mbh58.dyn.redhatworkshops.io"

mkdir -p manifests/httproutes

create_route() {

  local API="$1"
  local NAMESPACE="$2"

  cat > "manifests/httproutes/${API}.yaml" <<YAML
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: ${API}
  namespace: ${NAMESPACE}
  labels:
    app: ${API}-api
    app.kubernetes.io/part-of: openbank
spec:
  parentRefs:
    - name: ${GATEWAY_NAME}
      namespace: ${GATEWAY_NS}
      sectionName: http
  hostnames:
    - "${GATEWAY_HOST}"
  rules:
    - matches:
        - path:
            type: PathPrefix
            value: /${API}
      backendRefs:
        - name: ${API}-api
          port: 8080
YAML

  oc apply -f "manifests/httproutes/${API}.yaml"
}

for API in accounts payments legacy unstable
do
  create_route "$API" openbank-core
done

for API in exchange premium
do
  create_route "$API" openbank-partners
done

echo "OpenBank HTTPRoutes deployed."

#!/usr/bin/env bash

CLIENT_NS="openbank-partners"
CLIENT="openbank-client"

PASS=0
FAIL=0

check() {
    local NAME="$1"
    local URL="$2"
    local EXPECTED="$3"

    RESULT=$(oc exec -n "$CLIENT_NS" "$CLIENT" -- \
        curl -s -o /dev/null \
        --connect-timeout 5 \
        --max-time 10 \
        -w '%{http_code}' "$URL")

    if [[ "$RESULT" == "$EXPECTED" ]]; then
        echo "[PASS] $NAME -> HTTP $RESULT"
        PASS=$((PASS+1))
    else
        echo "[FAIL] $NAME -> HTTP $RESULT"
        FAIL=$((FAIL+1))
    fi
}

for API in customers accounts payments fraud legacy unstable
do
    BASE="http://${API}-api.openbank-core.svc.cluster.local:8080"

    check "$API health" "$BASE/healthz" 200
    check "$API OpenAPI" "$BASE/openapi.json" 200
done

for API in exchange premium
do
    BASE="http://${API}-api.openbank-partners.svc.cluster.local:8080"

    check "$API health" "$BASE/healthz" 200
    check "$API OpenAPI" "$BASE/openapi.json" 200
done

check "Customers endpoint" \
"http://customers-api.openbank-core.svc.cluster.local:8080/customers" 200

check "Accounts endpoint" \
"http://accounts-api.openbank-core.svc.cluster.local:8080/accounts" 200

check "Exchange endpoint" \
"http://exchange-api.openbank-partners.svc.cluster.local:8080/exchange" 200

check "Premium endpoint" \
"http://premium-api.openbank-partners.svc.cluster.local:8080/premium" 200

check "Legacy endpoint" \
"http://legacy-api.openbank-core.svc.cluster.local:8080/legacy" 200

check "Unstable simulated error" \
"http://unstable-api.openbank-core.svc.cluster.local:8080/unstable?status=500" 500

echo
echo "=============================="
echo "OPENBANK VALIDATION SUMMARY"
echo "PASS: $PASS"
echo "FAIL: $FAIL"
echo "=============================="

[[ "$FAIL" -eq 0 ]]

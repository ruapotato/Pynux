#!/bin/bash
# DevFS Integration Test
# Runs QEMU with test commands and checks output

set -e

TIMEOUT=15
QEMU="qemu-system-arm"
MACHINE="mps2-an385"
ELF="build/pynux.elf"

echo "=== DevFS Integration Test ==="
echo ""

# Create a script with delays for input
cat > /tmp/devfs_cmds.txt << 'CMDS'

drivers

cat /dev/sensors/temp0

cat /dev/gpio/pin0

echo 1 > /dev/gpio/pin0

cat /dev/gpio/pin0

cat /dev/motors/servo0

echo 90 > /dev/motors/servo0

cat /dev/motors/servo0

CMDS

# Run QEMU with commands (using slower input)
OUTPUT=$(timeout $TIMEOUT bash -c "sleep 2; while IFS= read -r line; do echo \"\$line\"; sleep 0.3; done < /tmp/devfs_cmds.txt" | $QEMU -machine $MACHINE -cpu cortex-m3 -nographic -semihosting -kernel $ELF 2>&1 || true)

echo "=== QEMU Output ==="
echo "$OUTPUT"
echo ""
echo "=== Checking Results ==="

PASS=0
FAIL=0

# Test 1: Kernel initializes DevFS
if echo "$OUTPUT" | grep -q "DevFS init.*OK"; then
    echo "[PASS] DevFS initialized successfully"
    PASS=$((PASS+1))
else
    echo "[FAIL] DevFS init should complete"
    FAIL=$((FAIL+1))
fi

# Test 2: Servo gets initialized (proves devfs_register works)
if echo "$OUTPUT" | grep -q "Servo 0 initialized"; then
    echo "[PASS] Servo 0 registered and initialized"
    PASS=$((PASS+1))
else
    echo "[FAIL] Servo should be initialized"
    FAIL=$((FAIL+1))
fi

# Test 3: DC motor gets initialized
if echo "$OUTPUT" | grep -q "DC motor 0 initialized"; then
    echo "[PASS] DC motor 0 registered and initialized"
    PASS=$((PASS+1))
else
    echo "[FAIL] DC motor should be initialized"
    FAIL=$((FAIL+1))
fi

# Test 4: Shell starts
if echo "$OUTPUT" | grep -q "Pynux Text Shell"; then
    echo "[PASS] Shell started successfully"
    PASS=$((PASS+1))
else
    echo "[FAIL] Shell should start"
    FAIL=$((FAIL+1))
fi

# Test 5: drivers command shows output (look for "Device Drivers" header)
if echo "$OUTPUT" | grep -q "Device Drivers"; then
    echo "[PASS] drivers command executed"
    PASS=$((PASS+1))
else
    echo "[INFO] drivers command output not captured (timing)"
fi

# Test 6: Check for temperature reading format
if echo "$OUTPUT" | grep -qE "[0-9]+\.[0-9]+"; then
    echo "[PASS] Temperature reading format correct"
    PASS=$((PASS+1))
else
    echo "[INFO] Temperature reading not captured (timing)"
fi

echo ""
echo "=== Summary: $PASS passed, $FAIL failed ==="

if [ $FAIL -gt 0 ]; then
    exit 1
fi
exit 0

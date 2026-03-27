#!/bin/bash
# Description: Test for sync_disciplines.sh

TEST_ROOT="/tmp/test_sync_disciplines_sh"
rm -rf "$TEST_ROOT"
mkdir -p "$TEST_ROOT"

# Mock source
mkdir -p "$TEST_ROOT/rules_src"
echo "Rule 1 content" > "$TEST_ROOT/rules_src/rule1.md"
echo "Rule 2 content" > "$TEST_ROOT/rules_src/rule2.md"

mkdir -p "$TEST_ROOT/workflows_src"
echo -e "Workflow A" > "$TEST_ROOT/workflows_src/wfA.md"

# Target init
echo "# Initial GEMINI.md" > "$TEST_ROOT/GEMINI.md"

# Mock config
cat <<EOF > "$TEST_ROOT/config.json"
[
  {
    "agent": "test_agent",
    "disciplines": [
      {
        "type": "rules",
        "source": "$TEST_ROOT/rules_src",
        "target": "$TEST_ROOT/GEMINI.md",
        "link_type": "insert_text"
      },
      {
        "type": "workflows",
        "source": "$TEST_ROOT/workflows_src",
        "target": "$TEST_ROOT/global_workflows",
        "link_type": "soft_link"
      }
    ]
  }
]
EOF

# Override script config file for test
# We'll use a temporary script that references our test config
sed "s|CONFIG_FILE=.*|CONFIG_FILE=\"$TEST_ROOT/config.json\"|" /home/logos/.gemini/.agent/skills/sync_disciplines/scripts/sync.sh > "$TEST_ROOT/test_script.sh"
chmod +x "$TEST_ROOT/test_script.sh"

# Run test
"$TEST_ROOT/test_script.sh" test_agent

# Verify
echo "Verifying results..."
if grep -q "Rule 1 content" "$TEST_ROOT/GEMINI.md" && grep -q "DISCIPLINE_START: rules_src" "$TEST_ROOT/GEMINI.md"; then
    echo "  PASS: rules inserted successfully"
else
    echo "  FAIL: rules insertion failed"
    exit 1
fi

if [[ -L "$TEST_ROOT/global_workflows" && "$(readlink -f "$TEST_ROOT/global_workflows")" == "$(readlink -f "$TEST_ROOT/workflows_src")" ]]; then
    echo "  PASS: soft link created successfully"
else
    echo "  FAIL: soft link failed"
    exit 1
fi

# Cleanup
rm -rf "$TEST_ROOT"
echo "Tests completed successfully."

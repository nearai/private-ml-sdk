#!/bin/bash
set -e

# Configuration
UPSTREAM_URL="https://github.com/Dstack-TEE/meta-dstack"
UPSTREAM_BRANCH="main"
SUBTREE_PREFIX="meta-dstack-nvidia"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}=== Upstream Sync for meta-dstack ===${NC}"

# Check we're in the right repo
if [[ ! -d "$SUBTREE_PREFIX" ]]; then
    echo -e "${RED}Error: $SUBTREE_PREFIX directory not found${NC}"
    echo "This script must be run from the Private-ML-SDK repository root"
    exit 1
fi

# Add remote if not exists
if ! git remote | grep -q "^meta-dstack-upstream$"; then
    echo -e "${YELLOW}Adding upstream remote...${NC}"
    git remote add meta-dstack-upstream "$UPSTREAM_URL"
fi

# Fetch latest from upstream without tags
echo -e "${YELLOW}Fetching upstream changes...${NC}"
git fetch --no-tags meta-dstack-upstream "$UPSTREAM_BRANCH"

# Use subtree merge strategy without squash to preserve history
echo -e "${YELLOW}Merging upstream changes...${NC}"
git merge -X subtree="$SUBTREE_PREFIX/" \
    --no-squash \
    --allow-unrelated-histories \
    meta-dstack-upstream/"$UPSTREAM_BRANCH" \
    -m "Sync with upstream meta-dstack $(date +%Y-%m-%d)"

if [[ $? -eq 0 ]]; then
    echo -e "${GREEN}=== Sync Complete ===${NC}"
    echo "Review changes with: git diff HEAD~1"
else
    echo -e "${RED}=== Merge conflicts detected ===${NC}"
    echo "Please resolve conflicts manually and commit"
    exit 1
fi

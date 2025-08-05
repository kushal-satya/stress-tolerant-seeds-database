#!/bin/bash

# GitHub Repository Setup Script
# Run this script after creating the repository on GitHub.com

echo "Setting up GitHub repository for Stress-Tolerant Seeds Database"
echo "=================================================="

# Check if we're in a git repository
if [ ! -d ".git" ]; then
    echo "Error: Not in a git repository. Please run this from the project root."
    exit 1
fi

# Get GitHub username and repository name
echo "Please provide your GitHub details:"
read -p "Enter your GitHub username: " GITHUB_USERNAME
read -p "Enter repository name (default: stress-tolerant-seeds-database): " REPO_NAME
REPO_NAME=${REPO_NAME:-stress-tolerant-seeds-database}

# Construct repository URL
REPO_URL="https://github.com/${GITHUB_USERNAME}/${REPO_NAME}.git"

echo ""
echo "Repository URL: $REPO_URL"
echo ""

# Add remote origin
echo "Adding remote origin..."
git remote add origin "$REPO_URL"

# Verify remote
echo "Remote added. Current remotes:"
git remote -v

echo ""
echo "Pushing to GitHub..."

# Push to GitHub
if git push -u origin main; then
    echo ""
    echo "Success! Repository uploaded to GitHub!"
    echo "View your repository at: https://github.com/${GITHUB_USERNAME}/${REPO_NAME}"
    echo ""
    echo "To make future updates:"
    echo "   git add ."
    echo "   git commit -m \"Your commit message\""
    echo "   git push"
else
    echo ""
    echo "Error: Failed to push to GitHub."
    echo "Make sure you have:"
    echo "   1. Created the repository on GitHub.com"
    echo "   2. Have correct permissions"
    echo "   3. Are logged in to git (git config --global user.name)"
fi

echo ""
echo "Next steps:"
echo "   1. Visit your repository on GitHub"
echo "   2. Add a description and topics"
echo "   3. Consider adding collaborators"
echo "   4. Share the repository URL!"


#!/bin/bash
echo "📦 Creating deployment package..."

# Remove old archives
rm -f bot_deploy.tar.gz

# Create tarball of current directory, excluding junk
# We need: core/, agents/, main_orchestrator.py, dashboard.py, database.py, paper_trader.py, technical_analyst.py, requirements.txt, Dockerfile, docker-compose.yml
# We exclude: logs/, data/ (except maybe structure), venv/, .git/, __pycache__

tar -czvf bot_deploy.tar.gz \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.DS_Store' \
    --exclude='.env' \
    --exclude='logs' \
    --exclude='data/*.db' \
    --exclude='venv' \
    --exclude='.git' \
    core/ \
    agents/ \
    *.py \
    requirements.txt \
    Dockerfile \
    docker-compose.yml

echo "✅ Package 'bot_deploy.tar.gz' created."

#!/bin/bash
# ===========================================
# PythonAnywhere Auto-Deploy Script
# Billing Tool - One-click deployment
# ===========================================

USERNAME="Shubhamkokane"
PROJECT_DIR="/home/$USERNAME/Billing-Tool"
VENV_DIR="$PROJECT_DIR/venv"
DOMAIN="${USERNAME}.pythonanywhere.com"

echo "========================================="
echo "  Deploying Billing Tool to PythonAnywhere"
echo "========================================="

# Step 1: Clone the repo
echo ""
echo "[1/7] Cloning repository..."
cd /home/$USERNAME
if [ -d "Billing-Tool" ]; then
    echo "  -> Repo already exists, pulling latest..."
    cd Billing-Tool && git pull origin master
else
    git clone https://github.com/curioushubham/Billing-Tool.git
    cd Billing-Tool
fi

# Step 2: Create virtual environment
echo ""
echo "[2/7] Setting up virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate

# Step 3: Install dependencies
echo ""
echo "[3/7] Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Step 4: Create .env file
echo ""
echo "[4/7] Creating .env configuration..."
SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(50))")
cat > .env << ENVEOF
SECRET_KEY=$SECRET
DEBUG=False
ALLOWED_HOSTS=$DOMAIN,www.$DOMAIN
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
ENVEOF
echo "  -> .env created with secure secret key"

# Step 5: Run migrations
echo ""
echo "[5/7] Running database migrations..."
python manage.py migrate --noinput

# Step 6: Collect static files
echo ""
echo "[6/7] Collecting static files..."
python manage.py collectstatic --noinput

# Step 7: Create superuser
echo ""
echo "[7/7] Creating admin superuser..."
python manage.py shell -c "
from accounts.models import User
if not User.objects.filter(username='admin').exists():
    u = User.objects.create_superuser('admin', 'admin@billing.com', 'admin123')
    u.role = 'admin'
    u.save()
    print('  -> Superuser created: admin / admin123')
else:
    print('  -> Superuser already exists')
"

echo ""
echo "========================================="
echo "  CODE DEPLOYED SUCCESSFULLY!"
echo "========================================="
echo ""
echo "  Now do these MANUAL steps on PythonAnywhere:"
echo ""
echo "  1. Go to the WEB tab"
echo "  2. Click 'Add a new web app'"
echo "  3. Choose 'Manual configuration'"
echo "  4. Select Python 3.10"
echo ""
echo "  5. Set VIRTUALENV path to:"
echo "     /home/$USERNAME/Billing-Tool/venv"
echo ""
echo "  6. Click the WSGI config file link and"
echo "     REPLACE ALL contents with this:"
echo ""
echo "  ---- COPY FROM HERE ----"
cat << 'WSGIEOF'
import os
import sys

path = '/home/Shubhamkokane/Billing-Tool'
if path not in sys.path:
    sys.path.append(path)

os.environ['DJANGO_SETTINGS_MODULE'] = 'billing_project.settings'

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
WSGIEOF
echo "  ---- COPY TO HERE ----"
echo ""
echo "  7. In Static Files section, add:"
echo "     URL: /static/  -> /home/$USERNAME/Billing-Tool/staticfiles"
echo "     URL: /media/   -> /home/$USERNAME/Billing-Tool/media"
echo ""
echo "  8. Click the green RELOAD button"
echo ""
echo "  9. Visit: https://$DOMAIN"
echo "     Login: admin / admin123"
echo ""
echo "========================================="

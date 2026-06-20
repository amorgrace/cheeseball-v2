cd "$(dirname "$0")"
pip install -r requirements.txt
python manage.py collectstatic --noinput
python manage.py migrate

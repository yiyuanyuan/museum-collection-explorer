# Gunicorn configuration file

# Increase worker timeout to 120 seconds (default is 30)
# This is needed for OpenAI API calls which can take longer
timeout = 120

# Number of worker processes
workers = 2

# Worker class
worker_class = 'sync'

# Bind address
bind = '0.0.0.0:5000'

# Access log
accesslog = '-'

# Error log
errorlog = '-'

# Log level
loglevel = 'info'
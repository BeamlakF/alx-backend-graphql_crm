#!/bin/bash

# Navigate to project root (adjust if needed)
cd "$(dirname "$0")/../.."

# Run Django shell to delete inactive customers
deleted_count=$(python3 manage.py shell <<EOF
import datetime
from crm.models import Customer, Order

one_year_ago = datetime.datetime.now() - datetime.timedelta(days=365)

# Customers with no orders in past year
inactive_customers = Customer.objects.exclude(
    id__in=Order.objects.filter(order_date__gte=one_year_ago).values("customer_id")
)

count = inactive_customers.count()
inactive_customers.delete()

print(count)
EOF
)

# Log the result with timestamp
echo "$(date '+%Y-%m-%d %H:%M:%S') Deleted customers: $deleted_count" >> /tmp/customer_cleanup_log.txt

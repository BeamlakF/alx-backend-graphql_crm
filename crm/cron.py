import datetime
from gql import gql, Client
from gql.transport.requests import RequestsHTTPTransport


def log_crm_heartbeat():
    """Log CRM heartbeat and optionally check GraphQL hello query."""

    # 1. Log heartbeat
    now = datetime.datetime.now().strftime("%d/%m/%Y-%H:%M:%S")
    message = f"{now} CRM is alive"
    with open("/tmp/crm_heartbeat_log.txt", "a") as log_file:
        log_file.write(message + "\n")

    # 2. Optionally check GraphQL endpoint (hello field)
    try:
        transport = RequestsHTTPTransport(
            url="http://localhost:8000/graphql",  # adjust if endpoint differs
            verify=False,
            retries=3,
        )
        client = Client(transport=transport, fetch_schema_from_transport=True)

        query = gql("{ hello }")
        result = client.execute(query)

        with open("/tmp/crm_heartbeat_log.txt", "a") as log_file:
            log_file.write(f"{now} GraphQL hello response: {result['hello']}\n")

    except Exception as e:
        with open("/tmp/crm_heartbeat_log.txt", "a") as log_file:
            log_file.write(f"{now} GraphQL hello check failed: {e}\n")

import graphene

class Query(graphene.ObjectType):
    hello = graphene.String(description="Simple hello world field")

    def resolve_hello(root, info):
        return "Hello, GraphQL!"

schema = graphene.Schema(query=Query)

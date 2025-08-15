import graphene
from graphene_django import DjangoObjectType
from .models import Customer, Product, Order
import re
from django.db import transaction



# === GraphQL Types ===
class CustomerType(DjangoObjectType):
    class Meta:
        model = Customer
        fields = ("id", "name", "email", "phone", "created_at")


class ProductType(DjangoObjectType):
    class Meta:
        model = Product
        fields = ("id", "name", "price", "stock")


class OrderType(DjangoObjectType):
    class Meta:
        model = Order
        fields = ("id", "customer", "products", "total_amount", "order_date")


# === Query Class ===
class Query(graphene.ObjectType):
    all_customers = graphene.List(CustomerType)
    all_products = graphene.List(ProductType)
    all_orders = graphene.List(OrderType)

    def resolve_all_customers(root, info):
        return Customer.objects.all()

    def resolve_all_products(root, info):
        return Product.objects.all()

    def resolve_all_orders(root, info):
        return Order.objects.select_related("customer").prefetch_related("products").all()

class CustomerInput(graphene.InputObjectType):
    name = graphene.String(required=True)
    email = graphene.String(required=True)
    phone = graphene.String(required=False)

# === CreateCustomer Mutation ===
class CreateCustomer(graphene.Mutation):
    class Arguments:
        input = CustomerInput(required=True)

    customer = graphene.Field(lambda: CustomerType)
    message = graphene.String()

    def mutate(root, info, input):
        # Email uniqueness check
        if Customer.objects.filter(email=input.email).exists():
            raise Exception("Email already exists.")

        # Optional phone validation
        if input.phone:
            phone_pattern = re.compile(r'^(\+\d{10,15}|\d{3}-\d{3}-\d{4})$')
            if not phone_pattern.match(input.phone):
                raise Exception("Invalid phone format.")

        customer = Customer(
            name=input.name,
            email=input.email,
            phone=input.phone
        )
        customer.save()

        return CreateCustomer(customer=customer, message="Customer created successfully.")
    
class BulkCreateCustomers(graphene.Mutation):
    class Arguments:
        inputs = graphene.List(CustomerInput, required=True)

    customers = graphene.List(lambda: CustomerType)
    errors = graphene.List(graphene.String)

    def mutate(root, info, inputs):
        created_customers = []
        errors = []

        # Start a transaction for bulk creation
        with transaction.atomic():
            for idx, input in enumerate(inputs):
                try:
                    # Email uniqueness
                    if Customer.objects.filter(email=input.email).exists():
                        raise Exception(f"Email already exists: {input.email}")

                    # Optional phone validation
                    if input.phone:
                        phone_pattern = re.compile(r'^(\+\d{10,15}|\d{3}-\d{3}-\d{4})$')
                        if not phone_pattern.match(input.phone):
                            raise Exception(f"Invalid phone format: {input.phone}")

                    customer = Customer(
                        name=input.name,
                        email=input.email,
                        phone=input.phone
                    )
                    customer.save()
                    created_customers.append(customer)

                except Exception as e:
                    errors.append(f"Record {idx + 1}: {str(e)}")
                    # Do not stop the loop — allow other valid records

        return BulkCreateCustomers(customers=created_customers, errors=errors)

class ProductInput(graphene.InputObjectType):
    name = graphene.String(required=True)
    price = graphene.Float(required=True)
    stock = graphene.Int(required=False, default_value=0)


class CreateProduct(graphene.Mutation):
    class Arguments:
        input = ProductInput(required=True)

    product = graphene.Field(lambda: ProductType)
    message = graphene.String()

    def mutate(root, info, input):
        # Validation
        if input.price <= 0:
            raise Exception("Price must be positive.")
        if input.stock < 0:
            raise Exception("Stock cannot be negative.")

        product = Product(
            name=input.name,
            price=input.price,
            stock=input.stock
        )
        product.save()

        return CreateProduct(product=product, message="Product created successfully.")


class Mutation(graphene.ObjectType):
    create_customer = CreateCustomer.Field()
    bulk_create_customers = BulkCreateCustomers.Field()
    create_product = CreateProduct.Field()